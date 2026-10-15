"""Extracción UBL de ítems y persistencia idempotente en catálogos por tenant."""

import hashlib
import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from xml.etree.ElementTree import Element, ParseError

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import fromstring
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.item_models import LineaComprobanteItem, ProductoItem
from app.services.contabilidad_items_rules import sugerir_categoria, texto_normalizado
from app.services.ubl import INVOICE, NS


@dataclass(frozen=True)
class ItemUBL:
    numero: int
    descripcion: str
    cantidad: Decimal
    unidad: str
    importe: Decimal | None


def extraer_items_ubl(contenido: bytes) -> list[ItemUBL]:
    """Lee líneas de factura UBL sin inferencias OCR ni equivalencias de unidades."""
    try:
        raiz: Element = fromstring(contenido)
    except (ParseError, DefusedXmlException):
        return []
    if raiz.tag != INVOICE:
        return []
    salida: list[ItemUBL] = []
    for n, linea in enumerate(raiz.findall("cac:InvoiceLine", NS), start=1):
        nodo_cantidad = linea.find("cbc:InvoicedQuantity", NS)
        nodo_importe = linea.find("cbc:LineExtensionAmount", NS)
        nombre = (
            linea.findtext("cac:Item/cbc:Description", default="", namespaces=NS)
            or linea.findtext("cac:Item/cbc:Name", default="", namespaces=NS)
        ).strip()
        if not nombre or nodo_cantidad is None or not nodo_cantidad.text:
            continue
        try:
            cantidad = Decimal(nodo_cantidad.text.strip())
            importe = (
                Decimal(nodo_importe.text.strip())
                if nodo_importe is not None and nodo_importe.text
                else None
            )
        except InvalidOperation:
            continue
        if not cantidad.is_finite() or cantidad <= 0:
            continue
        if importe is not None and not importe.is_finite():
            continue
        unidad = (nodo_cantidad.get("unitCode") or "NIU").strip().upper()
        salida.append(
            ItemUBL(
                numero=n,
                descripcion=nombre[:1000],
                cantidad=cantidad,
                unidad=unidad[:40],
                importe=importe,
            )
        )
    return salida


def registrar_items_ubl(
    session: Session,
    tenant_id: uuid.UUID,
    documento_id: uuid.UUID,
    contenido: bytes,
) -> int:
    """No duplica líneas al reprocesar; no mezcla productos con variantes diferentes."""
    items = extraer_items_ubl(contenido)
    registrados = 0
    for linea in items:
        ya_registrada = session.scalar(
            select(LineaComprobanteItem.id).where(
                LineaComprobanteItem.tenant_id == tenant_id,
                LineaComprobanteItem.documento_id == documento_id,
                LineaComprobanteItem.numero_linea == linea.numero,
            )
        )
        if ya_registrada is not None:
            continue
        clave = hashlib.sha256(
            f"{texto_normalizado(linea.descripcion)}|{linea.unidad}".encode()
        ).hexdigest()
        producto = session.scalar(
            select(ProductoItem).where(
                ProductoItem.tenant_id == tenant_id,
                ProductoItem.clave_catalogo == clave,
            )
        )
        if producto is None:
            producto = ProductoItem(
                tenant_id=tenant_id,
                clave_catalogo=clave,
                descripcion=linea.descripcion[:500],
                categoria=sugerir_categoria(linea.descripcion),
                clasificacion_confirmada=False,
                activo=True,
            )
            session.add(producto)
            session.flush()
        session.add(
            LineaComprobanteItem(
                tenant_id=tenant_id,
                documento_id=documento_id,
                producto_id=producto.id,
                numero_linea=linea.numero,
                descripcion_original=linea.descripcion,
                cantidad=linea.cantidad,
                unidad=linea.unidad,
                importe_linea=linea.importe,
            )
        )
        registrados += 1
    return registrados
