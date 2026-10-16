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
