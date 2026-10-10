import json
import re
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.enums import RolMiembro, TipoDocumento
from app.models import Empresa, Expediente
from app.schemas import NexusChatOut, NexusFuente, NexusMensajeHistorial
from app.security import ContextoAcceso
from app.services.expedientes import documentos_faltantes, tipos_presentes
from app.services.nexus_context import (
    ContextoNexus,
    condiciones_expedientes,
    construir_contexto,
    puede_ver_expediente,
)
from app.services.nexus_knowledge import recuperar_conocimiento


@dataclass(frozen=True)
class RespuestaExterna:
    texto: str
    fuentes: list[NexusFuente]
    datos: dict[str, object]


def responder(
    session: Session,
    settings: Settings,
    auth: ContextoAcceso,
    mensaje: str,
    ruta: str,
    expediente_id: uuid.UUID | None,
    historial: list[NexusMensajeHistorial] | None = None,
) -> NexusChatOut:
    texto = mensaje.strip()
    normalizado = texto.lower()
    contexto = construir_contexto(session, settings, auth, ruta, expediente_id)
    conocimiento, fuentes_conocimiento = recuperar_conocimiento(
        settings,
        texto,
        contexto.seccion,
    )

    if expediente_id is not None and any(
        frase in normalizado
        for frase in ("qué falta", "que falta", "falta algo", "expediente", "revisar factura")
    ):
        salida = _responder_expediente(session, settings, auth, expediente_id)
        return _enriquecer(salida, contexto, fuentes_conocimiento, "ESPECIALISTA_EXPEDIENTES")

    ruc = _extraer_ruc(texto)
    if ruc is not None and any(
        palabra in normalizado
        for palabra in ("ruc", "verifica", "verificar", "razon", "razón", "sunat")
    ):
        salida = _responder_ruc(session, settings, auth, ruc)
        return _enriquecer(salida, contexto, fuentes_conocimiento, "ESPECIALISTA_RUC")

    if any(
        frase in normalizado
        for frase in (
            "cuánto llevo",
            "cuanto llevo",
            "total de compras",
            "cuánto va",
            "cuanto va",
            "compras este mes",
            "compras del mes",
        )
    ):
        salida = _responder_totales(session, settings, auth)
        return _enriquecer(salida, contexto, fuentes_conocimiento, "ESPECIALISTA_DATOS")

    if any(
        palabra in normalizado
        for palabra in (
            "sunat",
            "norma",
            "actualización",
            "actualizacion",
            "internet",
            "buscar",
        )
    ) and settings.nexus_search_url:
        salida = _responder_busqueda_web(settings, texto)
        return _enriquecer(salida, contexto, fuentes_conocimiento, "ESPECIALISTA_WEB")

    if settings.nexus_llm_url:
        try:
            return _responder_llm(
                settings,
                contexto,
                texto,
                historial or [],
                conocimiento,
                fuentes_conocimiento,
            )
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
            pass

    return _responder_contextual(
        contexto,
        texto,
        conocimiento,
        fuentes_conocimiento,
        requiere_llm=not bool(settings.nexus_llm_url),
    )


def _enriquecer(
    salida: NexusChatOut,
    contexto: ContextoNexus,
    fuentes: list[NexusFuente],
    motor: str,
) -> NexusChatOut:
    existentes = {(fuente.titulo, fuente.tipo) for fuente in salida.fuentes}
    combinadas = list(salida.fuentes)
    for fuente in fuentes:
        clave = (fuente.titulo, fuente.tipo)
        if clave not in existentes:
            combinadas.append(fuente)
            existentes.add(clave)
    datos = dict(salida.datos)
    datos["contexto"] = {
        "seccion": contexto.seccion,
        "ruta": contexto.ruta,
        "advertencias": contexto.advertencias,
    }
    return salida.model_copy(
        update={
            "fuentes": combinadas,
            "datos": datos,
            "motor": motor,
            "seccion": contexto.seccion,
        }
    )


