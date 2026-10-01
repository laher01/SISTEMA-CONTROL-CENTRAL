from datetime import date
from decimal import Decimal

import pytest

from app.enums import TipoDocumento
from app.services.ubl import UblInvalido, parece_xml, parse_ubl
from tests.xml import EMISOR, RECEPTOR, factura, guia


def test_parse_factura() -> None:
    comprobante = parse_ubl(factura())
    assert comprobante is not None
    assert comprobante.tipo_documento == TipoDocumento.FACT
    assert (comprobante.serie, comprobante.correlativo) == ("F001", "123")
    assert comprobante.fecha_emision == date(2026, 9, 10)
    assert comprobante.emisor.ruc == EMISOR
    assert comprobante.emisor.razon_social == "PROVEEDOR SAC"
    assert comprobante.receptor.ruc == RECEPTOR
    assert comprobante.moneda == "PEN"
    assert comprobante.importe_total == Decimal("2500.00")


def test_parse_guia_con_referencia() -> None:
    comprobante = parse_ubl(guia())
    assert comprobante is not None
    assert comprobante.tipo_documento == TipoDocumento.GRR
    assert comprobante.referencia is not None
    assert (comprobante.referencia.serie, comprobante.referencia.correlativo) == ("F001", "123")


def test_xml_no_ubl_devuelve_none() -> None:
    assert parse_ubl(b"<root><a>1</a></root>") is None
    assert parse_ubl(b"no es xml") is None


def test_rechaza_entidades_externas() -> None:
    xxe = b"""<?xml version="1.0"?>
<!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]><r>&x;</r>"""
    with pytest.raises(UblInvalido):
        parse_ubl(xxe)


def test_rechaza_ruc_invalido() -> None:
    with pytest.raises(UblInvalido):
        parse_ubl(factura(emisor="123"))


def test_parece_xml() -> None:
    assert parece_xml("f.XML", b"")
    assert parece_xml("sin_ext", b"\xef\xbb\xbf  <x/>")
    assert not parece_xml("f.pdf", b"%PDF-1.7")
