"""Lectura estricta de tablas de PDF nativo; no infiere importes ausentes."""

import re
from decimal import Decimal

NUM = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
Fila = tuple[str, Decimal, str, Decimal]


def _decimal(valor: str) -> Decimal:
    return Decimal(valor.replace(",", ""))


def _fila(match: re.Match[str], unidad: str) -> Fila | None:
    cantidad, precio, importe = map(_decimal, (match["cant"], match["precio"], match["importe"]))
    if not 0 < cantidad < 10**14 or not 0 <= importe < 10**16:
        return None
    if abs(cantidad * precio - importe) > Decimal("0.02"):
        return None
    descripcion = " ".join(match["desc"].split())
    if not any(c.isalpha() for c in descripcion):
        return None
    return descripcion[:2000], cantidad, unidad, importe


def extraer_items_nativos(texto: str) -> list[Fila]:
    """Acepta únicamente lotes reconciliados con el total o base impresa."""
    if not re.search(r"\bFACTURA ELECTR[ÓO]NICA\b", texto, re.I):
        return []
    filas: list[Fila] = []
    if "facturalaya" in texto.lower():
        cabecera = re.search(
            r"(?im)^CANT\.\s+DESCRIPCI[ÓO]N\s+"
            r"(PRECIO UNITARIO\s+UNID/MED\s+AFECT\.IGV|PRECIO)\s+IMPORTE\s*$",
            texto,
        )
        if not cabecera:
            return []
        tabla = re.split(
            r"(?im)^\s*(?:SON\b|GRAVADA:|IMPORTE EN LETRAS:)",
            texto[cabecera.end() :],
            maxsplit=1,
        )[0].strip()
        if "UNID/MED" in cabecera[1].upper():
            patron = re.compile(
                rf"(?m)^(?P<cant>{NUM})[ \t]*\n(?P<desc>[^\n]+(?:\n[^\n]+){{0,4}}?)"
                rf"\n[ \t]*S/\s*(?P<precio>{NUM})\s*\n(?P<unidad>[^\n]+)"
                rf"\n(?:Gravado|Exonerado|Inafecto)\s*\n[ \t]*S/\s*(?P<importe>{NUM})[ \t]*$",
                re.I,
            )
        else:
            patron = re.compile(
                rf"(?m)^(?P<cant>{NUM})[ \t]*\n(?P<desc>[\s\S]+?)"
                rf"\n(?P<precio>{NUM})[ \t]*\n(?P<importe>{NUM})[ \t]*$"
            )
        for m in patron.finditer(tabla):
            item = _fila(m, m.groupdict().get("unidad", "NIU").strip().upper())
            if item:
                filas.append(item)
        total = re.search(rf"(?im)^TOTAL[ \t]*:\s*S/\s*({NUM})", texto)
    elif re.search(r"https?://[^\s/]+\.factcentral\.online/buscar", texto, re.I):
        cabeceras = list(
            re.finditer(
                r"(?im)^COD\.\s*CANT\.\s*UNIDAD\s*DESCRIPCI[ÓO]N\s*"
                r"(?P<marca>MARCA\s+)?P\.UNIT\s*(?P<dto>DTO\.\s+)?TOTAL\s*$",
                texto,
            )
        )
        if not cabeceras:
            return []
        for i, cabecera in enumerate(cabeceras):
            fin = cabeceras[i + 1].start() if i + 1 < len(cabeceras) else len(texto)
            tabla = re.split(
                r"(?im)^\s*(?:OP\. GRAVADAS|Para consultar el comprobante)",
                texto[cabecera.end() : fin],
                maxsplit=1,
            )[0].strip()
            patron = re.compile(
                rf"(?m)^\S+\s+(?P<cant>{NUM})\s+(?P<unidad>[A-Z]{{2,5}})\s+"
                rf"(?P<desc>[\s\S]+?)\s+(?P<precio>{NUM})\s+"
                + (rf"{NUM}\s+" if cabecera["dto"] else "")
                + rf"(?P<importe>{NUM})[ \t]*$"
            )
            pagina: list[Fila] = []
            # Algunos códigos largos se parten en dos líneas; unir solo el código.
            tabla = re.sub(r"(?m)^(\w+)\n(\d+)\n(?=\d+\s+[A-Z]{2,5}\s)", r"\1\2\n", tabla)
            for m in patron.finditer(tabla):
                item = _fila(m, m["unidad"])
                if item:
                    pagina.append(item)
            filas.extend(pagina)
        total = re.search(rf"(?im)^TOTAL A PAGAR:\s*S/\s*({NUM})", texto)
    elif "www.efact.pe" in texto.lower():
        cabecera = re.search(
            r"(?im)^C[ÓO]DIGO\s+CANT\.\s+UNID\.\s+DESCRIPCI[ÓO]N\s+"
            r"V\. UNIT\.\s+DSCTO\.\s+V\. VENTA\s*$",
            texto,
        )
        if not cabecera:
            return []
        tabla = re.split(r"(?im)^\s*OBSERVACIONES", texto[cabecera.end() :], maxsplit=1)[0].strip()
        patron = re.compile(
            rf"(?m)^(?:\S+\s+)?(?P<cant>{NUM})\s+(?P<unidad>[A-Z]{{2,5}})\s+"
            rf"(?P<desc>.+?)\s+(?P<precio>{NUM})\s+0(?:\.0+)?\s+(?P<importe>{NUM})$"
        )
        for m in patron.finditer(tabla):
            item = _fila(m, m["unidad"])
            if item:
                filas.append(item)
        # EFACT imprime líneas sin IGV: se concilian con subtotal, no total.
        total = re.search(rf"(?im)^\s*SUB TOTAL\s*S/\s*({NUM})", texto)
        if total is None:
            # La secuencia de etiquetas y valores se conserva aun cuando se
            # extraen en dos bloques separados, como en el PDF EFACT nativo.
            total = re.search(
                rf"(?im)^\s*SUB TOTAL\s*\nICBPER\s*\nISC\s*\nIGV\s*\n"
                rf"(?:S/\s*{NUM}\s*\n){{6}}S/\s*({NUM})\s*$",
                texto,
            )
    else:
        return []
    if not total or not filas:
        return []
    esperado = _decimal(total[1])
    if abs(sum((f[3] for f in filas), Decimal(0)) - esperado) <= Decimal("0.02"):
        return filas
    return []
