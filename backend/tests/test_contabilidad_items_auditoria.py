"""Pruebas transaccionales del control de auditoría de ítems."""

import uuid
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.contabilidad_items import _alcance
from app.models import CuentaAcceso, Empresa, Expediente, Miembro
from app.services.contabilidad_items_auditoria import (
    registrar_decision,
    resolver_propuesta,
    ultima_decision,
)


def _expediente(session: Session, tenant_id: uuid.UUID) -> Expediente:
    emisor = Empresa(tenant_id=tenant_id, ruc="20111111111", razon_social="Proveedor de prueba")
    receptor = Empresa(tenant_id=tenant_id, ruc="20222222222", razon_social="Cliente de prueba")
    session.add_all([emisor, receptor])
    session.flush()
    expediente = Expediente(
        tenant_id=tenant_id,
        emisor_id=emisor.id,
        receptor_id=receptor.id,
        tipo_comprobante="FACT",
        serie="F001",
        correlativo="1",
        fecha_emision=date(2026, 10, 14),
        moneda="PEN",
        importe_total=Decimal("50.00"),
    )
    session.add(expediente)
    session.flush()
    return expediente


def test_secretaria_requiere_revisor_y_reactivacion_restaurable(session, auth_prueba):
    contexto = auth_prueba.contexto
    expediente = _expediente(session, contexto.tenant_id)
    secretaria = replace(contexto, rol="SECRETARIA")
    propuesta = registrar_decision(
        session, secretaria, expediente.id, "DESACTIVAR", "Producto ajeno al giro"
    )
    assert propuesta.estado == "INVALIDADA_PENDIENTE"

    with pytest.raises(HTTPException) as exc:
        resolver_propuesta(session, secretaria, propuesta.id, True)
    assert exc.value.status_code == 403

    revisor = CuentaAcceso(
        tenant_id=contexto.tenant_id,
        login="REVISOR-ITEMS",
        password_hash="hash-test",
        activo=True,
        cambio_clave_obligatorio=False,
    )
    session.add(revisor)
    session.flush()
    administrador = replace(contexto, cuenta_id=revisor.id, rol="ADMINISTRADOR")
    aprobada = resolver_propuesta(session, administrador, propuesta.id, True)
    assert aprobada.estado == "INVALIDADA_CONFIRMADA"

    reactivada = registrar_decision(
        session, administrador, expediente.id, "REACTIVAR", "Se verificó el comprobante"
    )
    assert reactivada.estado == "VIGENTE"
    assert ultima_decision(session, contexto.tenant_id, expediente.id).id == reactivada.id


def test_rol_usuario_no_puede_desactivar_factura(session, auth_prueba):
    contexto = auth_prueba.contexto
    expediente = _expediente(session, contexto.tenant_id)
    with pytest.raises(HTTPException) as exc:
        registrar_decision(session, contexto, expediente.id, "DESACTIVAR", "No autorizado")
    assert exc.value.status_code == 403


@pytest.mark.parametrize(
    ("aprobar", "esperado"), [(True, "VIGENTE"), (False, "INVALIDADA_CONFIRMADA")]
)
def test_observacion_resuelta_con_aprobacion_o_rechazo(session, auth_prueba, aprobar, esperado):
    contexto = auth_prueba.contexto
    revisor = CuentaAcceso(
        tenant_id=contexto.tenant_id,
        login="REVISOR-OBSERVACIONES",
        password_hash="hash-test",
        activo=True,
        cambio_clave_obligatorio=False,
    )
    session.add(revisor)
    session.flush()
    secretaria = replace(contexto, rol="SECRETARIA")
    administrador = replace(contexto, cuenta_id=revisor.id, rol="ADMINISTRADOR")

    expediente = _expediente(session, contexto.tenant_id)
    observacion = registrar_decision(
        session, secretaria, expediente.id, "OBSERVAR", "Ítem requiere justificación"
    )
    assert observacion.estado == "OBSERVADA"
    with pytest.raises(HTTPException) as error:
        resolver_propuesta(session, secretaria, observacion.id, aprobar)
    assert error.value.status_code == 403

    resuelta = resolver_propuesta(session, administrador, observacion.id, aprobar)
    assert resuelta.estado == esperado
    assert resuelta.aprobado_por_cuenta_id == revisor.id
    assert ultima_decision(session, contexto.tenant_id, expediente.id).id == resuelta.id
    with pytest.raises(HTTPException) as error:
        resolver_propuesta(session, administrador, observacion.id, aprobar)
    assert error.value.status_code == 409


