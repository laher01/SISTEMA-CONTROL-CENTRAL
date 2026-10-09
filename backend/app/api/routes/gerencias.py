"""Vínculos operativos entre Gerentes y Responsables, controlados por Administración."""

import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import OperativeAuthDep, SessionDep, TenantDep
from app.enums import RolMiembro
from app.models import GerenteResponsable, Miembro
from app.services import auditoria

router = APIRouter(prefix="/gerencias", tags=["gerencias"])


class VinculoIn(BaseModel):
    gerente_id: uuid.UUID
    responsable_id: uuid.UUID
    activo: bool = True


class VinculoOut(BaseModel):
    id: uuid.UUID
    gerente_id: uuid.UUID
    responsable_id: uuid.UUID
    activo: bool


def _administracion(auth: OperativeAuthDep) -> None:
    if auth.rol not in (RolMiembro.SUPERADMIN, RolMiembro.ADMINISTRADOR):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Administración puede asignar equipos")


def _miembro_activo(
    session: SessionDep, tenant_id: uuid.UUID, miembro_id: uuid.UUID, rol: str
) -> Miembro:
    miembro = session.get(Miembro, miembro_id)
    if (
        miembro is None
        or miembro.tenant_id != tenant_id
        or miembro.rol != rol
        or not miembro.activo
        or miembro.deleted_at is not None
    ):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Miembro no disponible")
    return miembro


@router.get("/vinculos", response_model=list[VinculoOut])
def vinculos(
    session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep
) -> list[GerenteResponsable]:
    if auth.rol not in (
        RolMiembro.SUPERADMIN,
        RolMiembro.ADMINISTRADOR,
        RolMiembro.GERENTE,
        RolMiembro.RESPONSABLE,
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin acceso")
    query = select(GerenteResponsable).where(GerenteResponsable.tenant_id == tenant_id)
    if auth.rol == RolMiembro.GERENTE:
        if auth.miembro_id is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Gerente sin identidad")
        query = query.where(GerenteResponsable.gerente_id == auth.miembro_id)
    if auth.rol == RolMiembro.RESPONSABLE:
        if auth.miembro_id is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Responsable sin identidad")
        query = query.where(GerenteResponsable.responsable_id == auth.miembro_id)
    return list(session.scalars(query.order_by(GerenteResponsable.created_at)))


@router.put("/vinculos", response_model=VinculoOut)
def asignar(
    datos: VinculoIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> GerenteResponsable:
    _administracion(auth)
    _miembro_activo(session, tenant_id, datos.gerente_id, RolMiembro.GERENTE)
    _miembro_activo(session, tenant_id, datos.responsable_id, RolMiembro.RESPONSABLE)
    relacion = session.scalar(
        select(GerenteResponsable).where(
            GerenteResponsable.tenant_id == tenant_id,
            GerenteResponsable.gerente_id == datos.gerente_id,
            GerenteResponsable.responsable_id == datos.responsable_id,
        )
    )
    if relacion is None:
        relacion = GerenteResponsable(
            tenant_id=tenant_id,
            gerente_id=datos.gerente_id,
            responsable_id=datos.responsable_id,
            activo=datos.activo,
        )
        session.add(relacion)
    else:
        relacion.activo = datos.activo
    session.flush()
    auditoria.registrar(
        session,
        tenant_id,
        "GERENCIA_RESPONSABLE_VINCULO",
        "gerentes_responsables",
        relacion.id,
        {
            "gerente_id": str(datos.gerente_id),
            "responsable_id": str(datos.responsable_id),
            "activo": datos.activo,
            "actor": auth.codigo,
        },
    )
    session.commit()
    session.refresh(relacion)
    return relacion
