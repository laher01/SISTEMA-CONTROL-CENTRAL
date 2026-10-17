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
from app.services.contabilidad_items_trabajo_persistencia import (
    guardar_transicion_xml,
    obtener_o_crear_trabajo_xml,
    reanudar_trabajo_xml_supervisado,
    recuperar_checkpoint_confirmado_xml,
)


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


def test_solicitud_xml_idempotente_y_aislada_por_actor(session: Session):
    tenant = Tenant(nombre="tenant_solicitud_xml")
    session.add(tenant)
    session.flush()
    actores = [
        CuentaAcceso(
            tenant_id=tenant.id,
            login=f"actor-xml-{i}",
            password_hash="test",
            activo=True,
            cambio_clave_obligatorio=False,
        )
        for i in range(2)
    ]
    session.add_all(actores)
    session.flush()
    creado, es_nuevo = obtener_o_crear_trabajo_xml(session, tenant.id, actores[0].id, "carga-1")
    repetido, otra_vez = obtener_o_crear_trabajo_xml(session, tenant.id, actores[0].id, "carga-1")
    assert es_nuevo is True
    assert otra_vez is False
    assert creado.id == repetido.id
    with pytest.raises(ValueError, match="otro actor"):
        obtener_o_crear_trabajo_xml(session, tenant.id, actores[1].id, "carga-1")
    assert session.scalar(select(func.count()).select_from(TrabajoReescaneoXML)) == 1


def test_checkpoint_se_revierte_con_evento_tras_rollback(engine):
    from sqlalchemy.orm import sessionmaker

    fabrica = sessionmaker(engine, expire_on_commit=False)
    with fabrica() as session:
        tenant = Tenant(nombre="tenant_rollback_xml")
        session.add(tenant)
        session.flush()
        actor = CuentaAcceso(
            tenant_id=tenant.id,
            login="actor-rollback-xml",
            password_hash="test",
            activo=True,
            cambio_clave_obligatorio=False,
        )
        session.add(actor)
        session.flush()
        trabajo, _ = obtener_o_crear_trabajo_xml(session, tenant.id, actor.id, "rollback-1")
        tenant_id, actor_id, trabajo_id = tenant.id, actor.id, trabajo.id
        session.commit()
    with fabrica() as session:
        guardar_transicion_xml(
            session,
            EventoAuditoriaXML(
                trabajo_id=trabajo_id,
                tenant_id=tenant_id,
                actor_cuenta_id=actor_id,
                estado_anterior=EstadoTrabajoXML.PENDIENTE,
                estado_nuevo=EstadoTrabajoXML.EJECUTANDO,
                ocurrido_en=datetime.now(UTC),
            ),
        )
        session.rollback()
    with fabrica() as session:
        estado = session.scalar(
            select(TrabajoReescaneoXML.estado).where(TrabajoReescaneoXML.id == trabajo_id)
        )
        assert estado == "PENDIENTE"
        assert session.scalar(select(func.count()).select_from(EventoReescaneoXML)) == 0


