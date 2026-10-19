"""Solicitudes MISD: registro y decisión; nunca ejecuta eliminación física/lógica."""

import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import OperativeAuthDep, SessionDep, TenantDep
from app.models import Expediente, Gestor, Miembro, SolicitudRetiroMISD, ahora
from app.services import auditoria
from app.services.misd_pagos import motivo_bloqueo_liquidacion
from app.services.permisos import PERMISO_ELIMINAR_REGISTROS, permiso_habilitado

router = APIRouter(prefix="/misd/solicitudes", tags=["misd"])


class SolicitarRetiro(BaseModel):
    expediente_id: uuid.UUID
    motivo: str = Field(min_length=8, max_length=500)


class ResolverRetiro(BaseModel):
    aprobar: bool
    motivo: str = Field(min_length=8, max_length=500)


def _ambito(expediente: Expediente, auth: OperativeAuthDep, session: SessionDep) -> bool:
    if auth.rol == "GESTOR":
        return auth.gestor_id is not None and expediente.gestor_id == auth.gestor_id
    if auth.rol == "USUARIO":
        return auth.usuario_id is not None and expediente.usuario_id == auth.usuario_id
    if auth.rol == "RESPONSABLE":
        return bool(
            auth.miembro_id
            and session.scalar(
                select(Miembro.id).where(
                    Miembro.id == expediente.usuario_id,
                    Miembro.tenant_id == expediente.tenant_id,
                    Miembro.responsable_id == auth.miembro_id,
                    Miembro.deleted_at.is_(None),
                )
            )
        )
    return auth.rol == "ADMINISTRADOR"


def _es_aprobador(
    solicitud: SolicitudRetiroMISD, expediente: Expediente, auth: OperativeAuthDep,
    session: SessionDep,
) -> bool:
    if auth.rol == "ADMINISTRADOR":
        return True
    if auth.rol == "RESPONSABLE" and auth.miembro_id is not None:
        return bool(
            session.scalar(
                select(Miembro.id).where(
                    Miembro.id == expediente.usuario_id,
                    Miembro.tenant_id == expediente.tenant_id,
                    Miembro.responsable_id == auth.miembro_id,
                    Miembro.deleted_at.is_(None),
                )
            )
        ) and solicitud.solicitante_rol in ("GESTOR", "USUARIO")
    if auth.rol == "USUARIO" and solicitud.solicitante_rol == "GESTOR":
        return auth.usuario_id is not None and expediente.usuario_id == auth.usuario_id
    return False


@router.post("", status_code=status.HTTP_201_CREATED)
def solicitar(
    datos: SolicitarRetiro, session: SessionDep, tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, str]:
    expediente = session.scalar(
        select(Expediente).where(
            Expediente.id == datos.expediente_id,
            Expediente.tenant_id == tenant_id,
            Expediente.deleted_at.is_(None),
        )
    )
    if expediente is None or not _ambito(expediente, auth, session):
        raise HTTPException(404, "Expediente no encontrado")
    if not permiso_habilitado(session, tenant_id, auth.rol, PERMISO_ELIMINAR_REGISTROS):
        raise HTTPException(403, "Sin permiso para solicitar retirada")
    if motivo_bloqueo_liquidacion(session, expediente) is not None:
        raise HTTPException(409, "Expediente bloqueado por liquidación generada")
    pendiente = session.scalar(
        select(SolicitudRetiroMISD.id).where(
            SolicitudRetiroMISD.tenant_id == tenant_id,
            SolicitudRetiroMISD.expediente_id == expediente.id,
            SolicitudRetiroMISD.estado == "PENDIENTE",
        )
    )
    if pendiente is not None:
        raise HTTPException(409, "Ya existe una solicitud pendiente")
    nueva = SolicitudRetiroMISD(
        tenant_id=tenant_id,
        expediente_id=expediente.id,
        solicitante_cuenta_id=auth.cuenta_id,
        solicitante_rol=auth.rol,
        solicitante_miembro_id=auth.miembro_id,
        solicitante_gestor_id=auth.gestor_id,
        motivo=datos.motivo.strip(),
        estado="PENDIENTE",
        notificado_a={"roles": ["ADMINISTRADOR", "RESPONSABLE", "USUARIO"]},
    )
    session.add(nueva)
    session.flush()
    auditoria.registrar(
        session, tenant_id, "MISD_SOLICITUD_RETIRO", "solicitud_retiro", nueva.id,
        {"expediente_id": str(expediente.id), "solicitante_rol": auth.rol},
    )
    session.commit()
    return {"id": str(nueva.id), "estado": nueva.estado}


@router.get("")
def listar(
    session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep,
) -> list[dict[str, str]]:
    consultas = session.scalars(
        select(SolicitudRetiroMISD).where(
            SolicitudRetiroMISD.tenant_id == tenant_id,
        ).order_by(SolicitudRetiroMISD.created_at.desc()).limit(200)
    )
    resultado = []
    for solicitud in consultas:
        expediente = session.get(Expediente, solicitud.expediente_id)
        if expediente is None:
            continue
        if solicitud.solicitante_cuenta_id != auth.cuenta_id and not _es_aprobador(
            solicitud, expediente, auth, session
        ):
            continue
        resultado.append({
            "id": str(solicitud.id),
            "expediente_id": str(solicitud.expediente_id),
            "estado": solicitud.estado,
            "rol_solicitante": solicitud.solicitante_rol,
        })
    return resultado


@router.post("/{solicitud_id}/resolver")
def resolver(
    solicitud_id: uuid.UUID, datos: ResolverRetiro, session: SessionDep,
    tenant_id: TenantDep, auth: OperativeAuthDep,
) -> dict[str, str]:
    solicitud = session.scalar(
        select(SolicitudRetiroMISD).where(
            SolicitudRetiroMISD.id == solicitud_id,
            SolicitudRetiroMISD.tenant_id == tenant_id,
        ).with_for_update()
    )
    if solicitud is None:
        raise HTTPException(404, "Solicitud no encontrada")
    expediente = session.get(Expediente, solicitud.expediente_id)
    if expediente is None or expediente.tenant_id != tenant_id or not _es_aprobador(
        solicitud, expediente, auth, session
    ):
        raise HTTPException(404, "Solicitud no encontrada")
    if solicitud.solicitante_cuenta_id == auth.cuenta_id:
        raise HTTPException(403, "El solicitante no puede aprobar su propia solicitud")
    if solicitud.estado != "PENDIENTE":
        raise HTTPException(409, "Solicitud ya resuelta")
    if datos.aprobar and (
        expediente.deleted_at is not None
        or motivo_bloqueo_liquidacion(session, expediente) is not None
    ):
        raise HTTPException(409, "El expediente ya no admite retiro")
    solicitud.estado = "APROBADA" if datos.aprobar else "RECHAZADA"
    solicitud.aprobado_por_cuenta_id = auth.cuenta_id
    solicitud.decidido_at = ahora()
    solicitud.decision_motivo = datos.motivo.strip()
    auditoria.registrar(
        session, tenant_id, "MISD_SOLICITUD_RESUELTA", "solicitud_retiro",
        solicitud.id, {"estado": solicitud.estado, "expediente_id": str(expediente.id)},
    )
    session.commit()
    # Aprobar no elimina: requiere ejecución MISD independiente y revalidada.
    return {"id": str(solicitud.id), "estado": solicitud.estado}
