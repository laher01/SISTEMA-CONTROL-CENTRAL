"""Cálculo puro de producción con/sin agente de retención.

Las tasas son honorarios pactados con el Usuario: NO son la tasa tributaria
de retención de SUNAT. No se mezclan monedas ni se modifica el expediente.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENTIMO = Decimal("0.01")


@dataclass(frozen=True)
class FacturaProduccion:
    importe: Decimal
    agente_retencion: bool


def liquidar_dos_tasas(
    facturas: list[FacturaProduccion],
    *,
    porcentaje_sin_agente: Decimal,
    porcentaje_con_agente: Decimal,
    adelantos: Decimal = Decimal("0"),
) -> dict[str, Decimal]:
    """Agrupa importes y calcula honorarios sobre cada grupo de facturas."""
    for tasa in (porcentaje_sin_agente, porcentaje_con_agente):
        if not tasa.is_finite() or not Decimal("0") <= tasa <= Decimal("100"):
            raise ValueError("Porcentaje contractual inválido")
    if not adelantos.is_finite() or adelantos < 0:
        raise ValueError("Adelantos inválidos")
    sin_agente = Decimal("0")
    con_agente = Decimal("0")
    for factura in facturas:
        if not factura.importe.is_finite() or factura.importe < 0:
            raise ValueError("Importe de factura inválido")
        if factura.agente_retencion:
            con_agente += factura.importe
        else:
            sin_agente += factura.importe
    bruto_sin_agente = (sin_agente * porcentaje_sin_agente / Decimal("100")).quantize(
        CENTIMO, rounding=ROUND_HALF_UP
    )
    bruto_con_agente = (con_agente * porcentaje_con_agente / Decimal("100")).quantize(
        CENTIMO, rounding=ROUND_HALF_UP
    )
    bruto = bruto_sin_agente + bruto_con_agente
    return {
        "produccion_sin_agente": sin_agente.quantize(CENTIMO),
        "produccion_con_agente": con_agente.quantize(CENTIMO),
        "bruto_sin_agente": bruto_sin_agente,
        "bruto_con_agente": bruto_con_agente,
        "bruto": bruto,
        "adelantos": adelantos.quantize(CENTIMO),
        "neto": (bruto - adelantos).quantize(CENTIMO),
    }
