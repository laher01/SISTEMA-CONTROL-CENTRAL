from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    AsignacionPedidoGerencia,
    Empresa,
    Expediente,
    Miembro,
    PedidoGerencia,
)
from app.security import ContextoAcceso
from tests.conftest import AuthPrueba


def test_responsable_solo_consulta_su_equipo(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    tid = auth_prueba.contexto.tenant_id
    responsable = Miembro(
        tenant_id=tid, codigo="RESP1", nombre="Resp", rol="RESPONSABLE", activo=True
    )
    propio = Miembro(tenant_id=tid, codigo="US1", nombre="Propio", rol="USUARIO", activo=True)
    ajeno = Miembro(tenant_id=tid, codigo="US2", nombre="Ajeno", rol="USUARIO", activo=True)
    session.add_all([responsable, propio, ajeno])
    session.flush()
    propio.responsable_id = responsable.id
    cliente = Empresa(tenant_id=tid, ruc="20123456789", razon_social="Cliente A")
    proveedor = Empresa(tenant_id=tid, ruc="20987654321", razon_social="Proveedor")
    session.add_all([cliente, proveedor])
    session.flush()
    for i, usuario in enumerate([propio, ajeno], start=1):
        session.add(
            Expediente(
                tenant_id=tid,
                receptor_id=cliente.id,
                emisor_id=proveedor.id,
                tipo_comprobante="01",
                serie="F001",
                correlativo=f"{i:08d}",
                fecha_emision=date(2026, 10, 1),
                moneda="PEN",
                importe_total=Decimal("100.00"),
                usuario_id=usuario.id,
            )
        )
    pedido = PedidoGerencia(
        tenant_id=tid,
        cliente_id=cliente.id,
        responsable_id=responsable.id,
        periodo_mes=date(2026, 10, 1),
        moneda="PEN",
        monto_solicitado=Decimal("200.00"),
        modalidad="POR_PEDIDO",
        modo_distribucion="MANUAL",
        estado="ACTIVO",
    )
    session.add(pedido)
    session.flush()
    session.add_all(
        [
            AsignacionPedidoGerencia(
                tenant_id=tid,
                pedido_id=pedido.id,
                usuario_id=propio.id,
                monto_asignado=Decimal("90.00"),
            ),
            AsignacionPedidoGerencia(
                tenant_id=tid,
                pedido_id=pedido.id,
                usuario_id=ajeno.id,
                monto_asignado=Decimal("110.00"),
            ),
        ]
    )
    session.commit()

    assert client.get("/api/v1/responsable/resumen").status_code == 403
    auth_prueba.contexto = ContextoAcceso(
        cuenta_id=auth_prueba.contexto.cuenta_id,
        tenant_id=tid,
        rol="RESPONSABLE",
        miembro_id=responsable.id,
        gestor_id=None,
        usuario_id=None,
        codigo=responsable.codigo,
        nombre=responsable.nombre,
        cambio_clave_obligatorio=False,
    )
    respuesta = client.get("/api/v1/responsable/resumen")
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert [u["codigo"] for u in datos["usuarios"]] == ["US1"]
    assert len(datos["clientes"]) == 1
    assert datos["clientes"][0]["produccion"] == "100.00"
    assert len(datos["pedidos"]) == 1
    assert datos["pedidos"][0]["monto_asignado"] == "90.00"
    assert datos["pagos"] == []
