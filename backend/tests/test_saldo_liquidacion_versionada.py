"""Regresiones: cada pago se aplica una vez y la versión histórica no cambia."""

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.services.saldo_liquidacion_versionada import (
    LiquidacionVersionada,
    MovimientoLiquidacion,
    calcular_saldo,
)


def test_parcial_y_final_sin_recalcular_tasa_historica() -> None:
    original = LiquidacionVersionada("L-1", "tasa-2026-09", "PEN", Decimal("35.00"))
    movimientos = (
        MovimientoLiquidacion("voucher-1", Decimal("10.00"), "PEN"),
        MovimientoLiquidacion("voucher-2", Decimal("25.00"), "PEN"),
    )
    assert calcular_saldo(original, movimientos[:1]) == Decimal("25.00")
    assert calcular_saldo(original, movimientos) == Decimal("0.00")
    assert original.version_regla == "tasa-2026-09"
    with pytest.raises(FrozenInstanceError):
        original.bruto_aprobado = Decimal("99.00")  # type: ignore[misc]


@pytest.mark.parametrize(
    ("movimientos", "error"),
    [
        (
            (
                MovimientoLiquidacion("R1", Decimal("10.00"), "PEN"),
                MovimientoLiquidacion("R1", Decimal("10.00"), "PEN"),
            ),
            "duplicado",
        ),
        ((MovimientoLiquidacion("R1", Decimal("36.00"), "PEN"),), "supera saldo"),
        ((MovimientoLiquidacion("R1", Decimal("1.00"), "USD"),), "Moneda distinta"),
    ],
)
def test_rechaza_movimientos_inconsistentes(
    movimientos: tuple[MovimientoLiquidacion, ...], error: str
) -> None:
    liquidacion = LiquidacionVersionada("L-1", "v1", "PEN", Decimal("35.00"))
    with pytest.raises(ValueError, match=error):
        calcular_saldo(liquidacion, movimientos)


def test_rechaza_referencia_vacia_y_valor_con_mas_de_dos_decimales() -> None:
    with pytest.raises(ValueError, match="Referencia"):
        MovimientoLiquidacion(" ", Decimal("1.00"), "PEN")
    with pytest.raises(ValueError, match="céntimos"):
        MovimientoLiquidacion("R1", Decimal("1.001"), "PEN")
