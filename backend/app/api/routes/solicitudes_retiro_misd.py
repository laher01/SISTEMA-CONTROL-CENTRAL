"""Solicitudes MISD: registro y decisión; nunca ejecuta eliminación física/lógica."""

import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import OperativeAuthDep, SessionDep, TenantDep
from app.models import ChatMensaje, CuentaAcceso, Expediente, Miembro, SolicitudRetiroMISD, ahora
from app.services import auditoria
from app.services.misd_autorizaciones import dentro_ventana_correccion
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
    solicitud: SolicitudRetiroMISD,
    expediente: Expediente,
    auth: OperativeAuthDep,
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



def _notificar(
    session: SessionDep,
    tenant_id: uuid.UUID,
    remitente: uuid.UUID,
    cuentas_destino: set[uuid.UUID],
    mensaje: str,
) -> None:
    """Notifica por la mensajería interna, siempre dentro del mismo tenant."""
    cuentas = session.scalars(
        select(CuentaAcceso).where(
            CuentaAcceso.tenant_id == tenant_id,
            CuentaAcceso.id.in_(cuentas_destino),
            CuentaAcceso.activo.is_(True),
            CuentaAcceso.deleted_at.is_(None),
        )
    )
    for cuenta in cuentas:
        if cuenta.id != remitente:
            session.add(
                ChatMensaje(
                    tenant_id=tenant_id,
                    remitente_cuenta_id=remitente,
                    destinatario_cuenta_id=cuenta.id,
                    texto=mensaje[:2000],
                )
            )


def _destinatarios_aprobacion(
    session: SessionDep, tenant_id: uuid.UUID, expediente: Expediente
) -> set[uuid.UUID]:
    ids = set(
        session.scalars(
            select(CuentaAcceso.id)
            .where(
                CuentaAcceso.tenant_id == tenant_id,
                CuentaAcceso.activo.is_(True),
                CuentaAcceso.deleted_at.is_(None),
                CuentaAcceso.miembro_id.in_(
                    select(Miembro.id).where(
                        Miembro.tenant_id == tenant_id,
                        Miembro.rol == "ADMINISTRADOR",
                        Miembro.deleted_at.is_(None),
                    )
                ),
            )
        )
    )
    if expediente.usuario_id is not None:
        usuario = session.get(Miembro, expediente.usuario_id)
        if usuario is not None and usuario.tenant_id == tenant_id:
            ids.update(
                session.scalars(
                    select(CuentaAcceso.id).where(
                        CuentaAcceso.tenant_id == tenant_id,
                        CuentaAcceso.miembro_id.in_(
                            [ident for ident in (usuario.id, usuario.responsable_id) if ident]
                        ),
                        CuentaAcceso.activo.is_(True),
                        CuentaAcceso.deleted_at.is_(None),
                    )
                )
            )
    return ids


