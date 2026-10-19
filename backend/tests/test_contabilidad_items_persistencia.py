"""Prueba real SQLAlchemy/PostgreSQL: idempotencia y aislamiento multitenant."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from threading import Barrier

import pytest

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

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
    assert linea.cantidad == Decimal("49.499")
    assert linea.unidad == "GLL"
    assert linea.importe_linea == Decimal("1005.08")


def test_pdf_no_registra_si_no_es_factura_escorpio(session: Session) -> None:
    tenant = Tenant(nombre="empresa_control")
    session.add(tenant)
    session.flush()
    documento = _documento(session, tenant.id)
    assert registrar_items_pdf_estacion(session, tenant.id, documento.id, "GLL DIESEL B5 S50") == 0
    guia = TEXTO_ESCORPIO.replace("FACTURA", "GUIA")
    assert registrar_items_pdf_estacion(session, tenant.id, documento.id, guia) == 0
    duplicado = TEXTO_ESCORPIO + " " + TEXTO_ESCORPIO
    assert registrar_items_pdf_estacion(session, tenant.id, documento.id, duplicado) == 0


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


def test_concurrencia_mismo_tenant_un_catalogo_y_dos_lineas(engine):
    """Dos transacciones independientes no compiten al crear el mismo producto."""
    if engine.dialect.name != "postgresql":
        pytest.skip("Bloqueos SELECT FOR UPDATE requieren PostgreSQL")
    fabrica = sessionmaker(engine, expire_on_commit=False)
    with fabrica() as inicio:
        tenant = Tenant(nombre="tenant_ubl_concurrente")
        inicio.add(tenant)
        inicio.flush()
        primero = _documento(inicio, tenant.id)
        segundo = _documento(inicio, tenant.id)
        ids = (primero.id, segundo.id)
        tenant_id = tenant.id
        inicio.commit()

    barrera = Barrier(2)

    def registrar(documento_id: uuid.UUID) -> int:
        with fabrica() as conexion:
            barrera.wait(timeout=10)
            nuevos = registrar_items_ubl(conexion, tenant_id, documento_id, XML)
            conexion.commit()
            return nuevos

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(registrar, documento_id) for documento_id in ids]
        assert [f.result(timeout=30) for f in futures] == [1, 1]
    with fabrica() as comprobacion:
        assert comprobacion.scalar(select(func.count()).select_from(ProductoItem)) == 1
        assert comprobacion.scalar(select(func.count()).select_from(LineaComprobanteItem)) == 2
