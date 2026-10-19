"""Items: authenticated invoice drilldown, search, tenant isolation (synthetic DB)."""

from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Documento, Empresa, Expediente, Tenant
from app.services.contabilidad_items_ubl import registrar_items_ubl
from tests.conftest import AuthPrueba

XML = (
    b'<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" '
    b'xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" '
    b'xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">'
    b'<cac:InvoiceLine><cbc:InvoicedQuantity unitCode="KGM">12</cbc:InvoicedQuantity>'
    b"<cbc:LineExtensionAmount>60</cbc:LineExtensionAmount>"
    b"<cac:Item><cbc:Name>Pota congelada</cbc:Name></cac:Item>"
    b"</cac:InvoiceLine></Invoice>"
)


def test_search_and_linked_invoices_are_tenant_scoped(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    auth_prueba.como_admin()
    tenant_a = auth_prueba.contexto.tenant_id
    tenant_b = Tenant(nombre="tenant_items_links_b")
    session.add(tenant_b)
    session.flush()
    for tenant, suffix in ((tenant_a, "1"), (tenant_b.id, "2")):
        emisor = Empresa(tenant_id=tenant, ruc=f"2010000000{suffix}", razon_social="Emisor")
        receptor = Empresa(tenant_id=tenant, ruc=f"2020000000{suffix}", razon_social="Receptor")
        session.add_all([emisor, receptor])
        session.flush()
        expediente = Expediente(
            tenant_id=tenant,
            emisor_id=emisor.id,
            receptor_id=receptor.id,
            tipo_comprobante="FACT",
            serie="F001",
            correlativo=suffix,
            fecha_emision=date(2026, 10, 19),
            moneda="PEN",
            importe_total=Decimal("60"),
        )
        session.add(expediente)
        session.flush()
        documento = Documento(
            tenant_id=tenant,
            expediente_id=expediente.id,
            estado="PENDIENTE_RELACION",
            sha256=suffix * 64,
            nombre_original="factura.xml",
            mime_type="text/xml",
            tamano_bytes=len(XML),
            ruta_storage=f"test/{suffix}.xml",
        )
        session.add(documento)
        session.flush()
        assert registrar_items_ubl(session, tenant, documento.id, XML) == 1
    session.commit()

    summary = client.get("/api/v1/contabilidad-items", params={"buscar": "pota"})
    assert summary.status_code == 200, summary.text
    assert len(summary.json()) == 1
    product_id = summary.json()[0]["producto_id"]
    assert Decimal(summary.json()[0]["cantidad"]) == 12

    missing = client.get("/api/v1/contabilidad-items", params={"buscar": "anchoveta"})
    assert missing.status_code == 200
    assert missing.json() == []

    category = summary.json()[0]["categoria"]
    by_category = client.get(
        "/api/v1/contabilidad-items",
        params={"buscar": "congelada", "categoria": category},
    )
    assert by_category.status_code == 200, by_category.text
    assert len(by_category.json()) == 1
    export = client.get(
        "/api/v1/contabilidad-items/exportar-csv",
        params={"buscar": "pota", "categoria": category},
    )
    assert export.status_code == 200, export.text
    assert "Pota congelada" in export.text
    empty_export = client.get(
        "/api/v1/contabilidad-items/exportar-csv",
        params={"buscar": "anchoveta"},
    )
    assert empty_export.status_code == 200, empty_export.text
    assert "Pota congelada" not in empty_export.text

    invoices = client.get(f"/api/v1/contabilidad-items/productos/{product_id}/facturas")
    assert invoices.status_code == 200, invoices.text
    assert len(invoices.json()) == 1
    assert invoices.json()[0]["comprobante"] == "F001-1"
    assert invoices.json()[0]["descripcion_original"] == "Pota congelada"
    assert Decimal(invoices.json()[0]["importe"]) == 60

    # Only the authorized tenant and operational roles may consult a product.
    foreign = client.get(
        f"/api/v1/contabilidad-items/productos/{product_id}/facturas",
        params={"emisor_id": str(tenant_b.id)},
    )
    assert foreign.status_code == 200, foreign.text
    assert foreign.json() == []
    invalid_range = client.get(
        f"/api/v1/contabilidad-items/productos/{product_id}/facturas",
        params={"desde": "2026-10-20", "hasta": "2026-10-19"},
    )
    assert invalid_range.status_code == 422

    auth_prueba.como_superadmin()
    denied = client.get(f"/api/v1/contabilidad-items/productos/{product_id}/facturas")
    assert denied.status_code == 403
    auth_prueba.como_admin()

    own_doc = session.get(Documento, invoices.json()[0]["documento_id"])
    assert own_doc is not None
    own_doc.deleted_at = datetime.now(UTC)
    session.commit()
    inactive = client.get(f"/api/v1/contabilidad-items/productos/{product_id}/facturas")
    assert inactive.status_code == 200
    assert inactive.json() == []