def _responder_contextual(
    contexto: ContextoNexus,
    consulta: str,
    conocimiento: str,
    fuentes: list[NexusFuente],
    *,
    requiere_llm: bool,
) -> NexusChatOut:
    datos = contexto.datos
    partes = [
        f"Estoy trabajando en el contexto de {contexto.seccion}.",
        _resumen_contexto(datos),
    ]
    if contexto.advertencias:
        partes.append("Límite de acceso: " + " ".join(contexto.advertencias))
    if conocimiento:
        partes.append(
            "Encontré reglas o documentación relacionada en la base de conocimiento y las adjunto "
            "como fuentes. Puedo explicarlas con más detalle."
        )
    if requiere_llm:
        partes.append(
            "El motor conversacional externo todavía no está configurado; por ahora respondo con "
            "el contexto estructurado y los especialistas determinísticos de FACT CENTRAL."
        )
    return NexusChatOut(
        respuesta=" ".join(parte for parte in partes if parte),
        accion="CONTEXTO_NEXUS",
        fuentes=fuentes,
        datos={
            "consulta": consulta,
            "contexto": datos,
            "advertencias": contexto.advertencias,
        },
        motor="CONTEXTUAL",
        seccion=contexto.seccion,
        requiere_configuracion_externa=requiere_llm,
    )


def _resumen_contexto(datos: dict[str, object]) -> str:
    mes = datos.get("mes_actual")
    estados = datos.get("expedientes_por_estado")
    detalles: list[str] = []
    if isinstance(mes, dict):
        compras = mes.get("compras")
        if isinstance(compras, dict) and compras:
            segmentos = []
            for moneda, valor in compras.items():
                if isinstance(valor, dict):
                    segmentos.append(
                        f"{valor.get('expedientes', 0)} expedientes por {moneda} "
                        f"{valor.get('importe', '0')}"
                    )
            if segmentos:
                detalles.append("Mes actual: " + "; ".join(segmentos) + ".")
    if isinstance(estados, dict) and estados:
        detalles.append(
            "Estados: " + ", ".join(f"{clave}={valor}" for clave, valor in estados.items()) + "."
        )
    if "expediente_actual" in datos:
        actual = datos["expediente_actual"]
        if isinstance(actual, dict):
            detalles.append(
                f"Expediente actual: {actual.get('numero')} · estado {actual.get('estado')} · "
                f"{actual.get('moneda')} {actual.get('importe_total')}."
            )
    if "pagos" in datos:
        pago = datos["pagos"]
        if isinstance(pago, dict):
            detalles.append(
                f"Pagos: {pago.get('pedidos_mes', 0)} pedidos del mes por "
                f"{pago.get('monto_solicitado_mes', '0')}."
            )
    return " ".join(detalles) or "No hay un resumen cuantitativo adicional para esta pantalla."


