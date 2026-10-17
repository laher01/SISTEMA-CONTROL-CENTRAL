"""Persistencia transaccional de auditoría XML; no inicia ni ejecuta reprocesamientos."""

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.item_models import EventoReescaneoXML, TrabajoReescaneoXML
from app.services.contabilidad_items_trabajo_auditoria import EstadoTrabajoXML, EventoAuditoriaXML


def guardar_transicion_xml(session: Session, evento: EventoAuditoriaXML) -> EventoReescaneoXML:
    """Bloquea el trabajo y registra transición + checkpoint en la MISMA transacción.

    El llamador debe confirmar o revertir la transacción. Nunca realiza commit aquí.
    """
    trabajo = session.scalar(
        select(TrabajoReescaneoXML)
        .where(
            TrabajoReescaneoXML.id == evento.trabajo_id,
            TrabajoReescaneoXML.tenant_id == evento.tenant_id,
            TrabajoReescaneoXML.solicitado_por_cuenta_id == evento.actor_cuenta_id,
        )
        .with_for_update()
    )
    if trabajo is None:
        raise ValueError("Trabajo XML no encontrado para actor y tenant")
    if trabajo.estado != evento.estado_anterior:
        raise ValueError("Estado del trabajo XML cambió; recargar")
    registro = EventoReescaneoXML(
        tenant_id=evento.tenant_id,
        trabajo_id=evento.trabajo_id,
        actor_cuenta_id=evento.actor_cuenta_id,
        estado_anterior=evento.estado_anterior.value,
        estado_nuevo=evento.estado_nuevo.value,
        documento_id=evento.documento_id,
        cursor_documento_id=evento.cursor_documento_id,
        ocurrido_en=evento.ocurrido_en,
    )
    trabajo.estado = evento.estado_nuevo.value
    if evento.cursor_documento_id is not None:
        trabajo.cursor_documento_id = evento.cursor_documento_id
    session.add(registro)
    session.flush()
    return registro


def obtener_o_crear_trabajo_xml(
    session: Session,
    tenant_id: uuid.UUID,
    actor_cuenta_id: uuid.UUID,
    clave_idempotencia: str,
) -> tuple[TrabajoReescaneoXML, bool]:
    """Registra solicitud idempotente y devuelve existente tras choque concurrente.

    La clave pertenece al tenant, no al usuario: un actor distinto no puede
    recuperar ni suplantar una solicitud previamente registrada.
    """
    if not clave_idempotencia or len(clave_idempotencia) > 100:
        raise ValueError("Clave de idempotencia XML inválida")
    consulta = select(TrabajoReescaneoXML).where(
        TrabajoReescaneoXML.tenant_id == tenant_id,
        TrabajoReescaneoXML.clave_idempotencia == clave_idempotencia,
    )
    existente = session.scalar(consulta)
    if existente is not None:
        if existente.solicitado_por_cuenta_id != actor_cuenta_id:
            raise ValueError("Clave XML reservada por otro actor")
        return existente, False
    nuevo = TrabajoReescaneoXML(
        tenant_id=tenant_id,
        solicitado_por_cuenta_id=actor_cuenta_id,
        clave_idempotencia=clave_idempotencia,
        estado=EstadoTrabajoXML.PENDIENTE.value,
        documentos_procesados=0,
    )
    try:
        with session.begin_nested():
            session.add(nuevo)
            session.flush()
    except IntegrityError:
        existente = session.scalar(consulta)
        if existente is None:
            raise
        if existente.solicitado_por_cuenta_id != actor_cuenta_id:
            raise ValueError("Clave XML reservada por otro actor") from None
        return existente, False
    return nuevo, True


def recuperar_checkpoint_confirmado_xml(
    session: Session,
    tenant_id: uuid.UUID,
    actor_cuenta_id: uuid.UUID,
    trabajo_id: uuid.UUID,
) -> tuple[uuid.UUID | None, EstadoTrabajoXML]:
    """Relee el checkpoint persistido y verifica su último evento; no ejecuta lotes."""
    trabajo = session.scalar(
        select(TrabajoReescaneoXML).where(
            TrabajoReescaneoXML.id == trabajo_id,
            TrabajoReescaneoXML.tenant_id == tenant_id,
            TrabajoReescaneoXML.solicitado_por_cuenta_id == actor_cuenta_id,
        )
    )
    if trabajo is None:
        raise ValueError("Trabajo XML no encontrado para actor y tenant")
    ultimo = session.scalar(
        select(EventoReescaneoXML)
        .where(
            EventoReescaneoXML.trabajo_id == trabajo_id,
            EventoReescaneoXML.tenant_id == tenant_id,
            EventoReescaneoXML.actor_cuenta_id == actor_cuenta_id,
        )
        .order_by(EventoReescaneoXML.created_at.desc(), EventoReescaneoXML.id.desc())
        .limit(1)
    )
    if ultimo is None:
        if trabajo.estado != EstadoTrabajoXML.PENDIENTE.value or trabajo.cursor_documento_id:
            raise ValueError("Checkpoint XML sin auditoría consistente")
    elif ultimo.estado_nuevo != trabajo.estado or (
        ultimo.cursor_documento_id is not None
        and ultimo.cursor_documento_id != trabajo.cursor_documento_id
    ):
        raise ValueError("Checkpoint XML y auditoría no coinciden")
    estado = EstadoTrabajoXML(trabajo.estado)
    if estado == EstadoTrabajoXML.EJECUTANDO:
        raise ValueError("Trabajo XML ejecutándose; requiere pausa supervisada antes del reintento")
    return trabajo.cursor_documento_id, estado
