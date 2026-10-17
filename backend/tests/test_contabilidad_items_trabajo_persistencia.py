"""Persistencia de checkpoints XML aislada por tenant y actor."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.item_models import EventoReescaneoXML, TrabajoReescaneoXML
from app.models import CuentaAcceso, Tenant
from app.services.contabilidad_items_trabajo_auditoria import (
    EstadoTrabajoXML,
    EventoAuditoriaXML,
)
from app.services.contabilidad_items_trabajo_persistencia import guardar_transicion_xml


def test_checkpoint_xml_atómico_por_tenant_y_actor(session: Session):
    tenant = Tenant(nombre="trabajo_checkpoint_xml")
    session.add(tenant)
    session.flush()
    actor = CuentaAcceso(
        tenant_id=tenant.id,
        login="AUDITOR-XML",
        password_hash="test",
        activo=True,
        cambio_clave_obligatorio=False,
    )
    session.add(actor)
    session.flush()
    trabajo = TrabajoReescaneoXML(
        tenant_id=tenant.id,
        solicitado_por_cuenta_id=actor.id,
        clave_idempotencia="lote-1",
        estado="PENDIENTE",
    )
    session.add(trabajo)
    session.flush()
    evento = EventoAuditoriaXML(
        trabajo_id=trabajo.id,
        tenant_id=tenant.id,
        actor_cuenta_id=actor.id,
        estado_anterior=EstadoTrabajoXML.PENDIENTE,
        estado_nuevo=EstadoTrabajoXML.EJECUTANDO,
        ocurrido_en=datetime.now(UTC),
    )
    guardar_transicion_xml(session, evento)
    assert trabajo.estado == "EJECUTANDO"
    assert session.scalar(select(func.count()).select_from(EventoReescaneoXML)) == 1
    with pytest.raises(ValueError, match="cambió"):
        guardar_transicion_xml(session, evento)
    with pytest.raises(ValueError, match="actor y tenant"):
        guardar_transicion_xml(
            session,
            EventoAuditoriaXML(
                trabajo_id=trabajo.id,
                tenant_id=uuid.uuid4(),
                actor_cuenta_id=actor.id,
                estado_anterior=EstadoTrabajoXML.PENDIENTE,
                estado_nuevo=EstadoTrabajoXML.EJECUTANDO,
                ocurrido_en=datetime.now(UTC),
            ),
        )
    assert session.scalar(select(func.count()).select_from(EventoReescaneoXML)) == 1
