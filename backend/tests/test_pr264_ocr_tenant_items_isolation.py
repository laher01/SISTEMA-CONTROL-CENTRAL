"""Isolated API tenant/RBAC regression and UBL line idempotency checks."""

from dataclasses import replace
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.item_models import LineaComprobanteItem, ProductoItem
from app.models import CuentaAcceso, Documento, Miembro, Tenant
from app.services.contabilidad_items_ubl import registrar_items_ubl

UBL = b"""<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
<cac:InvoiceLine><cbc:InvoicedQuantity unitCode="KGM">2.5</cbc:InvoicedQuantity>
<cbc:LineExtensionAmount>15.50</cbc:LineExtensionAmount>
<cac:Item><cbc:Description>Pota congelada</cbc:Description></cac:Item></cac:InvoiceLine>
</Invoice>"""


def test_documentos_no_cruzan_dos_tenants_y_no_rechazan_mismo_hash(
    client, session: Session, auth_prueba
):
    """Same bytes are legal in separate tenants; credentials cannot cross-read."""
    tenant_a = auth_prueba.contexto.tenant_id
    contexto_a = auth_prueba.contexto
    tenant_b = Tenant(nombre="Tenant B aislado", codigo="PR264-B", estado="ACTIVO")
    session.add(tenant_b)
    session.flush()
    miembro_b = Miembro(
        tenant_id=tenant_b.id, codigo="B-USR", nombre="Usuario B", rol="USUARIO", activo=True
    )
    session.add(miembro_b)
    session.flush()
    cuenta_b = CuentaAcceso(
        tenant_id=tenant_b.id,
        miembro_id=miembro_b.id,
        login="B-USR",
        password_hash="test-hash",
        activo=True,
        cambio_clave_obligatorio=False,
    )
    session.add(cuenta_b)
    session.commit()
    contexto_b = replace(
        contexto_a,
        tenant_id=tenant_b.id,
        cuenta_id=cuenta_b.id,
        miembro_id=miembro_b.id,
        usuario_id=miembro_b.id,
        codigo="B-USR",
        nombre="Usuario B",
    )
    payload = b"archivos-documentales-de-prueba-identicos-entre-tenants"

    def upload():
        return client.post(
            "/api/v1/documentos",
            files={"archivo": ("evidencia.bin", payload, "application/octet-stream")},
            data={"tipo_documento": "OTRO"},
        )

    auth_prueba.contexto = contexto_a
    creado_a = upload()
    assert creado_a.status_code == 201, creado_a.text
    id_a = creado_a.json()["id"]

    auth_prueba.contexto = contexto_b
    creado_b = upload()
    assert creado_b.status_code == 201, creado_b.text
    id_b = creado_b.json()["id"]
    assert id_a != id_b
    assert client.get(f"/api/v1/documentos/{id_a}").status_code == 404
    assert client.get(f"/api/v1/documentos/{id_b}").status_code == 200
    listado_b = client.get("/api/v1/documentos")
    assert listado_b.status_code == 200, listado_b.text
    assert id_a not in {item["id"] for item in listado_b.json()}
    auth_prueba.contexto = contexto_a
    assert client.get(f"/api/v1/documentos/{id_b}").status_code == 404
    assert client.get(f"/api/v1/documentos/{id_a}").status_code == 200

    assert session.scalar(
        select(func.count()).select_from(Documento).where(
            Documento.tenant_id.in_((tenant_a, tenant_b.id))
        )
    ) == 2


def test_lineas_ubl_idempotentes_y_aisladas_por_tenant(session: Session, auth_prueba):
    """Reprocessing must not double count monetary lines or reuse another tenant's catalog."""
    tenant_a = auth_prueba.contexto.tenant_id
    tenant_b = Tenant(nombre="Tenant contable B", codigo="PR264-ITEM-B", estado="ACTIVO")
    session.add(tenant_b)
    session.flush()
    docs = []
    for tenant_id, sha in ((tenant_a, "a" * 64), (tenant_b.id, "b" * 64)):
        doc = Documento(
            tenant_id=tenant_id,
            sha256=sha,
            nombre_original="items.xml",
            mime_type="application/xml",
            tamano_bytes=len(UBL),
            ruta_storage=f"pruebas/{sha}",
            estado="PENDIENTE",
            tipo_documento="FACT",
        )
        session.add(doc)
        session.flush()
        docs.append(doc)
    session.commit()
    for doc in docs:
        assert registrar_items_ubl(session, doc.tenant_id, doc.id, UBL) == 1
        session.flush()
        assert registrar_items_ubl(session, doc.tenant_id, doc.id, UBL) == 0
    session.commit()
    for doc in docs:
        lineas = list(
            session.scalars(
                select(LineaComprobanteItem).where(
                    LineaComprobanteItem.tenant_id == doc.tenant_id,
                    LineaComprobanteItem.documento_id == doc.id,
                )
            )
        )
        assert len(lineas) == 1
        assert lineas[0].importe_linea == Decimal("15.50")
        assert lineas[0].cantidad == Decimal("2.5")
        assert (
            session.scalar(
                select(func.count()).select_from(ProductoItem).where(
                    ProductoItem.tenant_id == doc.tenant_id,
                )
            )
            == 1
        )
    assert docs[0].tenant_id != docs[1].tenant_id
