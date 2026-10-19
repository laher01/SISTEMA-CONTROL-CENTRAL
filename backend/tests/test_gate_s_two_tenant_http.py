"""Two-tenant HTTP contract checks using disposable fixture database."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Empresa, Expediente, Tenant
from tests.conftest import AuthPrueba


def test_conciliacion_excludes_other_tenant_and_emisor_receptor(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    auth_prueba.como_admin()
    own_tenant = auth_prueba.contexto.tenant_id
    other_tenant = Tenant(nombre="gate-s-otro-tenant")
    session.add(other_tenant)
    session.flush()
    for tenant_id, suffix, amount in (
        (own_tenant, "1", Decimal("120.00")),
        (other_tenant.id, "2", Decimal("900.00")),
    ):
        emitter = Empresa(
            tenant_id=tenant_id, ruc=f"2000000000{suffix}", razon_social=f"Emisor {suffix}"
        )
        receiver = Empresa(
            tenant_id=tenant_id, ruc=f"2100000000{suffix}", razon_social=f"Cliente {suffix}"
        )
        session.add_all([emitter, receiver])
        session.flush()
        session.add(
            Expediente(
                tenant_id=tenant_id,
                emisor_id=emitter.id,
                receptor_id=receiver.id,
                tipo_comprobante="FACT",
                serie="F001",
                correlativo=suffix,
                fecha_emision=date(2026, 10, 18),
                moneda="PEN",
                importe_total=amount,
            )
        )
    session.commit()

    own = client.get("/api/v1/contabilidad-items/conciliacion")
    assert own.status_code == 200, own.text
    assert len(own.json()) == 1
    assert Decimal(own.json()[0]["total"]) == Decimal("120.00")

    other_context = replace(auth_prueba.contexto, tenant_id=other_tenant.id)
    auth_prueba.contexto = other_context
    other = client.get("/api/v1/contabilidad-items/conciliacion")
    assert other.status_code == 200, other.text
    assert len(other.json()) == 1
    assert Decimal(other.json()[0]["total"]) == Decimal("900.00")

    auth_prueba.contexto = replace(other_context, tenant_id=own_tenant)
    own_again = client.get("/api/v1/contabilidad-items/conciliacion")
    assert own_again.status_code == 200, own_again.text
    assert Decimal(own_again.json()[0]["total"]) == Decimal("120.00")
