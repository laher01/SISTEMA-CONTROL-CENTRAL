from decimal import Decimal

import pytest

from app.services.calculo_comision_usuario import LineaComision, calcular_comision_documentada


def test_comision_dual_por_documento() -> None:
    resultado = calcular_comision_documentada([
        LineaComision("a", Decimal("60000"), Decimal("1.5"), "SIN_AGENTE"),
        LineaComision("b", Decimal("40000"), Decimal("1.0"), "CON_AGENTE"),
    ])
    assert resultado["produccion_sin"] == Decimal("60000")
    assert resultado["produccion_con"] == Decimal("40000")
    assert resultado["comision_sin"] == Decimal("900.00")
    assert resultado["comision_con"] == Decimal("400.00")
    assert resultado["comision_total"] == Decimal("1300.00")


@pytest.mark.parametrize("lineas", [
    [LineaComision("a", Decimal("100"), Decimal("1"), "DESCONOCIDO")],
    [LineaComision("a", Decimal("100"), Decimal("101"), "CON_AGENTE")],
    [
        LineaComision("a", Decimal("100"), Decimal("1"), "SIN_AGENTE"),
        LineaComision("a", Decimal("100"), Decimal("1"), "SIN_AGENTE"),
    ],
])
def test_rechaza_calculo_no_confiable(lineas: list[LineaComision]) -> None:
    with pytest.raises(ValueError):
        calcular_comision_documentada(lineas)


def test_redondeo_documento_a_documento() -> None:
    resultado = calcular_comision_documentada([
        LineaComision("a", Decimal("1.00"), Decimal("0.5"), "SIN_AGENTE"),
        LineaComision("b", Decimal("1.00"), Decimal("0.5"), "SIN_AGENTE"),
    ])
    assert resultado["comision_total"] == Decimal("0.02")
