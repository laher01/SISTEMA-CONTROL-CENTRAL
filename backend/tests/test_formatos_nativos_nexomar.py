"""Regresiones sintéticas de estructuras PDF; sin datos de clientes reales."""

from decimal import Decimal

from app.services.extraccion_campos import extraer_campos
from app.services.items_formatos_nativos import extraer_items_nativos


def test_factcentral_prioriza_total_fiscal_y_partes():
    texto = """EMPRESA DE PRUEBA E.I.R.L.
RUC 20100000001
FACTURA ELECTRÓNICA
F002-00000001
FECHA DE EMISIÓN : 2026-02-17
Cliente: COMPRADOR DE PRUEBA
S.A.C.
RUC: 20100000002
COD. CANT. UNIDAD DESCRIPCIÓN P.UNIT TOTAL
00189 12 NIU Producto de prueba
segunda línea
1.40 16.80
OP. GRAVADAS: S/ 14.24
IGV: S/ 2.56
TOTAL A PAGAR: S/ 16.80
https://demo.factcentral.online/buscar"""
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert isinstance(campos, dict)
    assert campos["importe_total"]["valor"] == "16.80"
    assert campos["ruc_emisor"]["valor"] == "20100000001"
    assert campos["razon_social_receptor"]["valor"] == "COMPRADOR DE PRUEBA S.A.C."
    assert extraer_items_nativos(texto) == [
        ("Producto de prueba segunda línea", Decimal(12), "NIU", Decimal("16.80"))
    ]


def test_facturalaya_ignora_moneda_de_cuenta_bancaria_y_reconcilia_renglones():
    texto = """EMPRESA DE PRUEBA EIRL - 20100000001
FACTURA ELECTRÓNICA
F002 - 000001
N° cuenta (Dólares): 123456789
Cant.
Descripción
Precio
Importe
2
Producto de prueba
de dos líneas
3.5
7.00
Gravada: S/ 5.93
Descuento Total: S/ 0.00
Total: S/ 7.00
facturalaya.com"""
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert isinstance(campos, dict)
    assert campos["moneda"]["valor"] == "PEN"
    assert campos["importe_total"]["valor"] == "7.00"
    assert extraer_items_nativos(texto) == [
        ("Producto de prueba de dos líneas", Decimal(2), "NIU", Decimal("7.00"))
    ]
    assert extraer_items_nativos(texto.replace("Total: S/ 7.00", "Total: S/ 8.00")) == []


def test_efact_fecha_abreviada_y_base_sin_igv():
    texto = """FACTURA ELECTRÓNICA
F001-000001
27-abr-2026
Fecha de Emisión:
CÓDIGO CANT. UNID. DESCRIPCIÓN V. UNIT. DSCTO. V. VENTA
2 TON Producto a granel 10.00 0.00 20.00
OBSERVACIONES
SUB TOTAL S/ 20.00
IGV S/ 3.60
TOTAL S/ 23.60
www.efact.pe"""
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert isinstance(campos, dict)
    assert campos["fecha_emision"]["valor"] == "2026-04-27"
    assert extraer_items_nativos(texto) == [
        ("Producto a granel", Decimal(2), "TON", Decimal("20.00"))
    ]
