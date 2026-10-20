"""Reglas puras de capacidad; no cambia rutas ni mueve archivos reales.

Los nodos deben validarse con pruebas de lectura/escritura y restauración ANTES
de que el orquestador habilite su uso como almacén activo.
"""

from dataclasses import dataclass
from decimal import Decimal

UMBRAL_PREPARACION = Decimal("0.60")


@dataclass(frozen=True)
class NodoDocumental:
    codigo: str
    total_bytes: int
    usado_bytes: int
    verificado: bool
    activo_escritura: bool


def evaluar_capacidad(nodo: NodoDocumental) -> tuple[Decimal, bool]:
    """Devuelve ocupación y alerta para preparar el siguiente nodo.

    60% genera alerta, no autoriza migración ni borrado automático.
    """
    if nodo.total_bytes <= 0 or not 0 <= nodo.usado_bytes <= nodo.total_bytes:
        raise ValueError("Medición de almacenamiento inválida")
    ocupacion = Decimal(nodo.usado_bytes) / Decimal(nodo.total_bytes)
    return ocupacion, ocupacion >= UMBRAL_PREPARACION


def validar_unico_almacen_activo(nodos: list[NodoDocumental]) -> NodoDocumental:
    """No distribuye simultáneamente nuevas escrituras entre varias VPS."""
    activos = [nodo for nodo in nodos if nodo.activo_escritura]
    if len(activos) != 1:
        raise ValueError("Debe existir exactamente un almacén activo de escritura")
    if not activos[0].verificado:
        raise ValueError("El almacén activo no ha sido verificado")
    evaluar_capacidad(activos[0])
    return activos[0]


def validar_siguiente_almacen(
    nodos: list[NodoDocumental], siguiente_codigo: str
) -> tuple[NodoDocumental, NodoDocumental]:
    """Preflight de conmutación, sin ejecutar la conmutación.

    El cambio real debe protegerse con una transacción y auditoría.
    """
    actual = validar_unico_almacen_activo(nodos)
    candidatos = [nodo for nodo in nodos if nodo.codigo == siguiente_codigo]
    if len(candidatos) != 1:
        raise ValueError("El nodo siguiente no existe o no es único")
    siguiente = candidatos[0]
    if siguiente.codigo == actual.codigo:
        raise ValueError("El siguiente almacén debe ser distinto")
    if not siguiente.verificado:
        raise ValueError("El siguiente almacén no está verificado")
    evaluar_capacidad(siguiente)
    if siguiente.usado_bytes >= siguiente.total_bytes:
        raise ValueError("El siguiente almacén no tiene espacio libre")
    return actual, siguiente
