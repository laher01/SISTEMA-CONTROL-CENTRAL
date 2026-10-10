"""Cálculos separados de devengos y caja del Responsable.

Entradas: movimientos ya autorizados, de una sola moneda, sin duplicados.
No crea asientos, no modifica pagos y no efectúa conciliación.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ResumenResponsable:
    por_cobrar: Decimal
    por_pagar: Decimal
    caja: Decimal


def resumir_saldos(
    *,
    por_cobrar_inicial: Decimal,
    comisiones_gerencia: Decimal,
    cobros_confirmados: Decimal,
    por_pagar_inicial: Decimal,
    comisiones_usuarios: Decimal,
    pagos_usuarios_confirmados: Decimal,
    anticipos_usuarios_aplicados: Decimal,
    caja_inicial: Decimal,
    otros_egresos_confirmados: Decimal = Decimal("0"),
) -> ResumenResponsable:
    cantidades = (
        por_cobrar_inicial,
        comisiones_gerencia,
        cobros_confirmados,
        por_pagar_inicial,
        comisiones_usuarios,
        pagos_usuarios_confirmados,
        anticipos_usuarios_aplicados,
        caja_inicial,
        otros_egresos_confirmados,
    )
    if any(not x.is_finite() for x in cantidades):
        raise ValueError("Importes no finitos")
    if any(
        x < 0
        for x in (
            comisiones_gerencia,
            cobros_confirmados,
            comisiones_usuarios,
            pagos_usuarios_confirmados,
            anticipos_usuarios_aplicados,
            otros_egresos_confirmados,
        )
    ):
        raise ValueError("Movimientos negativos: registre reversión separada")
    return ResumenResponsable(
        por_cobrar=por_cobrar_inicial + comisiones_gerencia - cobros_confirmados,
        por_pagar=(
            por_pagar_inicial + comisiones_usuarios
            - pagos_usuarios_confirmados - anticipos_usuarios_aplicados
        ),
        caja=(
            caja_inicial
            + cobros_confirmados
            - pagos_usuarios_confirmados
            - otros_egresos_confirmados
        ),
    )