@router.post("", status_code=status.HTTP_201_CREATED)
def solicitar(
    datos: SolicitarRetiro,
    session: SessionDep,
    tenant_id: TenantDep,
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
    destinatarios = _destinatarios_aprobacion(session, tenant_id, expediente)
    _notificar(
        session,
        tenant_id,
        auth.cuenta_id,
        destinatarios,
        f"MISD: solicitud de retiro pendiente para expediente {expediente.id}. "
        f"Motivo: {nueva.motivo}",
    )
    auditoria.registrar(
        session,
        tenant_id,
        "MISD_SOLICITUD_RETIRO",
        "solicitud_retiro",
        nueva.id,
        {"expediente_id": str(expediente.id), "solicitante_rol": auth.rol},
    )
    session.commit()
    return {"id": str(nueva.id), "estado": nueva.estado}


@router.get("")
def listar(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[dict[str, str]]:
    consultas = session.scalars(
        select(SolicitudRetiroMISD)
        .where(
            SolicitudRetiroMISD.tenant_id == tenant_id,
        )
        .order_by(SolicitudRetiroMISD.created_at.desc())
        .limit(200)
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
        resultado.append(
            {
                "id": str(solicitud.id),
                "expediente_id": str(solicitud.expediente_id),
                "estado": solicitud.estado,
                "rol_solicitante": solicitud.solicitante_rol,
            }
        )
    return resultado


@router.post("/{solicitud_id}/resolver")
def resolver(
    solicitud_id: uuid.UUID,
    datos: ResolverRetiro,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, str]:
    solicitud = session.scalar(
        select(SolicitudRetiroMISD)
        .where(
            SolicitudRetiroMISD.id == solicitud_id,
            SolicitudRetiroMISD.tenant_id == tenant_id,
        )
        .with_for_update()
    )
    if solicitud is None:
        raise HTTPException(404, "Solicitud no encontrada")
    expediente = session.get(Expediente, solicitud.expediente_id)
    if (
        expediente is None
        or expediente.tenant_id != tenant_id
        or not _es_aprobador(solicitud, expediente, auth, session)
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
    _notificar(
        session,
        tenant_id,
        auth.cuenta_id,
        {solicitud.solicitante_cuenta_id},
        f"MISD: solicitud {solicitud.id} {solicitud.estado.lower()}. "
        f"Motivo: {solicitud.decision_motivo}",
    )
    auditoria.registrar(
        session,
        tenant_id,
        "MISD_SOLICITUD_RESUELTA",
        "solicitud_retiro",
        solicitud.id,
        {"estado": solicitud.estado, "expediente_id": str(expediente.id)},
    )
    session.commit()
    # Aprobar no elimina: requiere ejecución MISD independiente y revalidada.
    return {"id": str(solicitud.id), "estado": solicitud.estado}


@router.post("/{solicitud_id}/ejecutar")
def ejecutar(
    solicitud_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, str]:
    """Retirada lógica con autorización consumible y revalidación transaccional.

    Nunca destruye originales físicos ni pagos ni auditoría.
    """
    solicitud = session.scalar(
        select(SolicitudRetiroMISD)
        .where(
            SolicitudRetiroMISD.id == solicitud_id,
            SolicitudRetiroMISD.tenant_id == tenant_id,
        )
        .with_for_update()
    )
    if solicitud is None:
        raise HTTPException(404, "Solicitud no encontrada")
    expediente = session.scalar(
        select(Expediente)
        .where(Expediente.id == solicitud.expediente_id, Expediente.tenant_id == tenant_id)
        .with_for_update()
    )
    if expediente is None:
        raise HTTPException(404, "Expediente no encontrado")
    es_solicitante = auth.cuenta_id == solicitud.solicitante_cuenta_id
    if not es_solicitante or not _ambito(expediente, auth, session):
        raise HTTPException(404, "Solicitud no encontrada")
    if not permiso_habilitado(session, tenant_id, auth.rol, PERMISO_ELIMINAR_REGISTROS):
        raise HTTPException(403, "Sin permiso para ejecutar retiro")
    if solicitud.estado == "EJECUTADA":
        raise HTTPException(409, "Solicitud consumida previamente")
    if solicitud.estado == "RECHAZADA":
        raise HTTPException(409, "Solicitud rechazada")
    if expediente.deleted_at is not None:
        raise HTTPException(409, "Expediente ya retirado")
    if motivo_bloqueo_liquidacion(session, expediente) is not None:
        raise HTTPException(409, "Expediente bloqueado por liquidación generada")

    # La ventana NO prevalece sobre un cliente registrado protegido.
    aprobacion_necesaria = (
        expediente.receptor.autorizada and auth.rol != "ADMINISTRADOR"
    ) or (
        auth.rol in ("GESTOR", "USUARIO")
        and not dentro_ventana_correccion(expediente, ahora())
    )
    if aprobacion_necesaria and solicitud.estado != "APROBADA":
        raise HTTPException(409, "Se requiere aprobación jerárquica")
    if solicitud.estado not in ("PENDIENTE", "APROBADA"):
        raise HTTPException(409, "Solicitud en estado incompatible")
    if solicitud.estado == "APROBADA" and solicitud.aprobado_por_cuenta_id is None:
        raise HTTPException(409, "Aprobación sin cuenta responsable")

    # Bloquear documentos para serializar retiradas simultáneas del mismo expediente.
    from app.models import Documento

    session.scalars(
        select(Documento.id)
        .where(Documento.tenant_id == tenant_id, Documento.expediente_id == expediente.id)
        .with_for_update()
    ).all()
    marca = ahora()
    expediente.deleted_at = marca
    for documento in expediente.documentos:
        if documento.deleted_at is None:
            documento.deleted_at = marca
            auditoria.registrar(
                session,
                tenant_id,
                "DOCUMENTO_ELIMINADO_CON_EXPEDIENTE",
                "documento",
                documento.id,
                {"expediente_id": str(expediente.id), "sha256": documento.sha256},
            )
    solicitud.estado = "EJECUTADA"
    auditoria.registrar(
        session,
        tenant_id,
        "MISD_RETIRO_EJECUTADO",
        "solicitud_retiro",
        solicitud.id,
        {"expediente_id": str(expediente.id), "actor_cuenta_id": str(auth.cuenta_id)},
    )
    destinatarios = _destinatarios_aprobacion(session, tenant_id, expediente)
    if solicitud.aprobado_por_cuenta_id is not None:
        destinatarios.add(solicitud.aprobado_por_cuenta_id)
    _notificar(
        session,
        tenant_id,
        auth.cuenta_id,
        destinatarios,
        f"MISD: expediente {expediente.id} retirado del sistema operativo.",
    )
    session.commit()
    return {"id": str(solicitud.id), "estado": solicitud.estado}