def _responder_llm(
    settings: Settings,
    contexto: ContextoNexus,
    consulta: str,
    historial: list[NexusMensajeHistorial],
    conocimiento: str,
    fuentes: list[NexusFuente],
) -> NexusChatOut:
    assert settings.nexus_llm_url is not None
    limite = max(1, settings.nexus_history_messages)
    historial_reciente = historial[-limite:]

    sistema = (
        "Eres NEXUS, asistente operativo de FACT CENTRAL. Responde en español claro y profesional. "
        "Tu autoridad está limitada al CONTEXTO AUTORIZADO recibido. Nunca amplíes permisos, nunca "
        "cambies Tenant, nunca inventes datos y nunca afirmes haber modificado el sistema. "
        "Los datos transaccionales de FACT CENTRAL tienen prioridad para cifras y estados. "
        "La BASE DE CONOCIMIENTO sirve para explicar reglas y arquitectura. Si falta evidencia, "
        "di exactamente qué falta. Diferencia hechos del sistema, reglas documentadas "
        "e inferencias. No cierres expedientes, no apruebes pagos, no cambies reglas ni "
        "datos críticos. Puedes explicar, detectar inconsistencias, sugerir pasos y "
        "responder preguntas contextuales."
    )
    mensajes: list[dict[str, str]] = [{"role": "system", "content": sistema}]
    mensajes.append(
        {
            "role": "system",
            "content": (
                "CONTEXTO AUTORIZADO\n"
                + contexto.a_prompt(settings.nexus_context_max_chars)
            ),
        }
    )
    if conocimiento:
        mensajes.append(
            {
                "role": "system",
                "content": "BASE DE CONOCIMIENTO RELEVANTE\n" + conocimiento,
            }
        )
    for item in historial_reciente:
        mensajes.append(
            {
                "role": "user" if item.autor == "usuario" else "assistant",
                "content": item.texto,
            }
        )
    mensajes.append({"role": "user", "content": consulta})

    datos = _http_json(
        settings.nexus_llm_url,
        method="POST",
        token=settings.nexus_llm_token,
        timeout=settings.nexus_llm_timeout_seconds,
        payload={
            "model": settings.nexus_llm_model or "default",
            "messages": mensajes,
            "temperature": 0.2,
        },
    )
    respuesta = _texto_llm(datos)
    if not respuesta:
        raise ValueError("El motor conversacional no devolvió texto")

    return NexusChatOut(
        respuesta=respuesta,
        accion="RESPUESTA_CONTEXTUAL",
        fuentes=fuentes,
        datos={
            "contexto": {
                "seccion": contexto.seccion,
                "ruta": contexto.ruta,
                "advertencias": contexto.advertencias,
            }
        },
        llm_usado=True,
        motor="LLM_CONTEXTUAL",
        seccion=contexto.seccion,
    )


def _texto_llm(datos: dict[str, object]) -> str | None:
    for clave in ("answer", "respuesta", "output_text", "text"):
        valor = datos.get(clave)
        if isinstance(valor, str) and valor.strip():
            return valor.strip()

    choices = datos.get("choices")
    if isinstance(choices, list) and choices:
        primero = choices[0]
        if isinstance(primero, dict):
            message = primero.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()
    return None


def _responder_expediente(
    session: Session,
    settings: Settings,
    auth: ContextoAcceso,
    expediente_id: uuid.UUID,
) -> NexusChatOut:
    expediente = session.get(Expediente, expediente_id)
    if expediente is None or expediente.tenant_id != auth.tenant_id or expediente.deleted_at:
        return NexusChatOut(
            respuesta="No encuentro ese expediente dentro de tu ámbito.",
            accion="EXPEDIENTE_NO_DISPONIBLE",
        )
    if not puede_ver_expediente(session, auth, expediente):
        return NexusChatOut(
            respuesta="Ese expediente no pertenece a tu ámbito de acceso.",
            accion="EXPEDIENTE_NO_DISPONIBLE",
        )

    faltantes = documentos_faltantes(expediente, settings)
    presentes = [TipoDocumento(tipo) for tipo in tipos_presentes(expediente)]
    numero = f"{expediente.tipo_comprobante} {expediente.serie}-{expediente.correlativo}"
    if faltantes:
        lista = ", ".join(tipo.value for tipo in faltantes)
        respuesta = f"{numero}: faltan {lista}."
    else:
        respuesta = f"{numero}: no tiene documentos obligatorios pendientes."

    if expediente.importe_total < settings.umbral_bancarizacion_pen and expediente.moneda == "PEN":
        respuesta += (
            " Por estar debajo de S/ 2,000, guía, voucher y cotización no son obligatorios "
            "por la regla interna configurada; pueden adjuntarse como sustento."
        )

    return NexusChatOut(
        respuesta=respuesta,
        accion="REVISAR_EXPEDIENTE",
        datos={
            "expediente_id": str(expediente.id),
            "numero": numero,
            "estado": expediente.estado,
            "importe_total": str(expediente.importe_total),
            "moneda": expediente.moneda,
            "presentes": [tipo.value for tipo in presentes],
            "faltantes": [tipo.value for tipo in faltantes],
        },
    )


