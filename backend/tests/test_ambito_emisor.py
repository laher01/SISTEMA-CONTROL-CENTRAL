"""Pruebas de aislamiento y atribución provisional del emisor."""
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    AsignacionPedidoGerencia, Empresa, Gestor, Miembro, PedidoGerencia, Tenant,
)
from app.services.ambito_emisor import EstadoAmbitoEmisor, revisar_asignaciones_emisor


def test_emisor_sin_asignacion_no_se_autoriza_automaticamente(session: Session, auth_prueba):
    tenant_id = auth_prueba.contexto.tenant_id
    empresa = Empresa(
        tenant_id=tenant_id, ruc="20111111111",
        razon_social="Emisor de prueba", tipo_relacion="PROVEEDOR",
    )
    session.add(empresa)
    session.commit()

    resultado = revisar_asignaciones_emisor(
        session, tenant_id, empresa.ruc, None, None,
    )
    assert resultado.estado == EstadoAmbitoEmisor.SIN_ASIGNACION


def test_emisor_asignado_a_otro_gestor_se_identifica_sin_mutaciones(
    session: Session, auth_prueba,
):
    tenant_id = auth_prueba.contexto.tenant_id
    empresa = Empresa(
        tenant_id=tenant_id, ruc="20222222222",
        razon_social="Proveedor protegido", tipo_relacion="PROVEEDOR",
    )
    responsable = Miembro(
        tenant_id=tenant_id, codigo="RESP-EMISOR-TEST",
        nombre="Responsable protegido", rol="RESPONSABLE", activo=True,
    )
    usuario = Miembro(
        tenant_id=tenant_id, codigo="USR-EMISOR-TEST",
        nombre="Usuario protegido", rol="USUARIO", activo=True,
    )
    session.add_all([empresa, responsable, usuario])
    session.flush()
    gestor = Gestor(
        tenant_id=tenant_id, codigo="GEST-EMISOR-TEST",
        nombre="Gestor protegido", usuario_id=usuario.id,
    )
    pedido = PedidoGerencia(
        tenant_id=tenant_id, cliente_id=empresa.id,
        responsable_id=responsable.id, periodo_mes=date(2026, 10, 1),
        moneda="PEN", monto_solicitado=Decimal("100"),
        estado="ACTIVO",
    )
    session.add_all([gestor, pedido])
    session.flush()
    session.add(AsignacionPedidoGerencia(
        tenant_id=tenant_id, pedido_id=pedido.id,
        usuario_id=usuario.id, gestor_id=gestor.id,
        proveedor_id=empresa.id, monto_asignado=Decimal("100"),
    ))
    session.commit()

    ajeno = revisar_asignaciones_emisor(
        session, tenant_id, empresa.ruc, None, None,
    )
    assert ajeno.estado == EstadoAmbitoEmisor.ASIGNADO_A_OTRO_GRUPO
    assert ajeno.gestor_propietario_id == gestor.id
    assert ajeno.responsable_propietario_id == responsable.id

    propio = revisar_asignaciones_emisor(
        session, tenant_id, empresa.ruc, usuario.id, gestor.id,
    )
    assert propio.estado == EstadoAmbitoEmisor.ASIGNADO_AL_GRUPO

    externo = Tenant(nombre="TENANT EXTERNO EMISOR", codigo="EXTERNO-EMISOR")
    session.add(externo)
    session.commit()
    aislado = revisar_asignaciones_emisor(
        session, externo.id, empresa.ruc, usuario.id, gestor.id,
    )
    assert aislado.estado == EstadoAmbitoEmisor.SIN_ASIGNACION
