"""Aplicación automática y auditable de una extracción documental.

La automatización solo materializa facturas o RHE cuando la clasificación y todos
los campos de identidad fiscal superan los umbrales configurados. Los casos
ambiguos permanecen en la bandeja de revisión con motivos explícitos.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.enums import EstadoDocumento, Moneda, TipoComprobante, TipoDocumento
from app.models import Documento
from app.services import auditoria
from app.services.expedientes import buscar_expediente, obtener_o_crear_empresa
from app.services.ingesta import crear_expediente, vincular_documento

CAMPOS_FISCALES = (
    "serie",
    "correlativo",
    "ruc_emisor",
    "ruc_receptor",
    "fecha_emision",
    "moneda",
    "importe_total",
)


@dataclass(frozen=True)
class ResultadoAutomatizacion:
    estado: str
    relacionado: bool = False
    expediente_id: uuid.UUID | None = None
    motivos: tuple[str, ...] = ()


def guardar_procesamiento(
    session: Session,
    documento: Documento,
    procesamiento: dict[str, object],
) -> None:
    datos = dict(documento.datos_extraidos or {})
    datos["procesamiento_documental"] = procesamiento
    documento.datos_extraidos = datos
    auditoria.registrar(
        session,
        documento.tenant_id,
        "PROCESAMIENTO_DOCUMENTAL_COMPLETADO",
        "documento",
        documento.id,
        {
            "metodo": str(procesamiento.get("metodo", "")),
            "motor": str(procesamiento.get("motor", "")),
            "requiere_ocr": procesamiento.get("requiere_ocr") is True,
        },
    )


def registrar_fallo(
    session: Session,
    documento: Documento,
    motivo: str,
) -> ResultadoAutomatizacion:
    _guardar_estado(documento, "FALLIDO", (motivo,))
    auditoria.registrar(
        session,
        documento.tenant_id,
        "PROCESAMIENTO_DOCUMENTAL_FALLIDO",
        "documento",
        documento.id,
        {"motivo": motivo},
    )
    return ResultadoAutomatizacion("FALLIDO", motivos=(motivo,))


def aplicar_automaticamente(
    session: Session,
    settings: Settings,
    hoy: date,
    documento: Documento,
    procesamiento: dict[str, object],
) -> ResultadoAutomatizacion:
    if documento.expediente_id is not None:
        _reparar_partes_vinculadas(session, settings, documento, procesamiento)
        resultado = ResultadoAutomatizacion(
            "COMPLETADO", relacionado=True, expediente_id=documento.expediente_id
        )
        _guardar_estado(documento, resultado.estado, expediente_id=documento.expediente_id)
        return resultado

    sugerencia = procesamiento.get("clasificacion_sugerida")
    tipo, confianza_clasificacion = _clasificacion(sugerencia)
    motivos: list[str] = []
    if tipo is None:
        motivos.append("No se pudo determinar el tipo documental")
    elif confianza_clasificacion < settings.confianza_minima_clasificacion:
        motivos.append(
            "La confianza de clasificación "
            f"({confianza_clasificacion:.0%}) es menor al mínimo "
            f"({settings.confianza_minima_clasificacion:.0%})"
        )
    else:
        documento.tipo_documento = tipo
        documento.estado = EstadoDocumento.PENDIENTE_RELACION

    if tipo not in (TipoDocumento.FACT, TipoDocumento.RHE):
        if tipo is not None and not motivos:
            motivos.append("El tipo documental requiere relacionarse con un expediente existente")
        return _revision(documento, motivos)

    extraccion = procesamiento.get("extraccion_estructurada")
    campos, confianzas, candidatos = _leer_extraccion(extraccion)
    _completar_rucs(campos, confianzas, candidatos, settings.tenant_ruc)

    faltantes = [campo for campo in CAMPOS_FISCALES if campo not in campos]
    if faltantes:
        motivos.append("Faltan campos fiscales: " + ", ".join(faltantes))
    baja_confianza = [
        campo
        for campo in CAMPOS_FISCALES
        if campo in confianzas and confianzas[campo] < settings.confianza_minima_expediente
    ]
    if baja_confianza:
        motivos.append("Campos con baja confianza: " + ", ".join(baja_confianza))
    if settings.tenant_ruc and campos.get("ruc_receptor") not in (None, settings.tenant_ruc):
        motivos.append("El RUC receptor no coincide con el RUC configurado para la empresa")
    if campos.get("ruc_emisor") == campos.get("ruc_receptor") and campos.get("ruc_emisor"):
        motivos.append("El RUC emisor y receptor no pueden ser iguales")
    if motivos:
        return _revision(documento, motivos)

    try:
        tipo_comprobante = TipoComprobante(tipo.value)
        serie = campos["serie"].upper()
        correlativo = str(int(campos["correlativo"]))
        emisor_ruc = campos["ruc_emisor"]
        receptor_ruc = campos["ruc_receptor"]
        fecha_emision = date.fromisoformat(campos["fecha_emision"])
        moneda = Moneda(campos["moneda"])
        importe_total = Decimal(campos["importe_total"])
    except (KeyError, ValueError, InvalidOperation) as exc:
        return _revision(documento, [f"Los campos fiscales no tienen un formato válido: {exc}"])

    campos_confirmados = {campo: campos[campo] for campo in CAMPOS_FISCALES}
    for opcional in ("razon_social_emisor", "razon_social_receptor"):
        if (
            opcional in campos
            and confianzas.get(opcional, 0) >= settings.confianza_minima_expediente
        ):
            campos_confirmados[opcional] = campos[opcional]
    confirmacion = {
        "version": 2,
        "origen": "AUTOMATICA",
        "confianza_minima": min(confianzas[campo] for campo in CAMPOS_FISCALES),
        "campos": campos_confirmados,
    }
    datos = dict(documento.datos_extraidos or {})
    datos["extraccion_confirmada"] = confirmacion
    documento.datos_extraidos = datos
    auditoria.registrar(
        session,
        documento.tenant_id,
        "EXTRACCION_DOCUMENTAL_VALIDADA_AUTOMATICAMENTE",
        "documento",
        documento.id,
        {
            "campos": list(CAMPOS_FISCALES),
            "confianza_minima": confirmacion["confianza_minima"],
        },
    )

    razon_emisor = campos.get("razon_social_emisor", emisor_ruc).strip() or emisor_ruc
    razon_receptor = campos.get("razon_social_receptor", receptor_ruc).strip() or receptor_ruc
    obtener_o_crear_empresa(session, documento.tenant_id, emisor_ruc, razon_emisor)
    obtener_o_crear_empresa(session, documento.tenant_id, receptor_ruc, razon_receptor)

    expediente = buscar_expediente(
        session,
        documento.tenant_id,
        tipo_comprobante,
        serie,
        correlativo,
        emisor_ruc,
        receptor_ruc,
    )
    creado = expediente is None
    if expediente is None:
        expediente = crear_expediente(
            session,
            settings,
            hoy,
            documento.tenant_id,
            receptor=(receptor_ruc, razon_receptor),
            emisor=(emisor_ruc, razon_emisor),
            tipo_comprobante=tipo_comprobante,
            serie=serie,
            correlativo=correlativo,
            fecha_emision=fecha_emision,
            moneda=moneda,
            importe_total=importe_total,
            requiere_guia=tipo_comprobante == TipoComprobante.FACT,
            gestor_id=documento.gestor_id,
        )
    vincular_documento(session, settings, hoy, documento, expediente.id, tipo)
    _guardar_estado(documento, "COMPLETADO", expediente_id=expediente.id, creado=creado)
    auditoria.registrar(
        session,
        documento.tenant_id,
        "DOCUMENTO_AUTOMATIZADO",
        "documento",
        documento.id,
        {"expediente_id": str(expediente.id), "expediente_creado": creado},
    )
    return ResultadoAutomatizacion("COMPLETADO", relacionado=True, expediente_id=expediente.id)


def _reparar_partes_vinculadas(
    session: Session,
    settings: Settings,
    documento: Documento,
    procesamiento: dict[str, object],
) -> None:
    expediente = documento.expediente
    if expediente is None:
        return
    extraccion = procesamiento.get("extraccion_estructurada")
    campos, confianzas, _ = _leer_extraccion(extraccion)
    for nombre, ruc_campo, empresa in (
        ("razon_social_emisor", "ruc_emisor", expediente.emisor),
        ("razon_social_receptor", "ruc_receptor", expediente.receptor),
    ):
        razon = campos.get(nombre, "").strip()
        if not razon or confianzas.get(nombre, 0) < settings.confianza_minima_expediente:
            continue
        ruc_extraido = campos.get(ruc_campo)
        if ruc_extraido and ruc_extraido != empresa.ruc:
            continue
        razon_actual = empresa.razon_social.strip()
        if razon_actual == empresa.ruc or razon_actual.startswith(empresa.ruc):
            empresa.razon_social = razon[:300]
            session.flush()
        else:
            obtener_o_crear_empresa(
                session,
                documento.tenant_id,
                empresa.ruc,
                razon,
            )


def _clasificacion(sugerencia: object) -> tuple[TipoDocumento | None, float]:
    if not isinstance(sugerencia, dict):
        return None, 0.0
    try:
        tipo = TipoDocumento(str(sugerencia.get("tipo")))
        confianza = float(sugerencia.get("confianza", 0))
    except (TypeError, ValueError):
        return None, 0.0
    return tipo, confianza


def _leer_extraccion(
    extraccion: object,
) -> tuple[dict[str, str], dict[str, float], list[tuple[str, float]]]:
    valores: dict[str, str] = {}
    confianzas: dict[str, float] = {}
    candidatos: list[tuple[str, float]] = []
    if not isinstance(extraccion, dict):
        return valores, confianzas, candidatos
    campos = extraccion.get("campos")
    if isinstance(campos, dict):
        for nombre, dato in campos.items():
            if not isinstance(dato, dict) or dato.get("valor") is None:
                continue
            valores[str(nombre)] = str(dato["valor"]).strip()
            try:
                confianzas[str(nombre)] = float(dato.get("confianza", 0))
            except (TypeError, ValueError):
                confianzas[str(nombre)] = 0.0
    todos = extraccion.get("candidatos")
    if isinstance(todos, dict) and isinstance(todos.get("ruc"), list):
        for candidato in todos["ruc"]:
            if not isinstance(candidato, dict) or candidato.get("valor") is None:
                continue
            try:
                candidatos.append((str(candidato["valor"]), float(candidato.get("confianza", 0))))
            except (TypeError, ValueError):
                continue
    return valores, confianzas, candidatos


def _completar_rucs(
    campos: dict[str, str],
    confianzas: dict[str, float],
    candidatos: list[tuple[str, float]],
    tenant_ruc: str | None,
) -> None:
    candidatos_unicos = {ruc: confianza for ruc, confianza in candidatos if len(ruc) == 11}
    if tenant_ruc and len(tenant_ruc) == 11 and tenant_ruc.isdigit():
        if tenant_ruc in candidatos_unicos or campos.get("ruc_receptor") == tenant_ruc:
            campos["ruc_receptor"] = tenant_ruc
            confianzas["ruc_receptor"] = max(
                confianzas.get("ruc_receptor", 0), candidatos_unicos.get(tenant_ruc, 1.0)
            )
        otros = [
            (ruc, confianza) for ruc, confianza in candidatos_unicos.items() if ruc != tenant_ruc
        ]
        if "ruc_emisor" not in campos and len(otros) == 1:
            campos["ruc_emisor"], confianzas["ruc_emisor"] = otros[0]

    if "ruc_emisor" in campos and "ruc_receptor" not in campos:
        otros = [
            (ruc, confianza)
            for ruc, confianza in candidatos_unicos.items()
            if ruc != campos["ruc_emisor"]
        ]
        if len(otros) == 1:
            campos["ruc_receptor"], confianzas["ruc_receptor"] = otros[0]
    if "ruc_receptor" in campos and "ruc_emisor" not in campos:
        otros = [
            (ruc, confianza)
            for ruc, confianza in candidatos_unicos.items()
            if ruc != campos["ruc_receptor"]
        ]
        if len(otros) == 1:
            campos["ruc_emisor"], confianzas["ruc_emisor"] = otros[0]


def _revision(documento: Documento, motivos: list[str]) -> ResultadoAutomatizacion:
    unicos = tuple(dict.fromkeys(motivos or ["El documento requiere revisión manual"]))
    _guardar_estado(documento, "REVISION_REQUERIDA", unicos)
    return ResultadoAutomatizacion("REVISION_REQUERIDA", motivos=unicos)


def _guardar_estado(
    documento: Documento,
    estado: str,
    motivos: tuple[str, ...] = (),
    expediente_id: uuid.UUID | None = None,
    creado: bool | None = None,
) -> None:
    resultado: dict[str, object] = {"version": 1, "estado": estado}
    if motivos:
        resultado["motivos"] = list(motivos)
    if expediente_id is not None:
        resultado["expediente_id"] = str(expediente_id)
    if creado is not None:
        resultado["expediente_creado"] = creado
    datos = dict(documento.datos_extraidos or {})
    datos["automatizacion_documental"] = resultado
    documento.datos_extraidos = datos
