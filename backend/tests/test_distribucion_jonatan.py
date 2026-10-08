from decimal import Decimal

import pytest

from app.services.distribucion_jonatan import TasasJonatan, calcular_distribucion_jonatan


def test_pago_sobre_pedido_manual_sin_alex() -> None:
    r = calcular_distribucion_jonatan(
        total_emitido=Decimal("1114897.76"),
        base_autorizada=Decimal("378000.00"),
    )
    assert r.bruto == Decimal("11340.00")
    assert r.gente_lima == Decimal("8505.00")
    assert r.javier == Decimal("472.50")
    assert r.jonatan == Decimal("1181.25")
    assert r.neto == Decimal("10158.75")
    assert r.excluido_alex == Decimal("1181.25")
    assert r.gente_lima + r.javier + r.jonatan == r.neto
    assert r.modo_base == "MANUAL"


def test_pago_total_emitido_exige_confirmacion() -> None:
    with pytest.raises(ValueError):
        calcular_distribucion_jonatan(total_emitido=Decimal("1114897.76"))
    with pytest.raises(ValueError):
        calcular_distribucion_jonatan(
            total_emitido=Decimal("1114897.76"), base_autorizada=Decimal("0")
        )
    r = calcular_distribucion_jonatan(total_emitido=Decimal("1114897.76"), usar_total_emitido=True)
    assert r.bruto == Decimal("33446.93")
    assert r.gente_lima == Decimal("25085.20")
    assert r.javier == Decimal("1393.62")
    assert r.jonatan == Decimal("3484.06")
    assert r.neto == Decimal("29962.88")
    assert r.excluido_alex == Decimal("3484.05")
    assert r.gente_lima + r.javier + r.jonatan == r.neto


def test_tasas_personalizadas_y_validaciones() -> None:
    with pytest.raises(ValueError):
        calcular_distribucion_jonatan(total_emitido=Decimal("100"), base_autorizada=Decimal("120"))
    with pytest.raises(ValueError):
        calcular_distribucion_jonatan(
            total_emitido=Decimal("100"),
            base_autorizada=Decimal("100"),
            tasas=TasasJonatan(jonatan=Decimal("0.500")),
        )
