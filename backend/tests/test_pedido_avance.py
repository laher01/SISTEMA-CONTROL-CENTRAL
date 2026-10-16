"""Pruebas de límites del semáforo de pedidos — Issue #242."""

from decimal import Decimal

import pytest

from app.services.pedido_avance import calcular_avance_consolidado, calcular_avance_pedido


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


def test_consolidado_pondera_importes_no_porcentajes() -> None:
    porcentaje, estado = calcular_avance_consolidado(
        [
            (Decimal("900"), Decimal("900")),
            (Decimal("100"), Decimal("0")),
        ]
    )
    assert porcentaje == Decimal("90")
    assert estado == "VERDE"


def test_consolidado_con_exceso() -> None:
    porcentaje, estado = calcular_avance_consolidado(
        [
            (Decimal("200"), Decimal("250")),
            (Decimal("300"), Decimal("350")),
        ]
    )
    assert porcentaje == Decimal("120")
    assert estado == "NARANJA"


def test_consolidado_vacio_o_invalido() -> None:
    with pytest.raises(ValueError):
        calcular_avance_consolidado([])
    with pytest.raises(ValueError):
        calcular_avance_consolidado([(Decimal("10"), Decimal("-1"))])


@pytest.mark.parametrize("invalido", ["NaN", "Infinity", "-Infinity"])
def test_importes_no_finitos_rechazados(invalido: str) -> None:
    with pytest.raises(ValueError):
        calcular_avance_pedido(Decimal(invalido), Decimal("1"))
    with pytest.raises(ValueError):
        calcular_avance_pedido(Decimal("10"), Decimal(invalido))
    with pytest.raises(ValueError):
        calcular_avance_consolidado([(Decimal("10"), Decimal(invalido))])
