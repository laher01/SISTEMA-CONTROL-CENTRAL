"""Protecciones de exportación para archivos de hojas de cálculo."""

from app.api.routes.contabilidad_items import _celda_csv


def test_csv_escapa_formulas_y_conserva_texto():
    assert _celda_csv("=1+1") == "'=1+1"
    assert _celda_csv("+SUM(A1:A2)") == "'+SUM(A1:A2)"
    assert _celda_csv("@comando") == "'@comando"
    assert _celda_csv("  =HYPERLINK('x')") == "'  =HYPERLINK('x')"
    assert _celda_csv("Pota congelada") == "Pota congelada"
