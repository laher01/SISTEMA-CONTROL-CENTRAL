"""Diagnóstico P0 de SCORPIO: 100 % lectura; no corrige la base de datos.

No tomar números del nombre del archivo como prueba fiscal: se contrastan
con el texto interno del PDF, su hash SHA256 y el emisor/receptor.
"""
import hashlib
import io
from dataclasses import asdict, dataclass

from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import TipoComprobante
from app.services import auditoria
from app.models import Documento, Empresa, Expediente
from app.services.facturas_estaciones import extraer_factura_estacion
from app.storage import AlmacenLocal

RUC_ESCORPIO = "20516453835"
OBJETIVOS = {
    "20605535098": "0016490",  # BORISO
    "20614966174": "0016491",  # B2C MUSA
    "20478053763": "0016492",  # HERNANDEZ
    "20611909234": "0016493",  # FRUTTI
    "20524049245": "0016494",  # LATINOAMERICANO
    "20538820050": "0016497",  # REQUE
}


@dataclass(frozen=True)
class Diagnostico:
    expediente_id: str
    documento_id: str | None
    receptor_ruc: str
    antes: str
    despues: str | None
    evidencia: str
    estado: str
    motivo: str
    auditoria_propuesta: dict[str, str]


def evaluar_identidad(
    *,
    actual_serie: str,
    actual_correlativo: str,
    esperado: str,
    receptor_ruc: str,
    texto_pdf: str,
) -> tuple[str, str]:
    """No confiar en nombre de archivo, fecha ni importes para inferir identidad."""
    campos = extraer_factura_estacion(texto_pdf)
    numero = campos.get("correlativo", ("", ""))[0]
    serie = campos.get("serie", ("", ""))[0]
    emisor = campos.get("ruc_emisor", ("", ""))[0]
    receptor = campos.get("ruc_receptor", ("", ""))[0]
    if (serie, numero, emisor, receptor) != (
        "F109", esperado, RUC_ESCORPIO, receptor_ruc
    ):
        return "BLOQUEADO", "Identidad fiscal no confirmada dentro del PDF"
    if (actual_serie, actual_correlativo) == ("F109", str(int(esperado))):
        return "YA_CORREGIDO", "La clave fiscal ya coincide"
    if (actual_serie, actual_correlativo) != ("2026", "10"):
        return "BLOQUEADO", "Valor anterior no coincide con la incidencia identificada"
    return "CANDIDATO", "Serie, correlativo, emisor y receptor verificados en PDF"


def diagnosticar(session: Session, almacen: AlmacenLocal, tenant_id) -> list[Diagnostico]:
    """Vista previa; no utiliza flush, commit, ni escribe auditoría en BD."""
    expedientes = list(
        session.scalars(
            select(Expediente)
            .join(Empresa, Expediente.emisor_id == Empresa.id)
            .where(
                Expediente.tenant_id == tenant_id,
                Expediente.deleted_at.is_(None),
                Expediente.tipo_comprobante == TipoComprobante.FACT,
                Empresa.ruc == RUC_ESCORPIO,
            )
        )
    )
    resultados = []
    for expediente in expedientes:
        receptor_ruc = session.scalar(select(Empresa.ruc).where(Empresa.id == expediente.receptor_id))
        if receptor_ruc not in OBJETIVOS:
            continue
        esperado = OBJETIVOS[receptor_ruc]
        docs = list(
            session.scalars(
                select(Documento).where(
                    Documento.tenant_id == tenant_id,
                    Documento.expediente_id == expediente.id,
                    Documento.deleted_at.is_(None),
                    Documento.tipo_documento == "FACT",
                )
            )
        )
        estado, motivo, documento_id = "BLOQUEADO", "Se requiere un solo PDF de factura", None
        evidencia = ""
        if len(docs) == 1 and docs[0].mime_type == "application/pdf":
            documento = docs[0]
            documento_id = str(documento.id)
            try:
                bytes_pdf = almacen.leer(documento.ruta_storage)
                if hashlib.sha256(bytes_pdf).hexdigest() != documento.sha256:
                    motivo = "Hash del original no coincide"
                else:
                    lector = PdfReader(io.BytesIO(bytes_pdf))
                    texto = "\n".join(p.extract_text() or "" for p in lector.pages[:10])
                    estado, motivo = evaluar_identidad(
                        actual_serie=expediente.serie,
                        actual_correlativo=expediente.correlativo,
                        esperado=esperado,
                        receptor_ruc=receptor_ruc,
                        texto_pdf=texto,
                    )
                    evidencia = hashlib.sha256(bytes_pdf).hexdigest()
            except Exception as exc:
                motivo = f"No se pudo comprobar el PDF ({type(exc).__name__})"
        if estado == "CANDIDATO":
            duplicados = list(
                session.scalars(
                    select(Expediente.id).where(
                        Expediente.tenant_id == tenant_id,
                        Expediente.deleted_at.is_(None),
                        Expediente.emisor_id == expediente.emisor_id,
                        Expediente.receptor_id == expediente.receptor_id,
                        Expediente.tipo_comprobante == TipoComprobante.FACT,
                        Expediente.serie == "F109",
                        Expediente.correlativo == str(int(esperado)),
                        Expediente.id != expediente.id,
                    )
                )
            )
            if duplicados:
                estado, motivo = "BLOQUEADO", "Colisión con expediente fiscal existente"
        antes = f"{expediente.serie}-{expediente.correlativo}"
        despues = f"F109-{esperado}" if estado == "CANDIDATO" else None
        resultados.append(
            Diagnostico(
                expediente_id=str(expediente.id), documento_id=documento_id,
                receptor_ruc=receptor_ruc, antes=antes, despues=despues,
                evidencia=evidencia, estado=estado, motivo=motivo,
                auditoria_propuesta={
                    "accion": "ESCORPIO_CORRECCION_HISTORICA_P0",
                    "antes": antes, "despues": despues or "",
                    "pdf_sha256": evidencia, "documento_id": documento_id or "",
                },
            )
        )
    return resultados


