"""Motor puro de reparto de comisiones. No registra pagos ni expone ingresos superiores."""

from decimal import ROUND_HALF_UP, Decimal

CENTIMO = Decimal("0.01")


def calcular_partidas(partidas: list[dict[str, str]]) -> dict[str, object]:
    """Calcula comisiones individuales sin realizar transferencias.

    Cada destinatario lleva base documentada y porcentaje propio.
    """
    if not partidas or len(partidas) > 100:
        raise ValueError("Debe indicar entre uno y cien destinatarios")
    calculadas: list[dict[str, str]] = []
    acumulado = Decimal("0.00")
    for partida in partidas:
        base = Decimal(partida["base"])
        porcentaje = Decimal(partida["porcentaje"])
        if not base.is_finite() or not porcentaje.is_finite():
            raise ValueError("Base y porcentaje deben ser finitos")
        if base < 0 or porcentaje < 0 or porcentaje > 100:
            raise ValueError("Base y porcentaje deben estar entre los límites permitidos")
        importe = (base * porcentaje / Decimal("100")).quantize(
            CENTIMO, rounding=ROUND_HALF_UP
        )
        acumulado += importe
        calculadas.append(
            {
                "beneficiario": partida["beneficiario"],
                "tipo": partida["tipo"],
                "base": str(base),
                "porcentaje": str(porcentaje),
                "importe": str(importe),
            }
        )
    return {"partidas": calculadas, "total": str(acumulado)}
