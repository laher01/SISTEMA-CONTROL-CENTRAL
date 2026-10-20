"""Regresiones de fecha fiscal para tickets de combustible PDF fragmentados."""

from app.services.facturas_estaciones import extraer_factura_estacion


def test_jabsa_fecha_con_espacios_y_columnas() -> None:
    texto = """SERVICENTRO JABSA S.A. FACTURA DE VENTA ELECTRÓNICA
F003-00004475
Fecha   Emisión :   15 / 10 / 2026
RUC: 20374914201
TOTAL S/ 3492.00
"""
    campos = extraer_factura_estacion(texto)
    assert campos["fecha_emision"][0] == "2026-10-15"
    assert campos["serie"][0] == "F003"
    assert campos["correlativo"][0] == "00004475"


def test_jabsa_fecha_invertida_y_acentuada() -> None:
    texto = """SERVICENTRO JABSA S.A. FACTURA
15 / 10 / 2026  Fecha Emisión
F003-00004475
"""
    assert extraer_factura_estacion(texto)["fecha_emision"][0] == "2026-10-15"


def test_no_inferir_fecha_sin_etiqueta_jabsa() -> None:
    texto = "SERVICENTRO JABSA S.A. FACTURA F003-00004475 15/10/2026"
    assert "fecha_emision" not in extraer_factura_estacion(texto)


def test_otro_emisor_no_recibe_reglas_jabsa() -> None:
    texto = "EMPRESA DISTINTA FACTURA F003-00004475 Fecha Emision: 15/10/2026"
    assert extraer_factura_estacion(texto) == {}
