from decimal import Decimal

import pytest

from app.services.saldos_responsable import resumir_saldos


def test_programacion_no_cambia_caja_y_devengo_no_equivale_a_cobro() -> None:
    resultado = resumir_saldos(
        por_cobrar_inicial=Decimal("200"),
        comisiones_gerencia=Decimal("1500"),
        cobros_confirmados=Decimal("500"),
        por_pagar_inicial=Decimal("100"),
        comisiones_usuarios=Decimal("600"),
        pagos_usuarios_confirmados=Decimal("250"),
        anticipos_usuarios_aplicados=Decimal("50"),
        caja_inicial=Decimal("1000"),
    )
    assert resultado.por_cobrar == Decimal("1200")
    assert resultado.por_pagar == Decimal("400")
    assert resultado.caja == Decimal("1250")


def test_devengo_sin_abonos_no_modifica_caja() -> None:
    resultado = resumir_saldos(
        por_cobrar_inicial=Decimal("0"),
        comisiones_gerencia=Decimal("900"),
        cobros_confirmados=Decimal("0"),
        por_pagar_inicial=Decimal("0"),
        comisiones_usuarios=Decimal("400"),
        pagos_usuarios_confirmados=Decimal("0"),
        anticipos_usuarios_aplicados=Decimal("0"),
        caja_inicial=Decimal("100"),
    )
    assert resultado.por_cobrar == Decimal("900")
    assert resultado.por_pagar == Decimal("400")
    assert resultado.caja == Decimal("100")


def test_rechaza_movimientos_negativos() -> None:
    with pytest.raises(ValueError):
        resumir_saldos(
            por_cobrar_inicial=Decimal("0"),
            comisiones_gerencia=Decimal("-1"),
            cobros_confirmados=Decimal("0"),
            por_pagar_inicial=Decimal("0"),
            comisiones_usuarios=Decimal("0"),
            pagos_usuarios_confirmados=Decimal("0"),
            anticipos_usuarios_aplicados=Decimal("0"),
            caja_inicial=Decimal("0"),
        )
