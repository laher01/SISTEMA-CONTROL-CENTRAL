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


def test_tablas_sunat_sin_catalogo_previo_y_con_variantes_de_presentacion(session):
    tenant = Tenant(nombre="tablas_sunat")
    session.add(tenant)
    session.flush()
    cabecera = "FACTURA ELECTRÓNICA\nCantidad Unidad Medida Descripción Valor Unitario"
    primera = (
        cabecera
        + """ ICBPER
8.00 PAQUETE GATORADE 500 ML 17.80 0.00
12.00 PAQUETE AGUA SAN CARLOS 500 ML 11.017 0.00
8.00 PAQUETE INCA KOLA 600 ML 28.813 0.00
10.00 PAQUETE FRUGO FRESH 500 ML 14.41 0.00
8.00 PAQUETE GUARANA 450 ML 19.49 0.00
Valor de Venta de Operaciones Gratuitas : S/ 0.00
"""
    )
    segunda = (
        cabecera
        + """
8.00 CAJA PULP TETRA 22.882
10.00 PAQUETE SPORADE 500ML 18.644
6.00 PAQUETE INCA KOLA 600ML 28.812
8.00 PAQUETE AGUA SAN LUIS 750 ML 15.255
8.00 PAQUETE VOLT 300 ML 18.644
Sub Total Ventas S/ 813.56
"""
    )
    for texto in (primera, segunda):
        documento = _documento(session, tenant.id)
        assert registrar_items_pdf_estacion(session, tenant.id, documento.id, texto) == 5
        session.flush()
        assert registrar_items_pdf_estacion(session, tenant.id, documento.id, texto) == 0
    assert session.scalar(select(func.count()).select_from(ProductoItem)) == 9
    producto = session.scalar(
        select(ProductoItem).where(ProductoItem.descripcion == "INCA KOLA 600 ML")
    )
    assert producto is not None
    assert producto.unidad_base == "PAQUETE"
    assert session.scalar(
        select(func.sum(LineaComprobanteItem.cantidad)).where(
            LineaComprobanteItem.producto_id == producto.id
        )
    ) == Decimal("14")


def test_ticket_combustible_lee_descripciones_y_no_el_total_fiscal(session):
    tenant = Tenant(nombre="ticket_combustible")
    session.add(tenant)
    session.flush()
    documento = _documento(session, tenant.id)
    texto = """FACTURA ELECTRÓNICA F001-5
Descripción Cant. U.M. P. Unit. Total
PETROLEO DIESEL 12.50 GAL 15.00 187.50
ACEITE 20W50 2.00 UND 25.00 50.00
IMPORTE TOTAL S/ 237.50
"""
    assert registrar_items_pdf_estacion(session, tenant.id, documento.id, texto) == 2
    assert registrar_items_pdf_estacion(session, tenant.id, documento.id, texto) == 0
    assert set(session.scalars(select(LineaComprobanteItem.descripcion_original))) == {
        "PETROLEO DIESEL",
        "ACEITE 20W50",
    }


def test_tabla_columnas_reordenadas_lee_producto_real(session):
    tenant = Tenant(nombre="tabla_columnas")
    session.add(tenant)
    session.flush()
    documento = _documento(session, tenant.id)
    texto = """FACTURA
Código  Producto  U.M.  Cantidad  Precio unitario  Importe
09  DIESEL B5 S50  GLL  49.499  23.96  1,005.08
10  LUBRICANTE SINTÉTICO  UND  2.00  25.00  50.00
Importe Total S/ 1055.08
"""
    assert registrar_items_pdf_estacion(session, tenant.id, documento.id, texto) == 2
    assert registrar_items_pdf_estacion(session, tenant.id, documento.id, texto) == 0
    lineas = list(session.scalars(select(LineaComprobanteItem)))
    assert [(linea.descripcion_original, linea.cantidad, linea.unidad) for linea in lineas] == [
        ("DIESEL B5 S50", Decimal("49.499"), "GLL"),
        ("LUBRICANTE SINTÉTICO", Decimal("2"), "UND"),
    ]


def test_tabla_san_jose_con_encabezado_und():
    from app.services.contabilidad_items_ubl import extraer_items_pdf

    texto = (
        "FACTURA ELECTRÓNICA F091-00007289\n"
        "Ítem  Código  Descripción  Und.  Cantidad  "
        "V. Unitario  P. Unitario  Descuento  Valor Venta\n"
        "1  05  DIESEL B5UV S50  GLL  300.00  19.92  23.50  0.00  5,974.58\n"
        "Sub Total  S/  5,974.58\n"
    )
    items = extraer_items_pdf(texto)
    assert len(items) == 1
    assert items[0].descripcion == "DIESEL B5UV S50"
    assert items[0].unidad == "GLL"
    assert items[0].cantidad == Decimal("300.00")
    assert items[0].importe == Decimal("5974.58")
