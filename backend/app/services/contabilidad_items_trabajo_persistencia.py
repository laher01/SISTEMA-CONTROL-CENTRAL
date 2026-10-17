"""Persistencia transaccional de auditoría XML; no inicia ni ejecuta reprocesamientos."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.item_models import EventoReescaneoXML, TrabajoReescaneoXML
from app.services.contabilidad_items_trabajo_auditoria import EventoAuditoriaXML


def guardar_transicion_xml(
    session: Session, evento: EventoAuditoriaXML
) -> EventoReescaneoXML:
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
