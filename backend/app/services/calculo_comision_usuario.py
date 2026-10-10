"""Cálculo decimal puro de comisiones documentadas.

Esta función no determina la condición tributaria ni valida expedientes:
el llamador debe aportar líneas YA clasificadas y con tasas históricas.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENTIMO = Decimal("0.01")


@dataclass(frozen=True)
class LineaComision:
    documento_id: str
    monto: Decimal
    tasa: Decimal
    clasificacion: str


def calcular_comision_documentada(lineas: list[LineaComision]) -> dict[str, Decimal]:
    vistos: set[str] = set()
    produccion_sin = Decimal("0")
    produccion_con = Decimal("0")
    comision_sin = Decimal("0")
    comision_con = Decimal("0")
    for linea in lineas:
        if linea.documento_id in vistos:
            raise ValueError("Documento duplicado en liquidación")
        vistos.add(linea.documento_id)
        if linea.clasificacion not in ("SIN_AGENTE", "CON_AGENTE"):
            raise ValueError("Clasificación tributaria sin verificar")
        if (
            not linea.monto.is_finite()
            or not linea.tasa.is_finite()
            or linea.monto < 0
            or not Decimal("0") <= linea.tasa <= Decimal("100")
        ):
            raise ValueError("Importe o tarifa inválido")
        importe = (linea.monto * linea.tasa / Decimal("100")).quantize(
            CENTIMO, rounding=ROUND_HALF_UP
        )
        if linea.clasificacion == "SIN_AGENTE":
            produccion_sin += linea.monto
            comision_sin += importe
        else:
            produccion_con += linea.monto
            comision_con += importe
    return {
        "produccion_sin": produccion_sin,
        "produccion_con": produccion_con,
        "comision_sin": comision_sin,
        "comision_con": comision_con,
        "comision_total": comision_sin + comision_con,
    }
