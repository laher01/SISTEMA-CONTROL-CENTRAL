"""Administración de titularidad de emisores por gestor, aislada por tenant."""

import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import OperativeAuthDep, SessionDep, TenantDep
from app.models import AsignacionEmpresaGestor, Empresa, Gestor, Miembro, ahora
from app.services import auditoria

router = APIRouter(prefix="/asignaciones-emisores", tags=["asignaciones-emisores"])


class AsignacionIn(BaseModel):
    empresa_id: uuid.UUID
    gestor_id: uuid.UUID
    responsable_id: uuid.UUID


class AsignacionOut(BaseModel):
    id: uuid.UUID
    empresa_id: uuid.UUID
    gestor_id: uuid.UUID
    usuario_id: uuid.UUID
    responsable_id: uuid.UUID
    activo: bool


def _administrador(auth: OperativeAuthDep) -> None:
    if auth.rol != "ADMINISTRADOR":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Requiere Administrador del tenant")


@router.get("", response_model=list[AsignacionOut])
def listar(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[AsignacionEmpresaGestor]:
    _administrador(auth)
    return list(
        session.scalars(
            select(AsignacionEmpresaGestor).where(
                AsignacionEmpresaGestor.tenant_id == tenant_id,
            )
        )
    )


@router.put("/{empresa_id}", response_model=AsignacionOut)
def asignar(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    empresa_id: uuid.UUID,
    datos: AsignacionIn,
) -> AsignacionEmpresaGestor:
    _administrador(auth)
    if datos.empresa_id != empresa_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Empresa no coincide")
    empresa = session.get(Empresa, empresa_id)
    gestor = session.get(Gestor, datos.gestor_id)
    responsable = session.get(Miembro, datos.responsable_id)
    if (
        empresa is None
        or empresa.tenant_id != tenant_id
        or empresa.deleted_at
        or gestor is None
        or gestor.tenant_id != tenant_id
        or gestor.deleted_at
        or responsable is None
        or responsable.tenant_id != tenant_id
        or responsable.deleted_at
        or not responsable.activo
        or responsable.rol != "RESPONSABLE"
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Empresa, gestor o responsable inválido"
        )
    usuario = session.get(Miembro, gestor.usuario_id) if gestor.usuario_id else None
    if (
        usuario is None
        or usuario.tenant_id != tenant_id
        or usuario.deleted_at
        or not usuario.activo
        or usuario.responsable_id != responsable.id
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Gestor no pertenece al responsable indicado"
        )

    asignacion = session.scalar(
        select(AsignacionEmpresaGestor)
        .where(
            AsignacionEmpresaGestor.tenant_id == tenant_id,
            AsignacionEmpresaGestor.empresa_id == empresa_id,
        )
        .with_for_update()
    )
    if asignacion is None:
        asignacion = AsignacionEmpresaGestor(
            tenant_id=tenant_id,
            empresa_id=empresa_id,
            gestor_id=gestor.id,
            usuario_id=usuario.id,
            responsable_id=responsable.id,
            creado_por_cuenta_id=auth.cuenta_id,
            activo=True,
        )
        session.add(asignacion)
    else:
        asignacion.gestor_id = gestor.id
        asignacion.usuario_id = usuario.id
        asignacion.responsable_id = responsable.id
        asignacion.activo = True
        asignacion.updated_at = ahora()
    session.flush()
    auditoria.registrar(
        session,
        tenant_id,
        "EMISOR_ASIGNADO",
        "empresa",
        empresa_id,
        {"gestor_id": str(gestor.id), "responsable_id": str(responsable.id)},
    )
    session.commit()
    return asignacion
