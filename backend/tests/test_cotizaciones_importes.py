"""Regresión del total comercial de las cotizaciones COMPOSTELA."""

import pytest

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
    texto = "COTIZACION No. 00861\nSUB TOTAL: S/ 4,411.99\nIGV 18%: S/ 794.16\nTOTAL: S/ 1.00\n"
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    assert "importe_total" not in resultado["campos"]


def test_cliente_ruc_no_es_atribuido_a_emisor_cotizacion() -> None:
    texto = "COTIZACION No. 00861\nCOMPOSTELA INVERSIONES GENERALES\nCLIENTE RUC 20538821374"
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert campos["ruc_receptor"]["valor"] == "20538821374"
    assert "ruc_emisor" not in campos


def test_partes_comerciales_con_etiquetas_explicitas() -> None:
    texto = (
        "COTIZACION No. 00861\n"
        "PROVEEDOR: COMPOSTELA INVERSIONES GENERALES\n"
        "CLIENTE: INVERSIONES Y NEGOCIACIONES MAREUF E.I.R.L.\n"
        "CLIENTE RUC 20538821374\n"
    )
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert campos["ruc_receptor"]["valor"] == "20538821374"
    assert campos["razon_social_receptor"]["valor"] == "INVERSIONES Y NEGOCIACIONES MAREUF E.I.R.L."
    assert campos["razon_social_emisor"]["valor"] == "COMPOSTELA INVERSIONES GENERALES"
    assert "ruc_emisor" not in campos


@pytest.mark.parametrize(
    ("subtotal", "igv", "total"),
    [
        ("5,305.50", "954.99", "6,260.49"),
        ("4,410.40", "793.87", "5,204.27"),
        ("4,177.00", "751.86", "4,928.86"),
        ("5,125.18", "922.53", "6,047.71"),
        ("4,411.99", "794.16", "5,206.15"),
    ],
)
def test_cotizacion_real_pdf_columnas_antes_de_etiquetas(
    subtotal: str, igv: str, total: str
) -> None:
    # Fragmento reproducido de la disposición de texto real en 5 páginas,
    # sin incluir nombres, RUC ni otros datos personales del PDF.
    texto = (
        "COTIZACIÓN\nNº 00861\nCANT UND COSTO TOTAL\n"
        "1 UND 4.30 S/   4.30S/\n"
        f"{subtotal}S/\n{igv}S/\n{total}S/\n"
        "NOTA: DURACIÓN DE LA COTIZACIÓN ES POR 30 DÍAS\n"
        "SUB TOTAL\nIGV 18%\nTOTAL"
    )
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    assert resultado["campos"]["importe_total"]["valor"] == total.replace(",", "")


def test_cotizacion_columnas_sin_cuadre_no_asume_total() -> None:
    texto = (
        "COTIZACIÓN\nCANT UND COSTO TOTAL\n1 UND 2.00S/\n"
        "4,411.99S/\n794.16S/\n1.00S/\n"
        "NOTA: DURACIÓN DE LA COTIZACIÓN\nSUB TOTAL\nIGV 18%\nTOTAL"
    )
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    assert "importe_total" not in resultado["campos"]
