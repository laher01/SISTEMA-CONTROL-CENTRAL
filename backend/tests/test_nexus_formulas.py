"""Pruebas de seguridad y cálculo del núcleo declarativo NEXUS."""

from decimal import Decimal

import pytest

from app.services.nexus_formulas import (
    calcular_pago_estandar,
    validar_destinatario_especial,
    validar_propuesta_nexus,
)


def test_pago_estandar_dos_tasas() -> None:
    resultado = calcular_pago_estandar(
        produccion_sin_retencion=Decimal("60000"),
        porcentaje_sin_retencion=Decimal("1.5"),
        produccion_con_retencion=Decimal("40000"),
        porcentaje_con_retencion=Decimal("1"),
    )
    assert resultado.sin_retencion == Decimal("900.00")
    assert resultado.con_retencion == Decimal("400.00")
    assert resultado.total == Decimal("1300.00")


@pytest.mark.parametrize("tasa", ["-1", "101", "NaN", "Infinity"])
def test_rechaza_tasas_invalidas(tasa: str) -> None:
    with pytest.raises(ValueError):
        calcular_pago_estandar(
            produccion_sin_retencion=Decimal("100"),
            porcentaje_sin_retencion=Decimal(tasa),
            produccion_con_retencion=Decimal("0"),
            porcentaje_con_retencion=Decimal("1"),
        )


def test_especial_solo_jona01() -> None:
    validar_destinatario_especial(codigo_usuario="JONA01")
    with pytest.raises(ValueError):
        validar_destinatario_especial(codigo_usuario="JAVIER01")


def test_nexus_no_ejecuta_codigo_arbitrario() -> None:
    with pytest.raises(ValueError):
        validar_propuesta_nexus(
            expresion="__import__('os').system('id')",
            variables=set(),
            variables_permitidas=set(),
        )
