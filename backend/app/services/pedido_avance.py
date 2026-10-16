"""Política de avance de pedidos SaaS: importes válidos, sin inventar ejecución."""

from decimal import Decimal


def calcular_avance_pedido(
    presupuesto: Decimal,
    ejecutado: Decimal,
) -> tuple[Decimal, str]:
    """Retorna porcentaje y estado; no bloquea registrar importes superiores al 120 %.

    El llamador debe suministrar exclusivamente ejecución documentada, deduplicada,
    autorizada y perteneciente al mismo Tenant y pedido.
    """
    if not presupuesto.is_finite() or not ejecutado.is_finite():
        raise ValueError("Los importes deben ser finitos")
    if presupuesto <= 0:
        raise ValueError("El presupuesto debe ser positivo")
    if ejecutado < 0:
        raise ValueError("La ejecución no puede ser negativa")

    porcentaje = (ejecutado / presupuesto) * Decimal("100")
    if porcentaje < Decimal("100"):
        estado = "VERDE"
    elif porcentaje <= Decimal("120"):
        estado = "NARANJA"
    else:
        estado = "ROJO"
    return porcentaje, estado


def calcular_avance_consolidado(
    importes: list[tuple[Decimal, Decimal]],
) -> tuple[Decimal, str]:
    """Calcula avance ponderado por importes, nunca promedio de porcentajes."""
    if not importes:
        raise ValueError("Se requiere al menos un pedido")
    total_presupuesto = Decimal("0")
    total_ejecutado = Decimal("0")
    for presupuesto, ejecutado in importes:
        if (
            not presupuesto.is_finite()
            or not ejecutado.is_finite()
            or presupuesto <= 0
            or ejecutado < 0
        ):
            raise ValueError("Importes inválidos en el consolidado")
        total_presupuesto += presupuesto
        total_ejecutado += ejecutado
    return calcular_avance_pedido(total_presupuesto, total_ejecutado)


def requiere_alerta_exceso(
    presupuesto: Decimal,
    ejecutado: Decimal,
) -> bool:
    """Alerta urgente solo por encima de 120 %, sin rechazar la operación real."""
    _, estado = calcular_avance_pedido(presupuesto, ejecutado)
    return estado == "ROJO"