def _responder_ruc(
    session: Session,
    settings: Settings,
    auth: ContextoAcceso,
    ruc: str,
) -> NexusChatOut:
    empresa = session.scalar(
        select(Empresa).where(
            Empresa.tenant_id == auth.tenant_id,
            Empresa.ruc == ruc,
            Empresa.deleted_at.is_(None),
        )
    )
    local = empresa.razon_social if empresa is not None else None

    if settings.nexus_ruc_url_template:
        try:
            externo = _consultar_ruc_externo(settings, ruc)
            coincidencia = None
            razon_externa = _encontrar_razon_social(externo.datos)
            if local and razon_externa:
                coincidencia = local.strip().upper() == razon_externa.strip().upper()
            respuesta = f"RUC {ruc} consultado externamente."
            if local:
                respuesta += f" En FACT CENTRAL: {local}."
            if razon_externa:
                respuesta += f" Fuente externa: {razon_externa}."
            if coincidencia is True:
                respuesta += " Las razones sociales coinciden."
            elif coincidencia is False:
                respuesta += " Hay una diferencia; no modifiqué la base de datos."
            return NexusChatOut(
                respuesta=respuesta,
                accion="VERIFICAR_RUC",
                fuentes=externo.fuentes,
                datos={
                    "ruc": ruc,
                    "razon_local": local,
                    "razon_externa": razon_externa,
                    "coincide": coincidencia,
                    "respuesta_externa": externo.datos,
                },
                internet_usado=True,
            )
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            return NexusChatOut(
                respuesta=(
                    f"No pude completar la consulta externa del RUC {ruc}. "
                    f"La información local es: {local or 'sin registro'}. "
                    "No se modificó ningún dato."
                ),
                accion="VERIFICAR_RUC",
                datos={"ruc": ruc, "razon_local": local, "error_externo": str(exc)},
            )

    return NexusChatOut(
        respuesta=(
            f"RUC {ruc}: "
            + (
                f"en FACT CENTRAL figura como {local}."
                if local
                else "no está registrado localmente."
            )
            + " La consulta externa de RUC todavía no tiene proveedor configurado."
        ),
        accion="VERIFICAR_RUC",
        datos={"ruc": ruc, "razon_local": local},
        requiere_configuracion_externa=True,
    )


def _responder_totales(
    session: Session,
    settings: Settings,
    auth: ContextoAcceso,
) -> NexusChatOut:
    hoy = settings.hoy()
    desde = date(hoy.year, hoy.month, 1)
    condiciones = condiciones_expedientes(session, auth)
    condiciones.extend(
        [
            Expediente.tenant_id == auth.tenant_id,
            Expediente.deleted_at.is_(None),
            Expediente.fecha_emision >= desde,
            Expediente.fecha_emision <= hoy,
        ]
    )

    filas = session.execute(
        select(
            Expediente.moneda,
            func.count(Expediente.id),
            func.coalesce(func.sum(Expediente.importe_total), 0),
        )
        .where(*condiciones)
        .group_by(Expediente.moneda)
    ).all()

    totales: dict[str, dict[str, object]] = {}
    partes: list[str] = []
    for moneda, cantidad, total in filas:
        valor = Decimal(total or 0)
        totales[str(moneda)] = {"registros": int(cantidad), "total": str(valor)}
        partes.append(f"{int(cantidad)} registros por {moneda} {valor:,.2f}")

    if partes:
        respuesta = "Compras del mes dentro de tu ámbito: " + "; ".join(partes) + "."
    else:
        respuesta = "No hay compras registradas este mes dentro de tu ámbito."

    return NexusChatOut(
        respuesta=respuesta,
        accion="TOTAL_COMPRAS_MES",
        datos={"desde": desde.isoformat(), "hasta": hoy.isoformat(), "totales": totales},
    )


