"""Prueba real SQLAlchemy/PostgreSQL: idempotencia y aislamiento multitenant."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.item_models import LineaComprobanteItem, ProductoItem
from app.models import Documento, Tenant
from app.services.contabilidad_items_ubl import registrar_items_ubl

XML = b"""<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
<cac:InvoiceLine><cbc:InvoicedQuantity unitCode="KGM">12.5</cbc:InvoicedQuantity>
<cac:Item><cbc:Name>Pota congelada</cbc:Name></cac:Item></cac:InvoiceLine>
</Invoice>"""


def _documento(session: Session, tenant_id: uuid.UUID) -> Documento:
    documento = Documento(
        tenant_id=tenant_id,
        estado="PENDIENTE_RELACION",
        sha256=uuid.uuid4().hex.ljust(64, "0"),
        nombre_original="factura.xml",
        mime_type="text/xml",
        tamano_bytes=len(XML),
        ruta_storage="pruebas/no-se-usa.xml",
    )
    session.add(documento)
    session.flush()
    return documento


def test_items_ubl_idempotentes_y_separados_por_tenant(session: Session):
    primero = Tenant(nombre="empresa_a")
    segundo = Tenant(nombre="empresa_b")
    session.add_all([primero, segundo])
    session.flush()
    a = _documento(session, primero.id)
    b = _documento(session, segundo.id)

    assert registrar_items_ubl(session, primero.id, a.id, XML) == 1
    session.flush()
    assert registrar_items_ubl(session, primero.id, a.id, XML) == 0
    assert registrar_items_ubl(session, segundo.id, b.id, XML) == 1
    session.flush()

    assert session.scalar(select(func.count()).select_from(LineaComprobanteItem)) == 2
    assert session.scalar(select(func.count()).select_from(ProductoItem)) == 2
    productos = list(session.scalars(select(ProductoItem)))
    assert productos[0].tenant_id != productos[1].tenant_id


def test_reescaneo_rechaza_documento_de_otro_tenant(session: Session):
    propietario = Tenant(nombre="propietario_xml")
    ajeno = Tenant(nombre="tenant_ajeno_xml")
    session.add_all([propietario, ajeno])
    session.flush()
    documento = _documento(session, propietario.id)

    with pytest.raises(ValueError, match="tenant autorizado"):
        registrar_items_ubl(session, ajeno.id, documento.id, XML)

    session.flush()
    assert session.scalar(select(func.count()).select_from(LineaComprobanteItem)) == 0
    assert session.scalar(select(func.count()).select_from(ProductoItem)) == 0


def test_reescaneo_rechaza_documento_inexistente(session: Session):
    propietario = Tenant(nombre="tenant_xml_inexistente")
    session.add(propietario)
    session.flush()

    with pytest.raises(ValueError, match="tenant autorizado"):
        registrar_items_ubl(session, propietario.id, uuid.uuid4(), XML)

    assert session.scalar(select(func.count()).select_from(LineaComprobanteItem)) == 0


def test_reescaneo_rechaza_documento_eliminado(session: Session):
    propietario = Tenant(nombre="tenant_xml_eliminado")
    session.add(propietario)
    session.flush()
    documento = _documento(session, propietario.id)
    documento.deleted_at = datetime.now(UTC)
    session.flush()

    with pytest.raises(ValueError, match="tenant autorizado"):
        registrar_items_ubl(session, propietario.id, documento.id, XML)

    assert session.scalar(select(func.count()).select_from(LineaComprobanteItem)) == 0


def test_reescaneo_rechaza_tenant_inexistente_sin_crear_lineas(session: Session):
    with pytest.raises(ValueError, match="Tenant no encontrado"):
        registrar_items_ubl(session, uuid.uuid4(), uuid.uuid4(), XML)

    assert session.scalar(select(func.count()).select_from(LineaComprobanteItem)) == 0
    assert session.scalar(select(func.count()).select_from(ProductoItem)) == 0
