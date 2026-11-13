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
                descripcion=nombre[:2000],
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
    existentes = set(
        session.scalars(
            select(LineaComprobanteItem.numero_linea).where(
                LineaComprobanteItem.tenant_id == tenant_id,
                LineaComprobanteItem.documento_id == documento_id,
            )
        )
    )
    pendientes = []
    for linea in items:
        if linea.numero in existentes:
            continue
        existentes.add(linea.numero)
        nombre = texto_normalizado(linea.descripcion)
        # SUNAT puede imprimir «500ML» o «500 ML» para la misma presentación.
        medida = r"(?<=\d) *(ml|cl|l|kg|g|mg)\b"
        variantes = (re.sub(medida, r" \1", nombre), re.sub(medida, r"\1", nombre))
        claves = [
            hashlib.sha256(f"{variante}|{linea.unidad}".encode()).hexdigest()
            for variante in dict.fromkeys((nombre, *variantes))
        ]
        pendientes.append((linea, claves))
    if not pendientes:
        return 0

    claves_pendientes = list(dict.fromkeys(clave for _, claves in pendientes for clave in claves))
    productos: dict[str, ProductoItem] = {}
    for inicio in range(0, len(claves_pendientes), 1000):
        for producto_existente in session.scalars(
            select(ProductoItem).where(
                ProductoItem.tenant_id == tenant_id,
                ProductoItem.clave_catalogo.in_(claves_pendientes[inicio : inicio + 1000]),
            )
        ):
            productos[producto_existente.clave_catalogo] = producto_existente

    lineas_nuevas = []
    for linea, claves in pendientes:
        producto = next((productos[c] for c in claves if c in productos), None)
        clave = claves[0]
        if producto is None:
            producto = ProductoItem(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                clave_catalogo=clave,
                descripcion=linea.descripcion[:2000],
                unidad_base=linea.unidad,
                categoria=sugerir_categoria(linea.descripcion),
                clasificacion_confirmada=False,
                activo=True,
            )
            session.add(producto)
            productos[clave] = producto
        lineas_nuevas.append(
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
    session.flush()
    session.add_all(lineas_nuevas)
    return len(lineas_nuevas)


def registrar_items_pdf_estacion(
    session: Session, tenant_id: uuid.UUID, documento_id: uuid.UUID, texto: str
) -> int:
    items = extraer_items_pdf(texto)
    return _registrar_lineas(session, tenant_id, documento_id, items) if items else 0


def extraer_items_pdf(texto: str) -> list[ItemUBL]:
    items = extraer_items_pdf_tabla(texto)
    if items:
        return items
    if detectar_formato_documental(texto) == "MASYDASE_FACTURA":
        return extraer_items_pdf_masydase(texto)
    cabecera = re.search(
        r"CANTIDAD\s+C[ÓO]DIGO\s+U\.?M\.?\s+DESCRIPCI[ÓO]N\s+"
        r"VALOR\s+UNITARIO\s+PRECIO\s+UNITARIO\s+IMPORTE",
        texto,
        re.I,
    )
    if not cabecera:
        return (
            extraer_items_pdf_ticket(texto)
            or extraer_items_pdf_columnas(texto)
            or extraer_items_pdf_formatos_alternos(texto)
        )
    if not re.search(r"\bFACTURA\b", texto[: cabecera.start()], re.I):
        return []
    patron = re.compile(
        rf"(?P<cantidad>{_NUMERO_TABLA})\s+\S+\s+"
        rf"(?P<unidad>[A-Z][A-Z0-9./-]{{0,39}})\s+(?P<descripcion>.+?)\s+"
        rf"{_NUMERO_TABLA}\s+{_NUMERO_TABLA}\s+(?P<importe>{_NUMERO_TABLA})",
        re.I,
    )
    tabla = _FIN_TABLA.split(texto[cabecera.end() :], maxsplit=1)[0]
    if re.search(r"\bFACTURA\s+ELECTR[ÓO]NICA\b", tabla, re.I):
        return []
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
                )
            )
    return items or extraer_items_pdf_columnas(texto)


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
            rf"\s+{_NUMERO_TABLA}\s+{_NUMERO_TABLA}"
            if cabecera.group("icbper")
            else rf"\s+{_NUMERO_TABLA}"
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
                    )
                )
    return items


