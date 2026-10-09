import uuid
from decimal import Decimal

import pytest

from app.services.comisiones import calcular_comisiones_por_receptor


def test_comisiones_por_receptor_y_global() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    base = {a: Decimal("1000"), b: Decimal("500")}
    r = calcular_comisiones_por_receptor(
        base,
        porcentajes_por_receptor={a: Decimal("2.5"), b: Decimal("3.5")},
    )
    assert r["total_produccion"] == Decimal("1500.00")
    assert r["comision_total"] == Decimal("42.50")
    otro = calcular_comisiones_por_receptor(base, porcentaje_global=Decimal("2"))
    assert otro["comision_total"] == Decimal("30.00")


def test_tarifa_faltante_no_usa_cero_automatico() -> None:
    with pytest.raises(ValueError, match="Falta porcentaje"):
        calcular_comisiones_por_receptor({uuid.uuid4(): Decimal("50")})


def test_no_admite_importes_negativos_ni_tasas_erroneas() -> None:
    cliente = uuid.uuid4()
    with pytest.raises(ValueError):
        calcular_comisiones_por_receptor(
            {cliente: Decimal("-1")}, porcentaje_global=Decimal("2")
        )
    with pytest.raises(ValueError):
        calcular_comisiones_por_receptor(
            {cliente: Decimal("100")}, porcentaje_global=Decimal("101")
        )
