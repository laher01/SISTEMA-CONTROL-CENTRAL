from dataclasses import replace

import pytest

from app.services.lotes_imagenes import (
    DecisionFiscal,
    IdentidadFactura,
    decidir_factura,
    dividir_sublotes,
)


@pytest.mark.parametrize(
    "cantidad,grupos",
    [(0, []), (1, [1]), (10, [10]), (11, [10, 1]), (25, [10, 10, 5])],
)
def test_planificar_sublotes(cantidad: int, grupos: list[int]) -> None:
    elementos = list(range(cantidad))
    sublotes = dividir_sublotes(elementos)
    assert [len(x) for x in sublotes] == grupos
    assert [e for grupo in sublotes for e in grupo] == elementos


@pytest.mark.parametrize("limite", [0, -1, 11])
def test_limite_no_valido(limite: int) -> None:
    with pytest.raises(ValueError):
        dividir_sublotes([1], limite)


@pytest.fixture
def factura() -> IdentidadFactura:
    return IdentidadFactura(
        tenant_id="empresa-a",
        ruc_emisor="20123456789",
        tipo="01",
        serie="F001",
        correlativo="123",
        ruc_receptor="20987654321",
        importe="118.00",
        fecha_emision="2026-10-15",
    )


def test_factura_nueva(factura: IdentidadFactura) -> None:
    assert decidir_factura(factura, None, confianza_suficiente=True) == DecisionFiscal.CREAR


def test_factura_duplicada(factura: IdentidadFactura) -> None:
    assert (
        decidir_factura(factura, factura, confianza_suficiente=True)
        == DecisionFiscal.RECHAZAR_DUPLICADO
    )


@pytest.mark.parametrize(
    "campo,valor",
    [("ruc_receptor", "20111111111"), ("importe", "120.00"), ("fecha_emision", "2026-10-14")],
)
def test_conflictos(factura: IdentidadFactura, campo: str, valor: str) -> None:
    assert (
        decidir_factura(replace(factura, **{campo: valor}), factura, confianza_suficiente=True)
        == DecisionFiscal.REVISAR_CONFLICTO
    )


def test_confianza_insuficiente(factura: IdentidadFactura) -> None:
    assert (
        decidir_factura(factura, None, confianza_suficiente=False)
        == DecisionFiscal.REVISION_REQUERIDA
    )


def test_faltan_datos(factura: IdentidadFactura) -> None:
    assert (
        decidir_factura(replace(factura, ruc_emisor=""), None, confianza_suficiente=True)
        == DecisionFiscal.REVISION_REQUERIDA
    )


def test_tenant_distinto_no_se_trata_como_duplicado(factura: IdentidadFactura) -> None:
    assert (
        decidir_factura(replace(factura, tenant_id="empresa-b"), factura, confianza_suficiente=True)
        == DecisionFiscal.REVISION_REQUERIDA
    )