def test_recuperacion_checkpoint_desde_otra_sesion(engine):
    from sqlalchemy.orm import sessionmaker

    fabrica = sessionmaker(engine, expire_on_commit=False)
    with fabrica() as sesion:
        tenant = Tenant(nombre="tenant_reinicio_checkpoint_xml")
        sesion.add(tenant)
        sesion.flush()
        cuenta = CuentaAcceso(
            tenant_id=tenant.id,
            login="actor-recuperacion-xml",
            password_hash="test",
            activo=True,
            cambio_clave_obligatorio=False,
        )
        sesion.add(cuenta)
        sesion.flush()
        trabajo, _ = obtener_o_crear_trabajo_xml(sesion, tenant.id, cuenta.id, "reinicio-1")
        ids = (tenant.id, cuenta.id, trabajo.id)
        guardar_transicion_xml(
            sesion,
            EventoAuditoriaXML(
                trabajo_id=trabajo.id,
                tenant_id=tenant.id,
                actor_cuenta_id=cuenta.id,
                estado_anterior=EstadoTrabajoXML.PENDIENTE,
                estado_nuevo=EstadoTrabajoXML.EJECUTANDO,
                ocurrido_en=datetime.now(UTC),
            ),
        )
        guardar_transicion_xml(
            sesion,
            EventoAuditoriaXML(
                trabajo_id=trabajo.id,
                tenant_id=tenant.id,
                actor_cuenta_id=cuenta.id,
                estado_anterior=EstadoTrabajoXML.EJECUTANDO,
                estado_nuevo=EstadoTrabajoXML.PAUSADO,
                ocurrido_en=datetime.now(UTC),
            ),
        )
        sesion.commit()

    with fabrica() as sesion:
        assert recuperar_checkpoint_confirmado_xml(sesion, *ids) == (
            None,
            EstadoTrabajoXML.PAUSADO,
        )
        with pytest.raises(ValueError, match="actor y tenant"):
            recuperar_checkpoint_confirmado_xml(sesion, uuid.uuid4(), ids[1], ids[2])
        trabajo = sesion.get(TrabajoReescaneoXML, ids[2])
        assert trabajo is not None
        trabajo.estado = "COMPLETADO"
        sesion.flush()
        with pytest.raises(ValueError, match="no coinciden"):
            recuperar_checkpoint_confirmado_xml(sesion, *ids)
        sesion.rollback()


def test_reanudar_xml_pausado_con_limite_y_auditoria(engine):
    from sqlalchemy.orm import sessionmaker

    fabrica = sessionmaker(engine, expire_on_commit=False)
    with fabrica() as sesion:
        tenant = Tenant(nombre="tenant_reanudar_supervisado")
        sesion.add(tenant)
        sesion.flush()
        actor = CuentaAcceso(
            tenant_id=tenant.id,
            login="actor-reanudar-xml",
            password_hash="test",
            activo=True,
            cambio_clave_obligatorio=False,
        )
        sesion.add(actor)
        sesion.flush()
        trabajo, _ = obtener_o_crear_trabajo_xml(sesion, tenant.id, actor.id, "reanudar-1")
        ids = tenant.id, actor.id, trabajo.id
        for anterior, nuevo in (
            (EstadoTrabajoXML.PENDIENTE, EstadoTrabajoXML.EJECUTANDO),
            (EstadoTrabajoXML.EJECUTANDO, EstadoTrabajoXML.PAUSADO),
        ):
            guardar_transicion_xml(
                sesion,
                EventoAuditoriaXML(
                    trabajo_id=trabajo.id,
                    tenant_id=tenant.id,
                    actor_cuenta_id=actor.id,
                    estado_anterior=anterior,
                    estado_nuevo=nuevo,
                    ocurrido_en=datetime.now(UTC),
                ),
            )
        sesion.commit()

    with fabrica() as sesion:
        with pytest.raises(ValueError, match="Límite"):
            reanudar_trabajo_xml_supervisado(
                sesion, *ids, max_documentos=101, ocurrido_en=datetime.now(UTC)
            )
        cursor, evento = reanudar_trabajo_xml_supervisado(
            sesion, *ids, max_documentos=50, ocurrido_en=datetime.now(UTC)
        )
        assert cursor is None
        assert evento.estado_nuevo == "EJECUTANDO"
        with pytest.raises(ValueError, match="requiere pausa supervisada"):
            reanudar_trabajo_xml_supervisado(
                sesion, *ids, max_documentos=50, ocurrido_en=datetime.now(UTC)
            )
        sesion.rollback()
    with fabrica() as sesion:
        assert recuperar_checkpoint_confirmado_xml(sesion, *ids) == (
            None,
            EstadoTrabajoXML.PAUSADO,
        )
        assert sesion.scalar(select(func.count()).select_from(EventoReescaneoXML)) == 2
