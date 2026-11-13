"""Items: authenticated invoice drilldown, search, tenant isolation (synthetic DB)."""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Documento, Empresa, Expediente, Gestor, Miembro, Tenant
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
    foreign_emisor_id = None
    for tenant, suffix in ((tenant_a, "1"), (tenant_b.id, "2")):
        emisor = Empresa(tenant_id=tenant, ruc=f"2010000000{suffix}", razon_social="Emisor")
        receptor = Empresa(tenant_id=tenant, ruc=f"2020000000{suffix}", razon_social="Receptor")
        session.add_all([emisor, receptor])
        session.flush()
        if tenant == tenant_b.id:
            foreign_emisor_id = emisor.id
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

    catalog_invoices = client.get(
        f"/api/v1/contabilidad-items/productos/{product_id}/facturas",
        params={"vista_catalogo": True},
    )
    assert catalog_invoices.status_code == 200, catalog_invoices.text
    assert len(catalog_invoices.json()) == 1
    factura = catalog_invoices.json()[0]
    assert factura["emisor_ruc"] == "20100000001"
    assert factura["receptor_ruc"] == "20200000001"
    assert Decimal(factura["importe_total"]) == 60
    totales = client.get(
        f"/api/v1/contabilidad-items/productos/{product_id}/facturas",
        params={"vista_catalogo": True, "solo_totales": True, "offset": 50},
    )
    assert totales.status_code == 200, totales.text
    assert totales.json()[0]["comprobantes"] == "1"
    assert Decimal(totales.json()[0]["importe_total"]) == 60
    detalle = client.get(f"/api/v1/expedientes/{factura['expediente_id']}")
    assert detalle.status_code == 200, detalle.text
    assert detalle.json()["anterior_id"] is None
    assert detalle.json()["siguiente_id"] is None

    # Only the authorized tenant and operational roles may consult a product.
    assert foreign_emisor_id is not None
    foreign = client.get(
        f"/api/v1/contabilidad-items/productos/{product_id}/facturas",
        params={"emisor_id": str(foreign_emisor_id)},
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

    own_doc = session.get(Documento, UUID(invoices.json()[0]["documento_id"]))
    assert own_doc is not None
    own_doc.deleted_at = datetime.now(UTC)
    session.commit()
    inactive = client.get(f"/api/v1/contabilidad-items/productos/{product_id}/facturas")
    assert inactive.status_code == 200
    assert inactive.json() == []


def test_all_operational_roles_can_open_item_invoices_with_their_own_scope(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    contexto = auth_prueba.contexto
    tenant_id = contexto.tenant_id
    usuario_propio = session.get(Miembro, auth_prueba.usuario_id)
    assert usuario_propio is not None
    responsable_propio = Miembro(
        tenant_id=tenant_id,
        codigo="RESP-ITEMS-PROPIO",
        nombre="Responsable propio",
        rol="RESPONSABLE",
    )
    responsable_ajeno = Miembro(
        tenant_id=tenant_id,
        codigo="RESP-ITEMS-AJENO",
        nombre="Responsable ajeno",
        rol="RESPONSABLE",
    )
    gerente_propio = Miembro(
        tenant_id=tenant_id,
        codigo="GER-ITEMS-PROPIO",
        nombre="Gerente propio",
        rol="GERENTE",
    )
    gerente_ajeno = Miembro(
        tenant_id=tenant_id,
        codigo="GER-ITEMS-AJENO",
        nombre="Gerente ajeno",
        rol="GERENTE",
    )
    session.add_all([responsable_propio, responsable_ajeno, gerente_propio, gerente_ajeno])
    session.flush()
    usuario_propio.responsable_id = responsable_propio.id
    usuario_ajeno = Miembro(
        tenant_id=tenant_id,
        codigo="USU-ITEMS-AJENO",
        nombre="Usuario ajeno",
        rol="USUARIO",
        responsable_id=responsable_ajeno.id,
    )
    gestor_propio = session.get(Gestor, auth_prueba.gestor_id)
    assert gestor_propio is not None
    session.add(usuario_ajeno)
    session.flush()
    gestor_ajeno = Gestor(
        tenant_id=tenant_id,
        codigo="GST-ITEMS-AJENO",
        nombre="Gestor ajeno",
        usuario_id=usuario_ajeno.id,
    )
    session.add(gestor_ajeno)
    session.flush()

    emisor = Empresa(tenant_id=tenant_id, ruc="20100000001", razon_social="Emisor de prueba")
    receptor = Empresa(tenant_id=tenant_id, ruc="20200000001", razon_social="Receptor de prueba")
    session.add_all([emisor, receptor])
    session.flush()
    expedientes: list[Expediente] = []
    for correlativo, usuario, gerente, gestor in (
        ("1", usuario_propio, gerente_propio, gestor_propio),
        ("2", usuario_ajeno, gerente_ajeno, gestor_ajeno),
    ):
        expediente = Expediente(
            tenant_id=tenant_id,
            emisor_id=emisor.id,
            receptor_id=receptor.id,
            tipo_comprobante="FACT",
            serie="F001",
            correlativo=correlativo,
            fecha_emision=date(2026, 11, 1),
            moneda="PEN",
            importe_total=Decimal("60"),
            usuario_id=usuario.id,
            gerente_id=gerente.id,
            gestor_id=gestor.id,
        )
        session.add(expediente)
        session.flush()
        documento = Documento(
            tenant_id=tenant_id,
            expediente_id=expediente.id,
            tipo_documento="FACT",
            estado="RELACIONADO",
            sha256=correlativo * 64,
            nombre_original=f"factura-{correlativo}.xml",
            mime_type="text/xml",
            tamano_bytes=len(XML),
            ruta_storage=f"test/{correlativo}.xml",
        )
        session.add(documento)
        session.flush()
        assert registrar_items_ubl(session, tenant_id, documento.id, XML) == 1
        expedientes.append(expediente)
    session.commit()

    auth_prueba.como_admin()
    resumen = client.get("/api/v1/contabilidad-items", params={"buscar": "pota"})
    assert resumen.status_code == 200, resumen.text
    product_id = resumen.json()[0]["producto_id"]

    base = auth_prueba.contexto
    roles_y_cantidad = (
        ("ADMINISTRADOR", 2),
        ("SECRETARIA", 2),
        ("GERENTE", 1),
        ("RESPONSABLE", 1),
        ("USUARIO", 1),
        ("GESTOR", 1),
    )
    for rol, cantidad_esperada in roles_y_cantidad:
        auth_prueba.contexto = replace(
            base,
            rol=rol,
            miembro_id=responsable_propio.id if rol == "RESPONSABLE" else gerente_propio.id,
            usuario_id=usuario_propio.id if rol in {"USUARIO", "GESTOR"} else None,
            gestor_id=gestor_propio.id if rol == "GESTOR" else None,
        )
        resumen_rol = client.get("/api/v1/contabilidad-items", params={"buscar": "pota"})
        assert resumen_rol.status_code == 200, f"{rol}: {resumen_rol.text}"
        facturas = client.get(f"/api/v1/contabilidad-items/productos/{product_id}/facturas")
        assert facturas.status_code == 200, f"{rol}: {facturas.text}"
        assert len(facturas.json()) == cantidad_esperada, rol
        assert {fila["comprobante"] for fila in facturas.json()} == (
            {"F001-1", "F001-2"} if cantidad_esperada == 2 else {"F001-1"}
        )