def vista_previa(session: Session, almacen: AlmacenLocal, tenant_id) -> list[dict]:
    return [asdict(item) for item in diagnosticar(session, almacen, tenant_id)]


class ReparacionBloqueada(ValueError):
    """La base no coincide con la vista previa autorizada."""


def aplicar_lote_verificado(
    session: Session,
    almacen: AlmacenLocal,
    tenant_id,
    aprobaciones: list[dict[str, str]],
) -> list[str]:
    """Aplica seis reparaciones exactas en una sola transacción.

    El llamador confirma/ejecuta commit; un fallo obliga a rollback.
    Todas las evidencias se recalculan después de bloquear expedientes.
    """
    if len(aprobaciones) != 6:
        raise ReparacionBloqueada("Se requieren exactamente seis aprobaciones")
    ids = [a.get("expediente_id") for a in aprobaciones]
    if len(set(ids)) != 6 or any(not item for item in ids):
        raise ReparacionBloqueada("Identificadores repetidos o ausentes")

    from uuid import UUID

    try:
        uuids = [UUID(item) for item in ids]
    except ValueError as exc:
        raise ReparacionBloqueada("Identificador inválido") from exc

    bloqueados = list(
        session.scalars(
            select(Expediente)
            .where(
                Expediente.tenant_id == tenant_id,
                Expediente.id.in_(uuids),
                Expediente.deleted_at.is_(None),
            )
            .order_by(Expediente.id)
            .with_for_update()
        )
    )
    if len(bloqueados) != 6:
        raise ReparacionBloqueada("Uno o más expedientes no están disponibles")
    por_id = {str(e.id): e for e in bloqueados}
    propuestas = diagnosticar(session, almacen, tenant_id)
    candidatos = {p.expediente_id: p for p in propuestas if p.estado == "CANDIDATO"}
    if set(ids) != set(candidatos):
        raise ReparacionBloqueada("La vista previa ha cambiado o existen candidatos distintos")

    for aprobacion in aprobaciones:
        p = candidatos[aprobacion["expediente_id"]]
        if (
            aprobacion.get("antes") != p.antes
            or aprobacion.get("despues") != p.despues
            or aprobacion.get("pdf_sha256") != p.evidencia
            or aprobacion.get("documento_id") != p.documento_id
        ):
            raise ReparacionBloqueada("Evidencia o estado diferente de la vista previa")

    for expediente_id in ids:
        p = candidatos[expediente_id]
        e = por_id[expediente_id]
        e.serie = "F109"
        e.correlativo = str(int(OBJETIVOS[p.receptor_ruc]))
        e.correlativo_original = OBJETIVOS[p.receptor_ruc]
        auditoria.registrar(
            session, tenant_id, "ESCORPIO_CORRECCION_HISTORICA_P0",
            "expediente", e.id,
            {**p.auditoria_propuesta, "correlativo_normalizado": e.correlativo},
        )
    session.flush()  # violaciones de unicidad abortan la transacción
    return ids
