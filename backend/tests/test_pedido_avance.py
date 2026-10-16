"""Pruebas de límites del semáforo de pedidos — Issue #242."""

from decimal import Decimal

import pytest

from app.services.pedido_avance import calcular_avance_pedido


@pytest.mark.parametrize(
    ("ejecutado", "estado"),
    [
        ("0", "VERDE"),
        ("99.99", "VERDE"),
        ("100", "NARANJA"),
        ("120", "NARANJA"),
        ("120.01", "ROJO"),
    ],
)
def test_limites_semaforo(ejecutado: str, estado: str) -> None:
    porcentaje, actual = calcular_avance_pedido(Decimal("100"), Decimal(ejecutado))
    assert porcentaje == Decimal(ejecutado)
    assert actual == estado


def test_exceso_no_se_recorta() -> None:
    porcentaje, estado = calcular_avance_pedido(Decimal("100"), Decimal("170"))
    assert porcentaje == Decimal("170")
    assert estado == "ROJO"


@pytest.mark.parametrize(("presupuesto", "ejecutado"), [("0", "1"), ("-5", "2"), ("5", "-1")])
def test_importes_invalidos(presupuesto: str, ejecutado: str) -> None:
    with pytest.raises(ValueError):
        calcular_avance_pedido(Decimal(presupuesto), Decimal(ejecutado))


def test_importes_grandes_con_precision_decimal() -> None:
    porcentaje, estado = calcular_avance_pedido(Decimal("500000"), Decimal("600000"))
    assert porcentaje == Decimal("120")
    assert estado == "NARANJA"
