import json
import re
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.enums import RolMiembro, TipoDocumento
from app.models import Empresa, Expediente
from app.schemas import NexusChatOut, NexusFuente
from app.security import ContextoAcceso
from app.services.expedientes import documentos_faltantes, tipos_presentes


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
) -> NexusChatOut:
    texto = mensaje.strip()
    normalizado = texto.lower()

    if expediente_id is not None and any(
        frase in normalizado
        for frase in ("qué falta", "que falta", "falta algo", "expediente", "revisar factura")
    ):
        return _responder_expediente(session, settings, auth, expediente_id)

    ruc = _extraer_ruc(texto)
    if ruc is not None and any(
        palabra in normalizado
        for palabra in ("ruc", "verifica", "verificar", "razon", "razón", "sunat")
    ):
        return _responder_ruc(session, settings, auth, ruc)

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
        return _responder_totales(session, settings, auth)

    if any(
        palabra in normalizado
        for palabra in (
            "sunat",
            "norma",
            "regla",
            "actualización",
            "actualizacion",
            "internet",
            "buscar",
        )
    ):
        return _responder_busqueda_web(settings, texto)

    contexto = _contexto_basico(session, auth, expediente_id)
    respuesta = (
        "Estoy conectado al contexto de FACT CENTRAL. Puedo revisar el expediente actual, "
        "consultar RUC, calcular compras dentro de tu ámbito, explicar qué documentos faltan "
        "y usar una integración externa para consultas SUNAT cuando esté configurada."
    )
    if contexto:
        respuesta += " Contexto actual: " + contexto
    return NexusChatOut(
        respuesta=respuesta,
        accion="AYUDA",
        datos={"ruta": ruta},
    )


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
    if not _puede_ver_expediente(auth, expediente):
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
            + (f"en FACT CENTRAL figura como {local}." if local else "no está registrado localmente.")
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
    condiciones = [
        Expediente.tenant_id == auth.tenant_id,
        Expediente.deleted_at.is_(None),
        Expediente.fecha_emision >= desde,
        Expediente.fecha_emision <= hoy,
    ]
    if auth.rol == "GESTOR":
        condiciones.append(Expediente.gestor_id == auth.gestor_id)
    elif auth.rol == RolMiembro.USUARIO:
        condiciones.append(Expediente.usuario_id == auth.usuario_id)

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


def _puede_ver_expediente(auth: ContextoAcceso, expediente: Expediente) -> bool:
    if auth.rol == "GESTOR":
        return expediente.gestor_id == auth.gestor_id
    if auth.rol == RolMiembro.USUARIO:
        return expediente.usuario_id == auth.usuario_id
    return True


def _contexto_basico(
    session: Session,
    auth: ContextoAcceso,
    expediente_id: uuid.UUID | None,
) -> str:
    if expediente_id is None:
        return f"sesión {auth.codigo} ({auth.rol})"
    expediente = session.get(Expediente, expediente_id)
    if expediente is None or not _puede_ver_expediente(auth, expediente):
        return f"sesión {auth.codigo} ({auth.rol})"
    return (
        f"{expediente.tipo_comprobante} {expediente.serie}-{expediente.correlativo}, "
        f"{expediente.moneda} {expediente.importe_total}"
    )
