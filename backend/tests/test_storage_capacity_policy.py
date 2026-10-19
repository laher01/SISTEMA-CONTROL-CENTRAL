"""Contrato del almacenamiento VPS secuencial, sin acceso a VPS reales."""

from decimal import Decimal

import pytest

from app.services.storage_capacity_policy import (
    NodoDocumental,
    evaluar_capacidad,
    validar_siguiente_almacen,
    validar_unico_almacen_activo,
)


def nodo(
    codigo: str, usado: int = 0, verificado: bool = True, activo: bool = False
) -> NodoDocumental:
    return NodoDocumental(codigo, 1000, usado, verificado, activo)


@pytest.mark.parametrize(
    ("ocupado", "alerta"),
    [(0, False), (599, False), (600, True), (750, True), (1000, True)],
)
def test_alerta_ocupacion_60_por_ciento(ocupado: int, alerta: bool) -> None:
    porcentaje, preparar = evaluar_capacidad(nodo("uno", usado=ocupado))
    assert porcentaje == Decimal(ocupado) / Decimal(1000)
    assert preparar is alerta


@pytest.mark.parametrize(
    ("total", "usado"),
    [(0, 0), (-1, 0), (100, -1), (100, 101)],
)
def test_rechaza_capacidad_invalida(total: int, usado: int) -> None:
    with pytest.raises(ValueError):
        evaluar_capacidad(NodoDocumental("uno", total, usado, True, True))


def test_solo_un_destino_de_escritura_global() -> None:
    primero = nodo("uno", activo=True)
    segundo = nodo("dos", verificado=True)
    assert validar_unico_almacen_activo([primero, segundo]) == primero
    with pytest.raises(ValueError):
        validar_unico_almacen_activo([primero, nodo("dos", activo=True)])
    with pytest.raises(ValueError):
        validar_unico_almacen_activo([nodo("uno"), segundo])


def test_almacen_activo_debe_estar_verificado() -> None:
    with pytest.raises(ValueError, match="verificado"):
        validar_unico_almacen_activo([nodo("uno", verificado=False, activo=True)])


def test_conmutacion_preparada_no_autoriza_nodo_sin_validar() -> None:
    actual = nodo("uno", usado=650, activo=True)
    siguiente = nodo("dos", verificado=False)
    with pytest.raises(ValueError, match="verificado"):
        validar_siguiente_almacen([actual, siguiente], "dos")


def test_conmutacion_requiere_nodo_distinto_y_espacio_libre() -> None:
    actual = nodo("uno", usado=650, activo=True)
    siguiente = nodo("dos", usado=1000)
    with pytest.raises(ValueError, match="distinto"):
        validar_siguiente_almacen([actual, siguiente], "uno")
    with pytest.raises(ValueError, match="espacio libre"):
        validar_siguiente_almacen([actual, siguiente], "dos")


def test_conmutacion_validada_separa_nodo_anterior_y_siguiente() -> None:
    actual = nodo("uno", usado=650, activo=True)
    siguiente = nodo("dos", usado=10)
    assert validar_siguiente_almacen([actual, siguiente], "dos") == (actual, siguiente)
    assert actual.activo_escritura is True
    assert siguiente.activo_escritura is False
