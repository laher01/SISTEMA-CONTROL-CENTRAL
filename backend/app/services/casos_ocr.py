"""Gestión auditada de incidencias OCR, sin exportar documentos a GitHub."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CasoOcr, Documento
from app.services import auditoria

ESTADOS = frozenset({"PENDIENTE", "EN_DIAGNOSTICO", "VALIDACION", "REPROCESADO", "BLOQUEADO"})
ESTADOS_FALLO = frozenset({"FALLIDO", "REVISION_REQUERIDA", "PENDIENTE_FACTURA"})


def motivo_pendiente(documento: Documento) -> str | None:
    """Crear incidencias solo desde fallos existentes, no según el nombre del archivo."""
    datos = documento.datos_extraidos or {}
    automatizacion = datos.get("automatizacion_documental")
    if not isinstance(automatizacion, dict):
        return None
    estado = automatizacion.get("estado")
    if estado not in ESTADOS_FALLO:
        return None
    # No persistir fragmentos OCR, números de cuenta, RUC ni PII en diagnóstico.
    return str(estado)


def registrar_caso(session: Session, documento: Documento) -> CasoOcr | None:
    """Idempotencia por tenant/documento. Nunca crear otra factura."""
    motivo = motivo_pendiente(documento)
    if motivo is None:
        return None
    caso = session.scalar(
        select(CasoOcr).where(
            CasoOcr.tenant_id == documento.tenant_id,
            CasoOcr.documento_id == documento.id,
        )
    )
    if caso is None:
        caso = CasoOcr(
            tenant_id=documento.tenant_id,
            documento_id=documento.id,
            estado="PENDIENTE",
            motivo=motivo,
            intentos=0,
        )
        session.add(caso)
        session.flush()
        auditoria.registrar(
            session,
            documento.tenant_id,
            "CASO_OCR_CREADO",
            "documento",
            documento.id,
            {"caso_id": str(caso.id), "motivo": motivo},
        )
    return caso


def serializar_caso(caso: CasoOcr) -> dict[str, object]:
    """Sin rutas de almacenamiento, texto OCR, RUC ni datos bancarios."""
    return {
        "id": str(caso.id),
        "documento_id": str(caso.documento_id),
        "estado": caso.estado,
        "motivo": caso.motivo,
        "intentos": caso.intentos,
        "regla_version": caso.regla_version,
    }


def clave_diagnostico(caso_id: uuid.UUID) -> str:
    """Identificador estable para que un chat conectado consulte el caso autorizado."""
    return f"OCR-{caso_id}"
