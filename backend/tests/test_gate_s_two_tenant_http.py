"""Two-tenant HTTP contract checks using disposable fixture database."""

from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
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
    assert Decimal(own.json()[0]["importe_total"]) == Decimal("120.00")

    other_context = replace(auth_prueba.contexto, tenant_id=other_tenant.id)
    auth_prueba.contexto = other_context
    other = client.get("/api/v1/contabilidad-items/conciliacion")
    assert other.status_code == 200, other.text
    assert len(other.json()) == 1
    assert Decimal(other.json()[0]["importe_total"]) == Decimal("900.00")

    auth_prueba.contexto = replace(other_context, tenant_id=own_tenant)
    own_again = client.get("/api/v1/contabilidad-items/conciliacion")
    assert own_again.status_code == 200, own_again.text
    assert Decimal(own_again.json()[0]["importe_total"]) == Decimal("120.00")

    own_emitter = session.scalar(
        select(Empresa).where(
            Empresa.tenant_id == own_tenant,
            Empresa.ruc == "20000000001",
        )
    )
    own_receiver = session.scalar(
        select(Empresa).where(
            Empresa.tenant_id == own_tenant,
            Empresa.ruc == "21000000001",
        )
    )
    assert own_emitter is not None and own_receiver is not None
    for filters in (
        {"emisor_id": str(own_emitter.id)},
        {"receptor_id": str(own_receiver.id)},
        {"emisor_id": str(own_emitter.id), "receptor_id": str(own_receiver.id)},
    ):
        response = client.get("/api/v1/contabilidad-items/conciliacion", params=filters)
        assert response.status_code == 200, response.text
        assert Decimal(response.json()[0]["importe_total"]) == Decimal("120.00")

    other_emitter = session.scalar(
        select(Empresa).where(
            Empresa.tenant_id == other_tenant.id,
            Empresa.ruc == "20000000002",
        )
    )
    assert other_emitter is not None
    denied = client.get(
        "/api/v1/contabilidad-items/conciliacion",
        params={"emisor_id": str(other_emitter.id)},
    )
    assert denied.status_code == 200, denied.text
    assert denied.json() == []

    own_invoice = session.scalar(
        select(Expediente).where(
            Expediente.tenant_id == own_tenant,
            Expediente.correlativo == "1",
        )
    )
    assert own_invoice is not None
    own_invoice.deleted_at = datetime.now(timezone.utc)
    session.commit()
    after_retirement = client.get("/api/v1/contabilidad-items/conciliacion")
    assert after_retirement.status_code == 200, after_retirement.text
    assert after_retirement.json() == []
