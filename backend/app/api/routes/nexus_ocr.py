"""API administrativa de la cola OCR; no expone originales ni permite despliegues."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import OperativeAuthDep, SessionDep, TenantDep
from app.enums import RolMiembro
from app.models import CasoOcr, Documento
from app.services.casos_ocr import clave_diagnostico, registrar_caso, serializar_caso

router = APIRouter(prefix="/nexus/ocr", tags=["nexus-ocr"])


def _admin(auth: OperativeAuthDep) -> None:
    if auth.rol not in (RolMiembro.ADMINISTRADOR, RolMiembro.SUPERADMIN):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo administradores")


@router.get("/casos")
def listar_casos(
    session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep
) -> list[dict[str, object]]:
    _admin(auth)
    consulta = (
        select(CasoOcr)
        .where(CasoOcr.tenant_id == tenant_id)
        .order_by(CasoOcr.created_at.desc())
        .limit(100)
    )
    return [serializar_caso(caso) for caso in session.scalars(consulta)]


@router.get("/casos/{caso_id}")
def ver_caso(
    caso_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, object]:
    _admin(auth)
    caso = session.scalar(
        select(CasoOcr).where(CasoOcr.id == caso_id, CasoOcr.tenant_id == tenant_id)
    )
    if caso is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Caso no encontrado")
    return {**serializar_caso(caso), "referencia_chat": clave_diagnostico(caso.id)}


@router.post("/documentos/{documento_id}/diagnostico")
def crear_diagnostico(
    documento_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, object]:
    """Registra un fallo ya documentado; nunca ejecuta OCR ni crea expediente."""
    _admin(auth)
    documento = session.scalar(
        select(Documento).where(
            Documento.id == documento_id,
            Documento.tenant_id == tenant_id,
            Documento.deleted_at.is_(None),
        )
    )
    if documento is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado")
    caso = registrar_caso(session, documento)
    if caso is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Documento sin fallo OCR diagnosticable")
    session.commit()
    return {**serializar_caso(caso), "referencia_chat": clave_diagnostico(caso.id)}