def _responder_busqueda_web(settings: Settings, consulta: str) -> NexusChatOut:
    if not settings.nexus_search_url:
        return NexusChatOut(
            respuesta=(
                "Puedo consultar fuentes externas y priorizar SUNAT, pero el conector de búsqueda "
                "a Internet todavía no tiene endpoint configurado en este servidor."
            ),
            accion="BUSQUEDA_WEB",
            datos={"consulta": consulta, "dominio_preferido": "sunat.gob.pe"},
            requiere_configuracion_externa=True,
        )

    try:
        externo = _buscar_web(settings, consulta)
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        return NexusChatOut(
            respuesta="La búsqueda externa falló. No se cambió ninguna regla del sistema.",
            accion="BUSQUEDA_WEB",
            datos={"consulta": consulta, "error_externo": str(exc)},
        )
    return NexusChatOut(
        respuesta=externo.texto,
        accion="BUSQUEDA_WEB",
        fuentes=externo.fuentes,
        datos=externo.datos,
        internet_usado=True,
    )


def _consultar_ruc_externo(settings: Settings, ruc: str) -> RespuestaExterna:
    assert settings.nexus_ruc_url_template is not None
    url = settings.nexus_ruc_url_template.format(ruc=ruc)
    datos = _http_json(
        url,
        method="GET",
        token=settings.nexus_ruc_token,
        timeout=settings.nexus_external_timeout_seconds,
    )
    return RespuestaExterna(
        texto=f"Consulta externa de RUC {ruc}.",
        fuentes=[NexusFuente(titulo="Consulta RUC externa", url=url, tipo="RUC")],
        datos=datos,
    )


def _buscar_web(settings: Settings, consulta: str) -> RespuestaExterna:
    assert settings.nexus_search_url is not None
    datos = _http_json(
        settings.nexus_search_url,
        method="POST",
        token=settings.nexus_search_token,
        timeout=settings.nexus_external_timeout_seconds,
        payload={
            "query": consulta,
            "preferred_domains": ["sunat.gob.pe"],
            "language": "es",
        },
    )
    texto = str(datos.get("answer") or datos.get("respuesta") or "Consulta externa completada.")
    fuentes: list[NexusFuente] = []
    fuentes_crudas = datos.get("sources") or datos.get("fuentes")
    if isinstance(fuentes_crudas, list):
        for item in fuentes_crudas[:8]:
            if isinstance(item, dict):
                fuentes.append(
                    NexusFuente(
                        titulo=str(item.get("title") or item.get("titulo") or "Fuente"),
                        url=str(item.get("url")) if item.get("url") else None,
                        tipo="WEB",
                    )
                )
    return RespuestaExterna(texto=texto, fuentes=fuentes, datos=datos)


def _http_json(
    url: str,
    *,
    method: str,
    token: str | None,
    timeout: int,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    headers = {"Accept": "application/json", "User-Agent": "FACT-CENTRAL-NEXUS/1.0"}
    body: bytes | None = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        contenido = response.read().decode("utf-8")
    resultado = json.loads(contenido)
    if not isinstance(resultado, dict):
        raise ValueError("La integración externa no devolvió un objeto JSON")
    return resultado


def _encontrar_razon_social(datos: dict[str, object]) -> str | None:
    candidatos = (
        "razon_social",
        "razonSocial",
        "nombre_o_razon_social",
        "nombre",
    )
    for clave in candidatos:
        valor = datos.get(clave)
        if isinstance(valor, str) and valor.strip():
            return valor.strip()
    data = datos.get("data")
    if isinstance(data, dict):
        return _encontrar_razon_social(data)
    return None


def _extraer_ruc(texto: str) -> str | None:
    coincidencia = re.search(r"(?<!\d)(?:10|20)\d{9}(?!\d)", texto)
    return coincidencia.group(0) if coincidencia else None
