"""Motor de cálculo de comisiones, sin efectos contables."""

import uuid
from decimal import ROUND_HALF_UP, Decimal

CENTIMO = Decimal("0.01")


def calcular_comisiones_por_receptor(
    produccion: dict[uuid.UUID, Decimal],
    *,
    porcentajes_por_receptor: dict[uuid.UUID, Decimal] | None = None,
    porcentaje_global: Decimal | None = None,
) -> dict[str, object]:
    """Cada factura suma una vez en su Receptor, sin mezclar divisas."""
    tasas = porcentajes_por_receptor or {}
    if porcentaje_global is not None and tasas:
        raise ValueError("Indicar tasas por Receptor o tasa global")
    detalle: list[dict[str, str]] = []
    produccion_total = Decimal("0")
    comision_total = Decimal("0")
    for receptor_id, monto in sorted(produccion.items(), key=lambda item: str(item[0])):
        tasa = porcentaje_global if porcentaje_global is not None else tasas.get(receptor_id)
        if tasa is None:
            raise ValueError(f"Falta porcentaje para receptor {receptor_id}")
        if not tasa.is_finite() or not 0 <= tasa <= 100:
            raise ValueError("Porcentaje inválido")
        if not monto.is_finite() or monto < 0:
            raise ValueError("Producción inválida")
        comision = (monto * tasa / Decimal("100")).quantize(CENTIMO, rounding=ROUND_HALF_UP)
        produccion_total += monto
        comision_total += comision
        detalle.append({
            "receptor_id": str(receptor_id),
            "produccion": str(monto),
            "porcentaje": str(tasa),
            "comision": str(comision),
        })
    return {
        "total_produccion": produccion_total.quantize(CENTIMO),
        "comision_total": comision_total,
        "detalle": detalle,
    }
