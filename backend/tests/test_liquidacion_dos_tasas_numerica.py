"""Pruebas monetarias de liquidaciones por clasificación de empresas.

Los saldos de meses anteriores requieren conservar la tasa histórica: no
se les debe aplicar automáticamente la tasa efectiva del periodo actual.
"""

from decimal import Decimal

import pytest

from app.services.liquidacion_dos_tasas import FacturaProduccion, liquidar_dos_tasas


def test_bruto_adelanto_y_neto_con_dos_tasas() -> None:
    resultado = liquidar_dos_tasas(
        [
            FacturaProduccion(Decimal("20000.00"), agente_retencion=True),
            FacturaProduccion(Decimal("15000.00"), agente_retencion=False),
        ],
        porcentaje_con_agente=Decimal("2.35"),
        porcentaje_sin_agente=Decimal("2.85"),
        adelantos=Decimal("150.00"),
    )
    assert resultado["produccion_con_agente"] == Decimal("20000.00")
    assert resultado["produccion_sin_agente"] == Decimal("15000.00")
    assert resultado["bruto_con_agente"] == Decimal("470.00")
    assert resultado["bruto_sin_agente"] == Decimal("427.50")
    assert resultado["bruto"] == Decimal("897.50")
    assert resultado["adelantos"] == Decimal("150.00")
    assert resultado["neto"] == Decimal("747.50")


def test_usuario_tasa_identica_con_o_sin_agente() -> None:
    resultado = liquidar_dos_tasas(
        [
            FacturaProduccion(Decimal("5000.00"), True),
            FacturaProduccion(Decimal("5000.00"), False),
        ],
        porcentaje_con_agente=Decimal("2.70"),
        porcentaje_sin_agente=Decimal("2.70"),
        adelantos=Decimal("0"),
    )
    assert resultado["bruto"] == Decimal("270.00")


def test_redondeo_y_adelanto_mayor_que_bruto() -> None:
    resultado = liquidar_dos_tasas(
        [FacturaProduccion(Decimal("100.50"), True)],
        porcentaje_con_agente=Decimal("1.00"),
        porcentaje_sin_agente=Decimal("2.00"),
        adelantos=Decimal("2.00"),
    )
    assert resultado["bruto"] == Decimal("1.01")
    assert resultado["neto"] == Decimal("-0.99")


@pytest.mark.parametrize("adelanto", [Decimal("-1"), Decimal("NaN")])
def test_rechazar_adelantos_invalidos(adelanto: Decimal) -> None:
    with pytest.raises(ValueError, match="Adelantos inválidos"):
        liquidar_dos_tasas(
            [],
            porcentaje_con_agente=Decimal("2"),
            porcentaje_sin_agente=Decimal("3"),
            adelantos=adelanto,
        )
