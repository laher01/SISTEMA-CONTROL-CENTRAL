"""No mezclar producción o pagos entre dos Gerentes del mismo Responsable."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Empresa, Expediente, Miembro, PedidoGerencia
from app.security import ContextoAcceso
from tests.conftest import AuthPrueba


def test_produccion_aislada_por_gerente(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    gerente_a = Miembro(tenant_id=tenant_id, codigo="GER-A", nombre="Gerente A",
                       rol="GERENTE", activo=True)
    gerente_b = Miembro(tenant_id=tenant_id, codigo="GER-B", nombre="Gerente B",
                       rol="GERENTE", activo=True)
    responsable = Miembro(tenant_id=tenant_id, codigo="RESP-A", nombre="Responsable",
                          rol="RESPONSABLE", activo=True)
    usuario = Miembro(tenant_id=tenant_id, codigo="USER-A", nombre="Usuario",
                      rol="USUARIO", activo=True)
    cliente = Empresa(tenant_id=tenant_id, ruc="20990000001",
                      razon_social="CLIENTE COMPARTIDO", tipo_relacion="CLIENTE")
    session.add_all([gerente_a, gerente_b, responsable, usuario, cliente])
    session.flush()
    usuario.responsable_id = responsable.id
    for gerente, numero in ((gerente_a, "000001"), (gerente_b, "000002")):
        pedido = PedidoGerencia(
            tenant_id=tenant_id, gerente_id=gerente.id,
            responsable_id=responsable.id, cliente_id=cliente.id,
            periodo_mes=date(2026, 10, 1), moneda="PEN",
            monto_solicitado=Decimal("1000"), modalidad="POR_PEDIDO",
            modo_distribucion="MANUAL", estado="ACTIVO",
        )
        session.add(pedido)
        session.flush()
        session.add(Expediente(
            tenant_id=tenant_id, receptor_id=cliente.id, emisor_id=cliente.id,
            tipo_comprobante="FACT", serie="F001", correlativo=numero,
            fecha_emision=date(2026, 10, 9), moneda="PEN",
            importe_total=Decimal("100" if gerente == gerente_a else "300"),
            usuario_id=usuario.id, gerente_id=gerente.id, pedido_gerencia_id=pedido.id,
        ))
    session.commit()

    def como(gerente: Miembro) -> None:
        anterior = auth_prueba.contexto
        auth_prueba.contexto = ContextoAcceso(
            cuenta_id=anterior.cuenta_id, tenant_id=tenant_id, rol="GERENTE",
            miembro_id=gerente.id, gestor_id=None, usuario_id=None,
            codigo=gerente.codigo, nombre=gerente.nombre,
            cambio_clave_obligatorio=False,
        )

    para = {"desde": "2026-10-01", "hasta": "2026-10-31", "moneda": "PEN"}
    como(gerente_a)
    a = client.get("/api/v1/pagos-responsables/resumen", params=para)
    assert a.status_code == 200, a.text
    assert a.json()["total_produccion"] == "100.00"
    pedidos_a = client.get("/api/v1/pagos/pedidos")
    assert pedidos_a.status_code == 200, pedidos_a.text
    assert len(pedidos_a.json()) == 1
    assert Decimal(str(pedidos_a.json()[0]["monto_ejecutado"])) == Decimal("100")

    como(gerente_b)
    b = client.get("/api/v1/pagos-responsables/resumen", params=para)
    assert b.status_code == 200, b.text
    assert b.json()["total_produccion"] == "300.00"
    pedidos_b = client.get("/api/v1/pagos/pedidos")
    assert pedidos_b.status_code == 200, pedidos_b.text
    assert len(pedidos_b.json()) == 1
    assert Decimal(str(pedidos_b.json()[0]["monto_ejecutado"])) == Decimal("300")
