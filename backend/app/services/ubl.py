"""Extracción de datos desde comprobantes electrónicos SUNAT en formato UBL 2.1."""

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from xml.etree.ElementTree import Element, ParseError

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import fromstring

from app.enums import TipoDocumento

NS = {
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}
INVOICE = "{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}Invoice"
DESPATCH = "{urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2}DespatchAdvice"

TIPO_FACTURA = "01"
TIPOS_GUIA = {"09": TipoDocumento.GRR, "31": TipoDocumento.GRT}

RUC_RE = re.compile(r"^\d{11}$")
NUMERO_RE = re.compile(r"^([A-Z0-9]{4})-(\d{1,8})$")


class UblInvalido(ValueError):
    pass


@dataclass(frozen=True)
class Parte:
    ruc: str
    razon_social: str


@dataclass(frozen=True)
class Referencia:
    serie: str
    correlativo: str
    emisor_ruc: str | None


@dataclass(frozen=True)
class ComprobanteUbl:
    tipo_documento: TipoDocumento
    serie: str
    correlativo: str
    fecha_emision: date
    emisor: Parte
    receptor: Parte
    moneda: str | None = None
    importe_total: Decimal | None = None
    referencia: Referencia | None = None

    def a_dict(self) -> dict[str, object]:
        datos: dict[str, object] = {
            "tipo_documento": self.tipo_documento.value,
            "serie": self.serie,
            "correlativo": self.correlativo,
            "fecha_emision": self.fecha_emision.isoformat(),
            "emisor": {"ruc": self.emisor.ruc, "razon_social": self.emisor.razon_social},
            "receptor": {"ruc": self.receptor.ruc, "razon_social": self.receptor.razon_social},
        }
        if self.moneda is not None:
            datos["moneda"] = self.moneda
        if self.importe_total is not None:
            datos["importe_total"] = str(self.importe_total)
        if self.referencia is not None:
            datos["referencia"] = {
                "serie": self.referencia.serie,
                "correlativo": self.referencia.correlativo,
                "emisor_ruc": self.referencia.emisor_ruc,
            }
        return datos


def parece_xml(nombre: str, contenido: bytes) -> bool:
    return nombre.lower().endswith(".xml") or contenido.lstrip(b"\xef\xbb\xbf \t\r\n")[:1] == b"<"


def parse_ubl(contenido: bytes) -> ComprobanteUbl | None:
    """Devuelve el comprobante si es una Factura o Guía UBL reconocida; None en otro caso."""
    try:
        raiz: Element = fromstring(contenido)
    except DefusedXmlException as exc:
        raise UblInvalido("XML con construcciones no permitidas") from exc
    except ParseError:
        return None

    if raiz.tag == INVOICE:
        if _texto(raiz, "cbc:InvoiceTypeCode") != TIPO_FACTURA:
            return None
        return _factura(raiz)
    if raiz.tag == DESPATCH:
        tipo = TIPOS_GUIA.get(_texto(raiz, "cbc:DespatchAdviceTypeCode") or "")
        if tipo is None:
            return None
        return _guia(raiz, tipo)
    return None


def _factura(raiz: Element) -> ComprobanteUbl:
    serie, correlativo = _numero(_requerido(raiz, "cbc:ID"))
    importe = _requerido(raiz, "cac:LegalMonetaryTotal/cbc:PayableAmount")
    try:
        importe_total = Decimal(importe).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise UblInvalido(f"Importe inválido: {importe}") from exc
    return ComprobanteUbl(
        tipo_documento=TipoDocumento.FACT,
        serie=serie,
        correlativo=correlativo,
        fecha_emision=_fecha(_requerido(raiz, "cbc:IssueDate")),
        emisor=_parte(raiz, "cac:AccountingSupplierParty/cac:Party"),
        receptor=_parte(raiz, "cac:AccountingCustomerParty/cac:Party"),
        moneda=_requerido(raiz, "cbc:DocumentCurrencyCode"),
        importe_total=importe_total,
    )


def _guia(raiz: Element, tipo: TipoDocumento) -> ComprobanteUbl:
    serie, correlativo = _numero(_requerido(raiz, "cbc:ID"))
    return ComprobanteUbl(
        tipo_documento=tipo,
        serie=serie,
        correlativo=correlativo,
        fecha_emision=_fecha(_requerido(raiz, "cbc:IssueDate")),
        emisor=_parte(raiz, "cac:DespatchSupplierParty/cac:Party"),
        receptor=_parte(raiz, "cac:DeliveryCustomerParty/cac:Party"),
        referencia=_referencia_factura(raiz),
    )


def _referencia_factura(raiz: Element) -> Referencia | None:
    for ref in raiz.findall("cac:AdditionalDocumentReference", NS):
        if _texto(ref, "cbc:DocumentTypeCode") != TIPO_FACTURA:
            continue
        numero = _texto(ref, "cbc:ID")
        if numero is None or not NUMERO_RE.match(numero):
            continue
        serie, correlativo = _numero(numero)
        emisor_ruc = _texto(ref, "cac:IssuerParty/cac:PartyIdentification/cbc:ID")
        if emisor_ruc is not None and not RUC_RE.match(emisor_ruc):
            emisor_ruc = None
        return Referencia(serie=serie, correlativo=correlativo, emisor_ruc=emisor_ruc)
    return None


def _parte(raiz: Element, ruta: str) -> Parte:
    ruc = _requerido(raiz, f"{ruta}/cac:PartyIdentification/cbc:ID")
    if not RUC_RE.match(ruc):
        raise UblInvalido(f"RUC inválido: {ruc}")
    razon = _texto(raiz, f"{ruta}/cac:PartyLegalEntity/cbc:RegistrationName") or ruc
    return Parte(ruc=ruc, razon_social=razon)


def _numero(valor: str) -> tuple[str, str]:
    coincidencia = NUMERO_RE.match(valor)
    if coincidencia is None:
        raise UblInvalido(f"Serie-correlativo inválido: {valor}")
    return coincidencia.group(1), str(int(coincidencia.group(2)))


def _fecha(valor: str) -> date:
    try:
        return date.fromisoformat(valor)
    except ValueError as exc:
        raise UblInvalido(f"Fecha inválida: {valor}") from exc


def _texto(raiz: Element, ruta: str) -> str | None:
    nodo = raiz.find(ruta, NS)
    if nodo is None or nodo.text is None:
        return None
    return nodo.text.strip() or None


def _requerido(raiz: Element, ruta: str) -> str:
    valor = _texto(raiz, ruta)
    if valor is None:
        raise UblInvalido(f"Falta el campo {ruta}")
    return valor
