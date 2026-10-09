"""Consolidado de expedientes por receptor y por Responsable."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Empresa, Expediente, Miembro
from tests.conftest import AuthPrueba


def test_consolidado_clientes_y_responsables(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    responsable = Miembro(
        tenant_id=tenant_id, codigo="RESP-CONS", nombre="Responsable", rol="RESPONSABLE"
    )
    usuario = Miembro(tenant_id=tenant_id, codigo="USR-CONS", nombre="Usuario", rol="USUARIO")
    cliente_a = Empresa(
        tenant_id=tenant_id, ruc="20538821374", razon_social="Cliente A", tipo_relacion="CLIENTE"
    )
    cliente_b = Empresa(
        tenant_id=tenant_id, ruc="20524011353", razon_social="Cliente B", tipo_relacion="CLIENTE"
    )
    session.add_all([responsable, usuario, cliente_a, cliente_b])
    session.flush()
    usuario.responsable_id = responsable.id
    for i, (receptor, monto, fecha) in enumerate(
        [
            (cliente_a, "100.00", date(2026, 10, 5)),
            (cliente_a, "150.00", date(2026, 10, 6)),
            (cliente_b, "200.00", date(2026, 10, 7)),
            (cliente_b, "1000.00", date(2026, 9, 20)),
        ]
    ):
        session.add(
            Expediente(
                tenant_id=tenant_id,
                emisor_id=cliente_a.id,
                receptor_id=receptor.id,
                tipo_comprobante="FACT",
                serie="F001",
                correlativo=str(i + 1),
                fecha_emision=fecha,
                moneda="PEN",
                importe_total=Decimal(monto),
                usuario_id=usuario.id,
                gerente_id=auth_prueba.contexto.miembro_id,
            )
        )
    session.commit()
    auth_prueba.como_gerente()
    url = "/api/v1/pagos/consolidado"
    params = {"desde": "2026-10-01", "hasta": "2026-10-31", "moneda": "PEN"}
    clientes = client.get(url, params={**params, "agrupar": "CLIENTE"})
    assert clientes.status_code == 200, clientes.text
    assert Decimal(clientes.json()["total"]) == Decimal("450.00")
    assert len(clientes.json()["filas"]) == 2
    responsables = client.get(url, params={**params, "agrupar": "RESPONSABLE"})
    assert responsables.status_code == 200, responsables.text
    assert Decimal(responsables.json()["total"]) == Decimal("450.00")
    assert len(responsables.json()["filas"]) == 1
    assert responsables.json()["filas"][0]["registros"] == 3