def extraer_items_pdf_ticket(texto: str) -> list[ItemUBL]:
    """Lee tickets fiscales con descripción primero o cantidad primero."""
    if not re.search(r"\bFACTURA\b", texto, re.I):
        return []
    cantidad = r"CANT(?:IDAD)?\.?"
    unidad = r"(?:U\.?\s*M\.?|UNIDAD(?:\s+(?:DE\s+)?MEDIDA)?)"
    descripcion = r"(?:DESCRIPCI[ÓO]N|PRODUCTO)"
    precio = r"(?:P\.?\s*UNIT(?:ARIO)?\.?|(?:PRECIO|VALOR)\s+UNITARIO)"
    cabecera = re.search(
        rf"(?im)^\s*(?P<primero>{descripcion}\s+{cantidad}\s+{unidad}|"
        rf"{cantidad}\s+{unidad}\s+{descripcion})\s+{precio}\s+(?:IMPORTE|TOTAL)\s*$",
        texto,
    )
    if cabecera is None:
        return []
    numero = _NUMERO_TABLA
    cantidad_unidad = rf"(?P<cantidad>{numero})\s+(?P<unidad>[A-Z][A-Z0-9./-]{{0,39}})"
    descripcion_fila = r"(?P<descripcion>.+?)"
    if re.match(descripcion, cabecera["primero"], re.I):
        inicio = rf"{descripcion_fila}\s+{cantidad_unidad}"
    else:
        inicio = rf"{cantidad_unidad}\s+{descripcion_fila}"
    fila = re.compile(rf"{inicio}\s+{numero}\s+(?P<importe>{numero})", re.I)
    tabla = _FIN_TABLA.split(texto[cabecera.end() :], maxsplit=1)[0]
    items = []
    for posicion, linea in enumerate(tabla.strip().splitlines(), 1):
        campos = fila.fullmatch(" ".join(linea.split()))
        if campos is None:
            continue
        unidades = Decimal(campos["cantidad"].replace(",", ""))
        importe = Decimal(campos["importe"].replace(",", ""))
        if 0 < unidades < 10**14 and 0 <= importe < 10**16:
            items.append(
                ItemUBL(
                    posicion,
                    campos["descripcion"][:2000],
                    unidades,
                    campos["unidad"].upper(),
                    importe,
                )
            )
    return items


def extraer_items_pdf_columnas(texto: str) -> list[ItemUBL]:
    """Lee tablas con separadores de columna conservados en el texto del PDF."""
    if not re.search(r"\bFACTURA\b", texto, re.I):
        return []
    etiquetas = {
        "cantidad": {"cant", "cantidad"},
        "unidad": {"um", "u m", "und", "unid", "unidad", "unidad de medida", "unidad medida"},
        "descripcion": {"descripcion", "producto", "descripcion del producto", "detalle"},
        "importe": {
            "importe",
            "total",
            "importe total",
            "valor de venta",
            "valor venta",
            "v venta",
        },
    }
    columnas: dict[str, int] = {}
    ancho = 0
    encabezados: list[str] = []
    items: list[ItemUBL] = []
    for linea in texto.splitlines():
        celdas = re.split(r" {2,}|\t+", linea.strip())
        nombres = [texto_normalizado(celda) for celda in celdas]
        detectadas = {
            campo: nombres.index(nombre)
            for campo, opciones in etiquetas.items()
            for nombre in nombres
            if nombre in opciones
        }
        if {"cantidad", "unidad", "descripcion"} <= detectadas.keys():
            columnas, ancho, encabezados = detectadas, len(celdas), nombres
            continue
        if not columnas:
            continue
        if _FIN_TABLA.match(linea) or re.match(
            r"\s*(?:op\.\s*gravadas|igv|sub\s*total|total\s+s/)", linea, re.I
        ):
            columnas = {}
            continue
        if len(celdas) == ancho - 1 and "codigo" in encabezados:
            posicion = encabezados.index("codigo")
            if posicion == 0 and re.fullmatch(_NUMERO_TABLA, celdas[0]):
                celdas.insert(0, "")
        if len(celdas) != ancho:
            continue
        cantidad = celdas[columnas["cantidad"]]
        unidad = celdas[columnas["unidad"]]
        descripcion = celdas[columnas["descripcion"]]
        if (
            not re.fullmatch(_NUMERO_TABLA, cantidad)
            or not re.fullmatch(r"[A-Za-z][A-Za-z0-9./-]{0,39}", unidad)
            or not any(letra.isalpha() for letra in descripcion)
        ):
            continue
        unidades = Decimal(cantidad.replace(",", ""))
        importe = None
        if "importe" in columnas:
            monto = re.sub(r"^(?:S/|USD)\s*|\s*(?:S/|USD)$", "", celdas[columnas["importe"]])
            if not re.fullmatch(_NUMERO_TABLA, monto):
                continue
            importe = Decimal(monto.replace(",", ""))
        if 0 < unidades < 10**14 and (importe is None or importe < 10**16):
            items.append(
                ItemUBL(len(items) + 1, descripcion[:2000], unidades, unidad.upper(), importe)
            )
    return items


