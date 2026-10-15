"""Decisiones internas de ítems, independientes del estado legal SUNAT."""

import uuid
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.item_models import AuditoriaFacturaItem
from app.models import Alerta, Auditoria, Expediente
from app.security import ContextoAcceso
from app.services.ambito_gerencia import alcance_expedientes_gerente

ROL_REVISION = frozenset({"ADMINISTRADOR", "GERENTE"})
ROL_PROPUESTA = ROL_REVISION | frozenset({"SECRETARIA"})
AccionItems = Literal["OBSERVAR", "DESACTIVAR", "REACTIVAR"]


def _expediente_autorizado(
    session: Session, auth: ContextoAcceso, expediente_id: uuid.UUID
) -> Expediente:
    if auth.rol not in ROL_PROPUESTA:
        raise HTTPException(403, "Rol sin permiso de auditoría de ítems")
    consulta = select(Expediente).where(
        Expediente.id == expediente_id,
        Expediente.tenant_id == auth.tenant_id,
        Expediente.deleted_at.is_(None),
    )
    if auth.rol == "GERENTE":
        consulta = consulta.where(alcance_expedientes_gerente(auth))
    expediente = session.scalar(consulta.with_for_update())
    if expediente is None:
        raise HTTPException(404, "Expediente no encontrado o fuera de alcance")
    return expediente


def ultima_decision(
    session: Session, tenant_id: uuid.UUID, expediente_id: uuid.UUID
) -> AuditoriaFacturaItem | None:
    return session.scalar(
        select(AuditoriaFacturaItem)
        .where(
            AuditoriaFacturaItem.tenant_id == tenant_id,
            AuditoriaFacturaItem.expediente_id == expediente_id,
        )
        .order_by(AuditoriaFacturaItem.created_at.desc(), AuditoriaFacturaItem.id.desc())
        .limit(1)
    )


def registrar_decision(
    session: Session,
    auth: ContextoAcceso,
    expediente_id: uuid.UUID,
    accion: AccionItems,
    motivo: str,
) -> AuditoriaFacturaItem:
    _expediente_autorizado(session, auth, expediente_id)
    anterior = ultima_decision(session, auth.tenant_id, expediente_id)
    estado_anterior = anterior.estado if anterior is not None else "VIGENTE"
    if accion == "OBSERVAR":
        if estado_anterior != "VIGENTE" and estado_anterior != "OBSERVADA":
            raise HTTPException(409, "No se puede observar una desactivación activa")
        estado = "OBSERVADA"
    elif accion == "DESACTIVAR":
        if estado_anterior in {"INVALIDADA_PENDIENTE", "INVALIDADA_CONFIRMADA"}:
            raise HTTPException(409, "El comprobante ya está desactivado o en revisión")
        estado = "INVALIDADA_PENDIENTE" if auth.rol == "SECRETARIA" else "INVALIDADA_CONFIRMADA"
    else:
        if estado_anterior not in {"INVALIDADA_CONFIRMADA", "INVALIDADA_PENDIENTE"}:
            raise HTTPException(409, "El comprobante no está desactivado")
        estado = "REACTIVACION_PENDIENTE" if auth.rol == "SECRETARIA" else "VIGENTE"

    decision = AuditoriaFacturaItem(
        tenant_id=auth.tenant_id,
        expediente_id=expediente_id,
        estado=estado,
        motivo=motivo.strip()[:1000],
        solicitado_por_cuenta_id=auth.cuenta_id,
        aprobado_por_cuenta_id=auth.cuenta_id if auth.rol in ROL_REVISION else None,
    )
    session.add(decision)
    session.flush()
    if auth.rol == "SECRETARIA":
        _actualizar_alerta(session, auth.tenant_id, expediente_id, estado)
    session.add(
        Auditoria(
            tenant_id=auth.tenant_id,
            accion=f"ITEMS_{accion}",
            entidad="expediente",
            entidad_id=expediente_id,
            datos={"decision_id": str(decision.id), "estado": estado, "motivo": motivo[:1000]},
        )
    )
    return decision


def _actualizar_alerta(
    session: Session,
    tenant_id: uuid.UUID,
    expediente_id: uuid.UUID,
    estado: str,
    resuelta: bool = False,
) -> None:
    alerta = session.scalar(
        select(Alerta).where(
            Alerta.tenant_id == tenant_id,
            Alerta.expediente_id == expediente_id,
            Alerta.tipo == "ITEMS_REVISION",
        )
    )
    if alerta is None:
        alerta = Alerta(
            tenant_id=tenant_id,
            expediente_id=expediente_id,
            tipo="ITEMS_REVISION",
            mensaje="Auditoría de ítems pendiente de revisión administrativa",
            resuelta=False,
        )
        session.add(alerta)
    alerta.mensaje = f"Contabilidad de Ítems: {estado.replace('_', ' ').lower()}"[:500]
    alerta.resuelta = resuelta


def resolver_propuesta(
    session: Session,
    auth: ContextoAcceso,
    decision_id: uuid.UUID,
    aprobar: bool,
) -> AuditoriaFacturaItem:
    if auth.rol not in ROL_PROPUESTA:
        raise HTTPException(403, "Rol sin permiso para resolver propuestas")
    propuesta = session.scalar(
        select(AuditoriaFacturaItem).where(
            AuditoriaFacturaItem.id == decision_id,
            AuditoriaFacturaItem.tenant_id == auth.tenant_id,
        )
    )
    if propuesta is None:
        raise HTTPException(404, "Propuesta no encontrada")
    _expediente_autorizado(session, auth, propuesta.expediente_id)
    vigente = ultima_decision(session, auth.tenant_id, propuesta.expediente_id)
    if vigente is None or vigente.id != propuesta.id:
        raise HTTPException(409, "La propuesta ya fue reemplazada")
    if propuesta.estado not in {"OBSERVADA", "INVALIDADA_PENDIENTE", "REACTIVACION_PENDIENTE"}:
        raise HTTPException(409, "No es una propuesta pendiente")
    if propuesta.solicitado_por_cuenta_id == auth.cuenta_id:
        raise HTTPException(403, "No se permite aprobar la propia decisión")
    if propuesta.estado == "OBSERVADA":
        estado = "VIGENTE" if aprobar else "INVALIDADA_CONFIRMADA"
    elif propuesta.estado == "INVALIDADA_PENDIENTE":
        estado = "INVALIDADA_CONFIRMADA" if aprobar else "VIGENTE"
    else:
        estado = "VIGENTE" if aprobar else "INVALIDADA_CONFIRMADA"

    decision = AuditoriaFacturaItem(
        tenant_id=auth.tenant_id,
        expediente_id=propuesta.expediente_id,
        estado=estado,
        motivo=propuesta.motivo,
        solicitado_por_cuenta_id=propuesta.solicitado_por_cuenta_id,
        aprobado_por_cuenta_id=auth.cuenta_id,
    )
    session.add(decision)
    session.flush()
    _actualizar_alerta(session, auth.tenant_id, propuesta.expediente_id, estado, True)
    session.add(
        Auditoria(
            tenant_id=auth.tenant_id,
            accion="ITEMS_APROBAR" if aprobar else "ITEMS_REVERTIR",
            entidad="expediente",
            entidad_id=propuesta.expediente_id,
            datos={"propuesta_id": str(propuesta.id), "decision_id": str(decision.id)},
        )
    )
    return decision
