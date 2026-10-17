"""Regresiones BCP sobre main sin degradar facturas fiscales."""

from app.services.extraccion_campos import extraer_campos


def test_voucher_bcp_fecha_no_es_serie() -> None:
    texto = (
        "BCP\nTransferencia exitosa\nS/ 10,160.00\n"
        "Domingo, 20 Septiembre 2026 - 06:23 p.m.\n"
        "Concepto: pago de factura electrónica\n"
        "Número de operación\n03857359\n"
    )
    resultado = extraer_campos(texto, "OCR", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert campos["numero_operacion"]["valor"] == "03857359"
    assert campos["importe_total"]["valor"] == "10160.00"
    assert campos["fecha_emision"]["valor"] == "2026-09-20"
    assert campos["banco"]["valor"] == "BCP"
    assert "serie" not in campos
    assert "correlativo" not in campos


def test_factura_real_menciona_pago_bcp_y_preserva_serie() -> None:
    texto = (
        "FACTURA ELECTRONICA\nF001-00000123\n"
        "Forma de pago: transferencia BCP\n"
        "IMPORTE TOTAL S/ 120.00\n"
    )
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    assert resultado["campos"]["serie"]["valor"] == "F001"
    assert resultado["campos"]["correlativo"]["valor"] == "123"


def test_no_inferir_operacion_bcp_sin_identificador() -> None:
    resultado = extraer_campos("BCP\nTransferencia exitosa\nS/ 350.00", "OCR", 1.0)
    assert resultado is not None
    assert "numero_operacion" not in resultado["campos"]
