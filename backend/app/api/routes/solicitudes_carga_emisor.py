"""Revisión de cargas de emisores ajenos: no son documentos fiscales activos."""

import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import AlmacenDep, OperativeAuthDep, SessionDep, TenantDep
from app.models import SolicitudCargaEmisor
from app.security import ContextoAcceso
from app.services import auditoria

router = APIRouter(prefix="/solicitudes-carga-emisor", tags=["solicitudes-carga-emisor"])


class Decision(BaseModel):
    observacion: str | None = None


class SolicitudOut(BaseModel):
    id: uuid.UUID
    ruc_emisor: str
    estado: str
    gestor_propietario_id: uuid.UUID | None
    responsable_propietario_id: uuid.UUID | None


def _puede_revisar(auth: ContextoAcceso, solicitud: SolicitudCargaEmisor) -> bool:
    return bool(
        auth.rol == "ADMINISTRADOR"
        or (auth.rol == "RESPONSABLE" and auth.miembro_id == solicitud.responsable_propietario_id)
    )


@router.get("", response_model=list[SolicitudOut])
def listar(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    estado: Literal["PENDIENTE", "APROBADA", "RECHAZADA"] = "PENDIENTE",
) -> list[SolicitudCargaEmisor]:
    consulta = select(SolicitudCargaEmisor).where(
        SolicitudCargaEmisor.tenant_id == tenant_id,
        SolicitudCargaEmisor.estado == estado,
    )
    if auth.rol == "RESPONSABLE":
        consulta = consulta.where(
            SolicitudCargaEmisor.responsable_propietario_id == auth.miembro_id
        )
    elif auth.rol != "ADMINISTRADOR":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Administración o Responsable")
    return list(session.scalars(consulta.order_by(SolicitudCargaEmisor.created_at.desc())))


@router.post("/{solicitud_id}/rechazar", response_model=SolicitudOut)
def rechazar(
    session: SessionDep,
    almacen: AlmacenDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    solicitud_id: uuid.UUID,
    datos: Decision,
) -> SolicitudCargaEmisor:
    solicitud = session.scalar(
        select(SolicitudCargaEmisor)
        .where(
            SolicitudCargaEmisor.id == solicitud_id,
            SolicitudCargaEmisor.tenant_id == tenant_id,
        )
        .with_for_update()
    )
    if solicitud is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitud no encontrada")
    if not _puede_revisar(auth, solicitud):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No puede decidir esta solicitud")
    if solicitud.solicitante_cuenta_id == auth.cuenta_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No puede decidir su propia solicitud")
    if solicitud.estado != "PENDIENTE":
        raise HTTPException(status.HTTP_409_CONFLICT, "Solicitud ya decidida")

    # Se conserva la ruta si no pudo borrarse, para permitir recuperación.
    ruta = solicitud.ruta_temporal
    if ruta:
        try:
            almacen.ruta_absoluta(ruta).unlink(missing_ok=True)
        except OSError as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "No se pudo eliminar el archivo en cuarentena",
            ) from exc
    solicitud.ruta_temporal = None
    solicitud.estado = "RECHAZADA"
    solicitud.observacion = datos.observacion
    solicitud.decidido_por_cuenta_id = auth.cuenta_id
    solicitud.decidido_at = datetime.now(UTC)
    auditoria.registrar(
        session,
        tenant_id,
        "CARGA_EMISOR_RECHAZADA",
        "solicitud_carga_emisor",
        solicitud.id,
        {"ruc_emisor": solicitud.ruc_emisor, "por": auth.codigo},
    )
    session.commit()
    return solicitud
