"""Prueba real SQLAlchemy/PostgreSQL: idempotencia y aislamiento multitenant."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.item_models import LineaComprobanteItem, ProductoItem
from app.models import Documento, Tenant
from app.services.contabilidad_items_ubl import (
    registrar_items_pdf_estacion,
    registrar_items_ubl,
)

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


TEXTO_ESCORPIO = (
    "www.facturacion.jadal.pe FACTURA ELECTRÓNICA F109 Nº 0016494 "
    "CANTIDAD CÓDIGO U.M DESCRIPCIÓN VALOR UNITARIO PRECIO UNITARIO IMPORTE "
    "49.499 09 GLL DIESEL B5 S50 20.31 23.96 1,005.08"
)


def test_pdf_escorpio_persiste_items_sin_duplicar(session: Session) -> None:
    tenant = Tenant(nombre="empresa_pdf")
    session.add(tenant)
    session.flush()
    documento = _documento(session, tenant.id)
    assert registrar_items_pdf_estacion(session, tenant.id, documento.id, TEXTO_ESCORPIO) == 1
    session.flush()
    assert registrar_items_pdf_estacion(session, tenant.id, documento.id, TEXTO_ESCORPIO) == 0
    linea = session.scalar(
        select(LineaComprobanteItem).where(LineaComprobanteItem.documento_id == documento.id)
    )
    assert linea is not None
    assert linea.descripcion_original == "DIESEL B5 S50"
    assert linea.cantidad == 49.499
    assert linea.unidad == "GLL"
    assert linea.importe_linea == 1005.08


def test_pdf_no_registra_si_no_es_factura_escorpio(session: Session) -> None:
    tenant = Tenant(nombre="empresa_control")
    session.add(tenant)
    session.flush()
    documento = _documento(session, tenant.id)
    assert registrar_items_pdf_estacion(session, tenant.id, documento.id, "GLL DIESEL B5 S50") == 0
    assert registrar_items_pdf_estacion(
        session, tenant.id, documento.id, TEXTO_ESCORPIO.replace("FACTURA", "GUIA")
    ) == 0
    assert registrar_items_pdf_estacion(
        session, tenant.id, documento.id, TEXTO_ESCORPIO + " " + TEXTO_ESCORPIO
    ) == 0
