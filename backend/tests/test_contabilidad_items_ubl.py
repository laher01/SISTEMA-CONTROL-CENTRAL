"""Verificaciones de extracción de líneas UBL, sin acceso a datos productivos."""

from decimal import Decimal

from app.services.contabilidad_items_ubl import extraer_items_ubl

UBL = b"""<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
<cac:InvoiceLine>
  <cbc:InvoicedQuantity unitCode="NIU">12</cbc:InvoicedQuantity>
  <cbc:LineExtensionAmount>36.00</cbc:LineExtensionAmount>
  <cac:Item><cbc:Description>Leche Gloria 400 g Clasica</cbc:Description></cac:Item>
</cac:InvoiceLine>
<cac:InvoiceLine>
  <cbc:InvoicedQuantity unitCode="KGM">2.5</cbc:InvoicedQuantity>
  <cbc:LineExtensionAmount>15.50</cbc:LineExtensionAmount>
  <cac:Item><cbc:Name>Pota congelada</cbc:Name></cac:Item>
</cac:InvoiceLine>
</Invoice>"""


def test_lineas_ubl_preservan_cantidad_unidad_precio_y_descripcion():
    items = extraer_items_ubl(UBL)
    assert len(items) == 2
    assert items[0].descripcion == "Leche Gloria 400 g Clasica"
    assert items[0].cantidad == Decimal("12")
    assert items[0].unidad == "NIU"
    assert items[0].importe == Decimal("36.00")
    assert items[1].cantidad == Decimal("2.5")
    assert items[1].unidad == "KGM"


def test_xml_malicioso_y_xml_no_factura_no_aportan_items():
    assert extraer_items_ubl(b"<a/>") == []
    prohibido = b'<!DOCTYPE a [<!ENTITY x SYSTEM "file:///etc/passwd">]><a>&x;</a>'
    assert extraer_items_ubl(prohibido) == []


def test_cantidades_invalidas_no_se_contabilizan():
    xml = UBL.replace(b">12<", b">-10<")
    items = extraer_items_ubl(xml)
    assert len(items) == 1
    assert items[0].descripcion == "Pota congelada"
