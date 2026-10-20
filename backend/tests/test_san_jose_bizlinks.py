"""Regresión Bizlinks: etiquetas fragmentadas o invertidas por pypdf.

Datos sintéticos de estructura reproducida con 17 PDF aportados; sin documentos
fiscales originales ni datos del cliente incorporados al repositorio.
"""

import pytest

from app.services.facturas_estaciones import extraer_factura_estacion


@pytest.mark.parametrize(
    ("numero", "fecha", "monto"),
    [
        ("00007211", "29/09/2026", "28,800.00"),
        ("00007270", "07/10/2026", "9,400.00"),
        ("00007271", "07/10/2026", "5,875.00"),
        ("00007229", "02/10/2026", "7,200.00"),
    ],
)
def test_san_jose_bizlinks_valores_antes_de_etiquetas(numero: str, fecha: str, monto: str) -> None:
    texto = (
        "ESTACION DE SERVICIOS SAN JOSE SAC\n"
        "R.U.C.\nELECTRÓNICA\n20175642341\nFACTURA\nF091-" + numero + "\n"
        "Cliente: EMPRESA DE PRUEBA E.I.R.L.\n"
        "20999999991 N° Guía Remisión: -RUC:\n" + fecha + " N° SCOP: -Fecha Emisión:\n"
        "Moneda: Sol\n"
        "Sub Total 100.00S/\n"
        "Importe Total " + monto + "S/\n"
        "Representación Impresa de la Factura Electrónica\nPowered by Bizlinks\n"
    )
    campos = extraer_factura_estacion(texto)
    assert campos["serie"][0] == "F091"
    assert campos["correlativo"][0] == numero
    assert campos["ruc_emisor"][0] == "20175642341"
    assert campos["ruc_receptor"][0] == "20999999991"
    assert campos["fecha_emision"][0] == fecha[6:10] + "-" + fecha[3:5] + "-" + fecha[:2]
    assert campos["importe_total"][0] == monto.replace(",", "")
    assert campos["moneda"][0] == "PEN"


def test_san_jose_no_infiere_receptor_ambiguo() -> None:
    texto = (
        "ESTACION DE SERVICIOS SAN JOSE SAC\n"
        "20175642341\nFACTURA\nF091-00007211\n"
        "Cliente: EMPRESA DE PRUEBA\n20999999991\n20999999992\nDirección:\n"
        "29/09/2026 N° SCOP: -Fecha Emisión:\n"
        "Importe Total 28,800.00S/\nPowered by Bizlinks"
    )
    assert "ruc_receptor" not in extraer_factura_estacion(texto)
