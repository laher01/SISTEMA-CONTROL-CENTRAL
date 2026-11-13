"""Extracción UBL de ítems y persistencia idempotente en catálogos por tenant."""

import hashlib
import re
import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from xml.etree.ElementTree import Element, ParseError

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import fromstring
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.item_models import LineaComprobanteItem, ProductoItem
from app.models import Documento, Tenant
from app.services.contabilidad_items_rules import sugerir_categoria, texto_normalizado
from app.services.extraccion_campos import detectar_formato_documental
from app.services.ubl import INVOICE, NS


@dataclass(frozen=True)
class ItemUBL:
    numero: int
    descripcion: str
    cantidad: Decimal
    unidad: str
    importe: Decimal | None
    precio: Decimal | None = None


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
        valor_unitario = linea.findtext("cac:Price/cbc:PriceAmount", namespaces=NS)
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
        try:
            precio = Decimal(valor_unitario) if valor_unitario else None
        except InvalidOperation:
            precio = None
        if precio is not None and (not precio.is_finite() or not 0 <= precio < 10**14):
            precio = None
        unidad = (nodo_cantidad.get("unitCode") or "NIU").strip().upper()
        salida.append(
            ItemUBL(
                numero=n,
                descripcion=nombre[:2000],
                cantidad=cantidad,
                unidad=unidad[:40],
                importe=importe,
                precio=precio,
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
    return _registrar_lineas(session, tenant_id, documento_id, extraer_items_ubl(contenido))


def _registrar_lineas(
    session: Session, tenant_id: uuid.UUID, documento_id: uuid.UUID, items: list[ItemUBL]
) -> int:
    # Serializa escrituras por tenant y bloquea ingestión de documentos ajenos o retirados.
    tenant_valido = session.scalar(
        select(Tenant.id).where(Tenant.id == tenant_id).with_for_update()
    )
    if tenant_valido is None:
        raise ValueError("Tenant no encontrado")
    documento_valido = session.scalar(
        select(Documento.id).where(
            Documento.id == documento_id,
            Documento.tenant_id == tenant_id,
            Documento.deleted_at.is_(None),
        )
    )
    if documento_valido is None:
        raise ValueError("Documento no encontrado en el tenant autorizado")
    registrados = 0
    for linea in items:
        precio = linea.precio if linea.precio is not None and 0 <= linea.precio < 10**14 else None
        ya_registrada = session.scalar(
            select(LineaComprobanteItem).where(
                LineaComprobanteItem.tenant_id == tenant_id,
                LineaComprobanteItem.documento_id == documento_id,
                LineaComprobanteItem.numero_linea == linea.numero,
            )
        )
        if ya_registrada is not None:
            if (
                ya_registrada.precio_unitario is None
                and ya_registrada.descripcion_original == linea.descripcion
                and ya_registrada.unidad == linea.unidad
                and ya_registrada.cantidad == linea.cantidad
            ):
                ya_registrada.precio_unitario = precio
            continue
        nombre = texto_normalizado(linea.descripcion)
        # SUNAT puede imprimir «500ML» o «500 ML» para la misma presentación.
        medida = r"(?<=\d) *(ml|cl|l|kg|g|mg)\b"
        variantes = (re.sub(medida, r" \1", nombre), re.sub(medida, r"\1", nombre))
        claves = [
            hashlib.sha256(f"{variante}|{linea.unidad}".encode()).hexdigest()
            for variante in dict.fromkeys((nombre, *variantes))
        ]
        producto = session.scalar(
            select(ProductoItem)
            .where(
                ProductoItem.tenant_id == tenant_id,
                ProductoItem.clave_catalogo.in_(claves),
            )
            .order_by((ProductoItem.clave_catalogo == claves[0]).desc(), ProductoItem.id)
            .limit(1)
        )
        clave = claves[0]
        if producto is None:
            producto = ProductoItem(
                tenant_id=tenant_id,
                clave_catalogo=clave,
                descripcion=linea.descripcion[:2000],
                unidad_base=linea.unidad,
                categoria=sugerir_categoria(linea.descripcion),
                clasificacion_confirmada=False,
                activo=True,
            )
            session.add(producto)
            session.flush()
        producto_id = producto.combinado_en_id or producto.id
        session.add(
            LineaComprobanteItem(
                tenant_id=tenant_id,
                documento_id=documento_id,
                producto_id=producto_id,
                numero_linea=linea.numero,
                descripcion_original=linea.descripcion,
                cantidad=linea.cantidad,
                unidad=linea.unidad,
                importe_linea=linea.importe,
                precio_unitario=precio,
            )
        )
        registrados += 1
    return registrados


def registrar_items_pdf_estacion(
    session: Session, tenant_id: uuid.UUID, documento_id: uuid.UUID, texto: str
) -> int:
    """Registra líneas verificables de tablas de facturas PDF.

    No infiere importes, no sustituye UBL y evita duplicados ante reprocesamientos.
    """
    items_tabla = extraer_items_pdf_tabla(texto)
    if items_tabla:
        return _registrar_lineas(session, tenant_id, documento_id, items_tabla)
    if detectar_formato_documental(texto) == "MASYDASE_FACTURA":
        items = extraer_items_pdf_masydase(texto)
        return _registrar_lineas(session, tenant_id, documento_id, items) if items else 0
    cabecera = re.search(
        r"CANTIDAD\s+C[ÓO]DIGO\s+U\.?M\.?\s+DESCRIPCI[ÓO]N\s+"
        r"VALOR\s+UNITARIO\s+PRECIO\s+UNITARIO\s+IMPORTE",
        texto,
        re.I,
    )
    if not cabecera or not re.search(r"\bFACTURA\b", texto[: cabecera.start()], re.I):
        return 0
    patron = re.compile(
        rf"(?P<cantidad>{_NUMERO_TABLA})\s+\S+\s+"
        rf"(?P<unidad>[A-Z][A-Z0-9./-]{{0,39}})\s+(?P<descripcion>.+?)\s+"
        rf"(?P<precio>{_NUMERO_TABLA})\s+{_NUMERO_TABLA}\s+(?P<importe>{_NUMERO_TABLA})",
        re.I,
    )
    tabla = _FIN_TABLA.split(texto[cabecera.end() :], maxsplit=1)[0]
    if re.search(r"\bFACTURA\s+ELECTR[ÓO]NICA\b", tabla, re.I):
        return 0
    items = []
    for numero, fila in enumerate(tabla.strip().splitlines(), 1):
        campos = patron.fullmatch(" ".join(fila.split()))
        if campos is None:
            continue
        cantidad = Decimal(campos["cantidad"].replace(",", ""))
        importe = Decimal(campos["importe"].replace(",", ""))
        if 0 < cantidad < Decimal("100000000000000") and importe < Decimal("10000000000000000"):
            items.append(
                ItemUBL(
                    numero,
                    campos["descripcion"][:2000],
                    cantidad,
                    campos["unidad"].upper(),
                    importe,
                    Decimal(campos["precio"].replace(",", "")),
                )
            )
    return _registrar_lineas(session, tenant_id, documento_id, items) if items else 0


_NUMERO_TABLA = r"(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?"
_CABECERA_TABLA = re.compile(
    r"\bCantidad\s+Unidad(?:\s+de)?\s+Medida\s+Descripci[óo]n\s+"
    r"Valor\s+Unitario(?P<icbper>\s+ICBPER)?\s*(?:\n|$)",
    re.I,
)
_FIN_TABLA = re.compile(
    r"(?im)^\s*(?:Valor de Venta de Operaciones|Sub\s*Total Ventas|"
    r"Importe Total|Total a Pagar|SON:|Observaci[óo]n\s*:|Esta es una representaci[óo]n)"
)
_INICIO_FILA = re.compile(
    rf"(?m)^\s*(?P<cantidad>{_NUMERO_TABLA})[ \t]+(?P<unidad>[A-Z][A-Z0-9./-]{{0,39}})[ \t]+",
    re.I,
)


def extraer_items_pdf_tabla(texto: str) -> list[ItemUBL]:
    """Lee las filas de una tabla de factura con valor unitario e ICBPER opcional."""
    if not re.search(r"\bFACTURA\b", texto, re.I):
        return []
    cabeceras = list(_CABECERA_TABLA.finditer(texto))
    items: list[ItemUBL] = []
    numero_linea = 0
    for indice, cabecera in enumerate(cabeceras):
        fin = cabeceras[indice + 1].start() if indice + 1 < len(cabeceras) else len(texto)
        tabla = _FIN_TABLA.split(texto[cabecera.end() : fin], maxsplit=1)[0]
        filas = list(_INICIO_FILA.finditer(tabla))
        precio_final = (
            rf"\s+(?P<precio>{_NUMERO_TABLA})\s+{_NUMERO_TABLA}"
            if cabecera.group("icbper")
            else rf"\s+(?P<precio>{_NUMERO_TABLA})"
        )
        for posicion, fila in enumerate(filas):
            numero_linea += 1
            fin_fila = filas[posicion + 1].start() if posicion + 1 < len(filas) else len(tabla)
            cuerpo = " ".join(tabla[fila.end() : fin_fila].split())
            campos = re.fullmatch(rf"(.+?){precio_final}", cuerpo)
            cantidad = Decimal(fila.group("cantidad").replace(",", ""))
            if campos and 0 < cantidad < Decimal("100000000000000"):
                items.append(
                    ItemUBL(
                        numero_linea,
                        campos.group(1)[:2000],
                        cantidad,
                        fila.group("unidad").upper(),
                        None,
                        Decimal(campos["precio"].replace(",", "")),
                    )
                )
    return items


def extraer_items_pdf_masydase(texto: str) -> list[ItemUBL]:
    tabla = re.search(
        r"^CANT\. UNIDAD DESCRIPCI[ÓO]N MODELO LOTE SERIE P\.UNIT DTO\. TOTAL\s*\n"
        r"([\s\S]+?)^(?:OP\. |IGV:|TOTAL A PAGAR:)",
        texto,
        re.I | re.M,
    )
    total = re.search(r"^TOTAL A PAGAR:\s*S/\s*([\d,]+\.\d{2})", texto, re.I | re.M)
    if not tabla or not total:
        return []
    filas = re.split(r"(?m)(?=^\d+(?:\.\d+)?\s+[A-Z]{2,4}\s+)", tabla.group(1).strip())
    items: list[ItemUBL] = []
    suma = Decimal(0)
    for fila in filter(str.strip, filas):
        campos = re.fullmatch(
            r"(\d+(?:\.\d+)?) ([A-Z]{2,4}) (.+?) "
            r"(\d[\d,]*\.\d+) 0(?:\.0+)? (\d[\d,]*\.\d{2})",
            " ".join(fila.split()),
        )
        if not campos:
            return []
        cantidad, unidad, descripcion, precio, importe = campos.groups()
        cantidad_decimal = Decimal(cantidad)
        importe_decimal = Decimal(importe.replace(",", ""))
        if cantidad_decimal <= 0 or abs(
            cantidad_decimal * Decimal(precio.replace(",", "")) - importe_decimal
        ) > Decimal("0.01"):
            return []
        items.append(
            ItemUBL(
                len(items) + 1,
                descripcion,
                cantidad_decimal,
                unidad,
                importe_decimal,
                Decimal(precio.replace(",", "")),
            )
        )
        suma += importe_decimal
    if suma != Decimal(total.group(1).replace(",", "")):
        return []
    return items
