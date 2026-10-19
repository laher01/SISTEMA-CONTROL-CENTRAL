"""Two-tenant HTTP contract checks using disposable fixture database."""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Documento, Empresa, Expediente, Tenant
from app.services.contabilidad_items_ubl import registrar_items_ubl
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
    own_invoice.deleted_at = datetime.now(UTC)
    session.commit()
    after_retirement = client.get("/api/v1/contabilidad-items/conciliacion")
    assert after_retirement.status_code == 200, after_retirement.text
    assert after_retirement.json() == []


def test_items_ubl_http_scoped_filters_and_retirement(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    auth_prueba.como_admin()
    own_tenant = auth_prueba.contexto.tenant_id
    other_tenant = Tenant(nombre="gate-s-ubl-other")
    session.add(other_tenant)
    session.flush()
    xml = (
        b'<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" '
        b'xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" '
        b'xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">'
        b'<cac:InvoiceLine><cbc:InvoicedQuantity unitCode="KGM">12</cbc:InvoicedQuantity>'
        b"<cbc:LineExtensionAmount>60</cbc:LineExtensionAmount>"
        b"<cac:Item><cbc:Name>Pota congelada</cbc:Name></cac:Item>"
        b"</cac:InvoiceLine></Invoice>"
    )
    ids = {}
    for tenant_id, tag in ((own_tenant, "1"), (other_tenant.id, "2")):
        emisor = Empresa(tenant_id=tenant_id, ruc=f"2200000000{tag}", razon_social="Emisor")
        receptor = Empresa(tenant_id=tenant_id, ruc=f"2300000000{tag}", razon_social="Receptor")
        session.add_all([emisor, receptor])
        session.flush()
        expediente = Expediente(
            tenant_id=tenant_id,
            emisor_id=emisor.id,
            receptor_id=receptor.id,
            tipo_comprobante="FACT",
            serie="F002",
            correlativo=tag,
            fecha_emision=date(2026, 10, 18),
            moneda="PEN",
            importe_total=Decimal("60"),
        )
        session.add(expediente)
        session.flush()
        documento = Documento(
            tenant_id=tenant_id,
            expediente_id=expediente.id,
            estado="PENDIENTE_RELACION",
            sha256=tag * 64,
            nombre_original="prueba.xml",
            mime_type="text/xml",
            tamano_bytes=len(xml),
            ruta_storage=f"{tenant_id}/prueba-{tag}.xml",
        )
        session.add(documento)
        session.flush()
        assert registrar_items_ubl(session, tenant_id, documento.id, xml) == 1
        assert registrar_items_ubl(session, tenant_id, documento.id, xml) == 0
        ids[tag] = (emisor.id, receptor.id, documento.id)
    session.commit()

    own = client.get("/api/v1/contabilidad-items")
    assert own.status_code == 200, own.text
    assert len(own.json()) == 1
    assert Decimal(own.json()[0]["cantidad"]) == Decimal("12")
    assert Decimal(own.json()[0]["importe"]) == Decimal("60")
    for key in ("emisor_id", "receptor_id"):
        idx = 0 if key == "emisor_id" else 1
        own_filtered = client.get("/api/v1/contabilidad-items", params={key: str(ids["1"][idx])})
        assert own_filtered.status_code == 200, own_filtered.text
        assert len(own_filtered.json()) == 1
        foreign_filtered = client.get(
            "/api/v1/contabilidad-items", params={key: str(ids["2"][idx])}
        )
        assert foreign_filtered.status_code == 200, foreign_filtered.text
        assert foreign_filtered.json() == []

    own_doc = session.get(Documento, ids["1"][2])
    assert own_doc is not None
    own_doc.deleted_at = datetime.now(UTC)
    session.commit()
    retired = client.get("/api/v1/contabilidad-items")
    assert retired.status_code == 200, retired.text
    assert retired.json() == []