def extraer_items_pdf_formatos_alternos(texto: str) -> list[ItemUBL]:
    """Reconoce tablas con códigos, unidades compuestas y descripciones partidas."""
    if not re.search(r"\bFACTURA\b", texto, re.I):
        return []
    formatos = (
        (
            r"CANTIDAD C[ÓO]DIGO DESCRIPCI[ÓO]N VALOR UNITARIO PRECIO UNITARIO IMPORTE",
            rf"(?P<cantidad>{_NUMERO_TABLA}) \S+ (?P<unidad>[A-Z]{{2,5}}) "
            rf"(?P<descripcion>.+?) {_NUMERO_TABLA} {_NUMERO_TABLA} "
            rf"(?P<importe>{_NUMERO_TABLA})",
        ),
        (
            r"CANTIDAD UNIDAD MEDIDA C[ÓO]DIGO DESCRIPCI[ÓO]N VALOR UNITARIO ICBPER",
            rf"(?P<cantidad>{_NUMERO_TABLA}) (?P<unidad>.+?) \d{{8}} "
            rf"(?P<descripcion>.+?) {_NUMERO_TABLA} {_NUMERO_TABLA}",
        ),
        (
            r"C[ÓO]DIGO DESCRIPCI[ÓO]N CANT\. P\.UNIT\. P\.TOTAL",
            rf"\S+ (?P<descripcion>.+?) (?P<cantidad>{_NUMERO_TABLA}) "
            rf"{_NUMERO_TABLA} (?P<importe>{_NUMERO_TABLA})",
        ),
    )
    lineas = texto.splitlines()
    for indice, linea in enumerate(lineas):
        cabecera = " ".join(linea.split())
        for encabezado, patron in formatos:
            if not re.fullmatch(encabezado, cabecera, re.I):
                continue
            items: list[ItemUBL] = []
            for fila in lineas[indice + 1 :]:
                limpia = " ".join(fila.split())
                if not limpia:
                    continue
                if _FIN_TABLA.match(limpia) or re.match(
                    r"^(?:OP[. ]|IGV\b|TOTAL\b|S/TOTAL|[-_]{3,})", limpia, re.I
                ):
                    break
                match = re.fullmatch(patron, limpia, re.I)
                if match:
                    datos = match.groupdict()
                    cantidad = Decimal(datos["cantidad"].replace(",", ""))
                    monto = datos.get("importe")
                    importe = Decimal(monto.replace(",", "")) if monto else None
                    if 0 < cantidad < 10**14 and (importe is None or importe < 10**16):
                        items.append(
                            ItemUBL(
                                len(items) + 1,
                                datos["descripcion"][:2000],
                                cantidad,
                                (datos.get("unidad") or "")[:40].upper(),
                                importe,
                            )
                        )
                elif items and "P.TOTAL" in cabecera.upper():
                    anterior = items[-1]
                    items[-1] = ItemUBL(
                        anterior.numero,
                        f"{anterior.descripcion} {limpia}"[:2000],
                        anterior.cantidad,
                        anterior.unidad,
                        anterior.importe,
                    )
            if items:
                return items
    return []


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
            ItemUBL(len(items) + 1, descripcion, cantidad_decimal, unidad, importe_decimal)
        )
        suma += importe_decimal
    if suma != Decimal(total.group(1).replace(",", "")):
        return []
    return items
