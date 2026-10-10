"""Casos numéricos verificables para comisiones sin mutación de datos."""

import uuid
from decimal import Decimal

import pytest

from app.services.comisiones import calcular_comisiones_por_receptor, comision_por_condicion_retencion


def test_comision_dos_receptores_calcula_bruto_total() -> None:
    a=uuid.UUID("00000000-0000-0000-0000-000000000001")
    b=uuid.UUID("00000000-0000-0000-0000-000000000002")
    resultado=calcular_comisiones_por_receptor(
        {a: Decimal("10000.00"), b: Decimal("5000.00")},
        porcentajes_por_receptor={a: Decimal("1.50"), b: Decimal("2.00")},
    )
    assert resultado["total_produccion"]==Decimal("15000.00")
    assert resultado["comision_total"]==Decimal("250.00")
    assert [item["comision"] for item in resultado["detalle"]]==["150.00","100.00"]


def test_redondeo_comision_al_centimo() -> None:
    receptor=uuid.uuid4()
    resultado=calcular_comisiones_por_receptor(
        {receptor: Decimal("100.50")}, porcentaje_global=Decimal("1.00")
    )
    assert resultado["comision_total"]==Decimal("1.01")


@pytest.mark.parametrize("tasa", [Decimal("-1"), Decimal("100.01")])
def test_rechaza_tasas_fuera_de_rango(tasa: Decimal) -> None:
    receptor=uuid.uuid4()
    with pytest.raises(ValueError, match="Porcentaje inválido"):
        calcular_comisiones_por_receptor(
            {receptor: Decimal("100.00")}, porcentaje_global=tasa
        )


def test_rechaza_tasas_mezcladas() -> None:
    receptor=uuid.uuid4()
    with pytest.raises(ValueError, match="tasas por Receptor o tasa global"):
        calcular_comisiones_por_receptor(
            {receptor: Decimal("100.00")},
            porcentajes_por_receptor={receptor: Decimal("1")},
            porcentaje_global=Decimal("2"),
        )


def test_retencion_aplica_3_y_sin_retencion_3_5_por_receptor() -> None:
    agente=uuid.UUID("00000000-0000-0000-0000-000000000003")
    sin_agente=uuid.UUID("00000000-0000-0000-0000-000000000004")
    resultado=comision_por_condicion_retencion({
        agente: (Decimal("10000.00"), True),
        sin_agente: (Decimal("10000.00"), False),
    })
    assert resultado["total_produccion"] == Decimal("20000.00")
    assert resultado["comision_total"] == Decimal("650.00")
    assert [item["porcentaje"] for item in resultado["detalle"]] == ["3.00", "3.50"]
    assert [item["comision"] for item in resultado["detalle"]] == ["300.00", "350.00"]
