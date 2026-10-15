"""Regresión del total comercial de las cotizaciones COMPOSTELA."""

from app.services.extraccion_campos import extraer_campos


def test_cotizacion_compostela_prioriza_total_verificado() -> None:
    texto = (
        "COTIZACION No. 00861\n"
        "FECHA DE EMISION: 25/08/2026\n"
        "CLIENTE RUC 20538821374\n"
        "ITEM CANTIDAD PRECIO\n"
        "1  1  1.00\n"
        "SUB TOTAL: S/ 4,411.99\n"
        "IGV 18%: S/ 794.16\n"
        "TOTAL: S/ 5,206.15\n"
    )
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    assert resultado["campos"]["importe_total"]["valor"] == "5206.15"
    assert resultado["campos"]["importe_total"]["requiere_confirmacion"] is True


def test_cotizacion_inconsistente_no_inventa_total() -> None:
    texto = (
        "COTIZACION No. 00861\n"
        "SUB TOTAL: S/ 4,411.99\n"
        "IGV 18%: S/ 794.16\n"
        "TOTAL: S/ 1.00\n"
    )
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    assert "importe_total" not in resultado["campos"]