def test_secretaria_distinta_puede_resolver_observacion(session, auth_prueba):
    contexto = auth_prueba.contexto
    expediente = _expediente(session, contexto.tenant_id)
    administrador = replace(contexto, rol="ADMINISTRADOR")
    observacion = registrar_decision(
        session, administrador, expediente.id, "OBSERVAR", "Falta sustento de ítems"
    )
    secretaria_cuenta = CuentaAcceso(
        tenant_id=contexto.tenant_id,
        login="SECRETARIA-REVISION-ITEMS",
        password_hash="hash-test",
        activo=True,
        cambio_clave_obligatorio=False,
    )
    session.add(secretaria_cuenta)
    session.flush()
    secretaria = replace(contexto, rol="SECRETARIA", cuenta_id=secretaria_cuenta.id)
    resultado = resolver_propuesta(session, secretaria, observacion.id, True)
    assert resultado.estado == "VIGENTE"
    assert resultado.aprobado_por_cuenta_id == secretaria_cuenta.id


def test_secretaria_no_puede_resolver_desactivacion_pendiente(session, auth_prueba):
    contexto = auth_prueba.contexto
    expediente = _expediente(session, contexto.tenant_id)
    secretaria = replace(contexto, rol="SECRETARIA")
    propuesta = registrar_decision(
        session, secretaria, expediente.id, "DESACTIVAR", "Requiere revisión"
    )
    segunda_cuenta = CuentaAcceso(
        tenant_id=contexto.tenant_id,
        login="SECRETARIA-OTRA-REVISION",
        password_hash="hash-test",
        activo=True,
        cambio_clave_obligatorio=False,
    )
    session.add(segunda_cuenta)
    session.flush()
    segunda_secretaria = replace(contexto, rol="SECRETARIA", cuenta_id=segunda_cuenta.id)
    with pytest.raises(HTTPException) as error:
        resolver_propuesta(session, segunda_secretaria, propuesta.id, True)
    assert error.value.status_code == 403


def test_responsable_consulta_solo_expedientes_de_su_equipo(session, auth_prueba):
    contexto = auth_prueba.contexto
    responsable = Miembro(
        tenant_id=contexto.tenant_id,
        codigo="RESP-ITEMS-TEST",
        nombre="Responsable auditoría",
        rol="RESPONSABLE",
    )
    otro_responsable = Miembro(
        tenant_id=contexto.tenant_id,
        codigo="RESP-ITEMS-OTRO",
        nombre="Otro responsable",
        rol="RESPONSABLE",
    )
    session.add_all([responsable, otro_responsable])
    session.flush()
    usuario_propio = Miembro(
        tenant_id=contexto.tenant_id,
        codigo="USU-ITEMS-PROPIO",
        nombre="Usuario del equipo",
        rol="USUARIO",
        responsable_id=responsable.id,
    )
    usuario_ajeno = Miembro(
        tenant_id=contexto.tenant_id,
        codigo="USU-ITEMS-AJENO",
        nombre="Usuario de otro equipo",
        rol="USUARIO",
        responsable_id=otro_responsable.id,
    )
    session.add_all([usuario_propio, usuario_ajeno])
    session.flush()
    expediente = _expediente(session, contexto.tenant_id)
    expediente.usuario_id = usuario_propio.id
    otro_expediente = Expediente(
        tenant_id=contexto.tenant_id,
        emisor_id=expediente.emisor_id,
        receptor_id=expediente.receptor_id,
        tipo_comprobante="FACT",
        serie="F001",
        correlativo="2",
        fecha_emision=date(2026, 10, 14),
        moneda="PEN",
        importe_total=Decimal("75.00"),
        usuario_id=usuario_ajeno.id,
    )
    session.add(otro_expediente)
    session.flush()
    auth = replace(contexto, rol="RESPONSABLE", miembro_id=responsable.id)
    expedientes = session.scalars(
        select(Expediente).where(
            Expediente.tenant_id == contexto.tenant_id,
            _alcance(auth),
        )
    ).all()
    assert expediente.id in {e.id for e in expedientes}
    assert otro_expediente.id not in {e.id for e in expedientes}
