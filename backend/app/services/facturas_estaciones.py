"""Extracción conservadora de facturas de estaciones de servicio.

No modifica identidad fiscal por evidencia ambigua. Compatibilidad con
representaciones tipo JADAL (F109 Nº 0016490) y tickets JABSA (F003-00004475).
"""

import re
from decimal import Decimal, InvalidOperation


def _monto(texto: str) -> Decimal | None:
    limpio = texto.replace(",", "").replace(" ", "")
    try:
        return Decimal(limpio).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def extraer_factura_estacion(texto: str) -> dict[str, tuple[str, str]]:
    """Devuelve únicamente campos apoyados por etiquetas inequívocas."""
    normal = texto.upper()
    escorpio = "FACTURACION.JADAL.PE" in normal and "FACTURA" in normal
    jabsa = "SERVICENTRO JABSA" in normal and "FACTURA" in normal
    if not (escorpio or jabsa):
        return {}
    campos: dict[str, tuple[str, str]] = {}
    compacto = " ".join(texto.split())
    numero = re.search(
        r"\b(F[0-9]{3})\s*(?:[-–—]\s*|N[°ºO.]\s*)0*([0-9]{1,10})\b",
        texto,
        re.I,
    )
    if numero:
        campos["serie"] = (numero.group(1).upper(), numero.group(0))
        campos["correlativo"] = (str(int(numero.group(2))), numero.group(0))

    if escorpio:
        emisor = re.search(r"R\.?U\.?C\.?\s*N[°º]?\s*(\d{11})", texto, re.I)
        receptor_nombre = re.search(
            r"SEÑOR\(ES\)\s*:\s*(.+?)\s+(?:DIRECCI[OÖÓ]N|RUC)\b", compacto, re.I
        )
        receptor_ruc = re.search(r"\bRUC\s*:\s*(\d{11})", compacto, re.I)
        nombre = re.search(
            r"(INVERSIONES\s+Y\s+ASESORAMIENTO\s+ESCORPIO\s+SAC)",
            " ".join(texto.split()),
            re.I,
        )
        if nombre and emisor:
            campos["razon_social_emisor"] = (nombre.group(1).strip(), nombre.group(0))
        if emisor:
            campos["ruc_emisor"] = (emisor.group(1), emisor.group(0))
        if receptor_nombre:
            campos["razon_social_receptor"] = (receptor_nombre.group(1), receptor_nombre.group(0))
        if receptor_ruc:
            campos["ruc_receptor"] = (receptor_ruc.group(1), receptor_ruc.group(0))
    else:
        emisor = re.search(r"(?m)^\s*RUC\s*:\s*(\d{11})", texto, re.I)
        receptor = re.search(r"(?m)^\s*RUC\s*:\s*(\d{11})\s+Placa\s*:", texto, re.I)
        nombre = re.search(r"SERVICENTRO\s+JABSA\s+S\.?A\.?", texto, re.I)
        cliente = re.search(r"(?m)^\s*Cliente\s*:\s*(.+)$", texto, re.I)
        if emisor:
            campos["ruc_emisor"] = (emisor.group(1), emisor.group(0))
        if nombre:
            campos["razon_social_emisor"] = (nombre.group(0).strip(), nombre.group(0))
        if receptor:
            campos["ruc_receptor"] = (receptor.group(1), receptor.group(0))
        if cliente:
            campos["razon_social_receptor"] = (cliente.group(1).strip(), cliente.group(0))
        # Algunos tickets pypdf separan las columnas Cliente/RUC de sus valores.
        if "ruc_receptor" not in campos and "Cliente" in texto:
            bloque = texto[texto.find("Cliente") :]
            cliente_despues = re.search(
                r"(?m)^\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ .-]{8,})\s*\n\s*(\d{11})\s*$",
                bloque,
            )
            if cliente_despues:
                campos["razon_social_receptor"] = (
                    cliente_despues.group(1).strip(),
                    cliente_despues.group(0),
                )
                campos["ruc_receptor"] = (cliente_despues.group(2), cliente_despues.group(0))

    total_label = "IMPORTE TOTAL" if escorpio else "TOTAL"
    total_re = re.compile(
        rf"\b{total_label}\s*(?:S/\.?\s*)?([0-9][0-9,.]*)\b",
        re.I,
    )
    encontrados = list(total_re.finditer(compacto))
    if encontrados:
        valor = _monto(encontrados[-1].group(1))
        if valor is not None:
            campos["importe_total"] = (str(valor), encontrados[-1].group(0))
    # En el PDF fragmentado "S/TOTAL" puede preceder al IGV, no al total.
    if jabsa and "S/TOTAL" in texto.upper():
        campos.pop("importe_total", None)
    if jabsa and "importe_total" not in campos:
        # El motor PDF puede colocar la cifra total debajo de OP.GRAVADAS,
        # y la cifra de IGV antes de su etiqueta. Solo aceptar si cuadra.
        bases = re.search(r"OP\.GRAVADAS\s*S/\s*([0-9,.]+)\s*\n\s*([0-9,.]+)", texto, re.I)
        igv = re.search(r"([0-9,.]+)\s*S/\s*IGV\b", texto, re.I)
        if bases and igv:
            base = _monto(bases.group(1))
            candidato = _monto(bases.group(2))
            impuesto = _monto(igv.group(1))
            if (
                base is not None
                and candidato is not None
                and impuesto is not None
                and abs(base + impuesto - candidato) <= Decimal("0.02")
            ):
                campos["importe_total"] = (str(candidato), f"{bases.group(0)} | {igv.group(0)}")

    if escorpio:
        fecha = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", texto)
        if fecha:
            campos["fecha_emision"] = (fecha.group(1), fecha.group(0))
    else:
        fecha = re.search(r"Fecha\s+Emision\s*:\s*(\d{2})/(\d{2})/(20\d{2})", texto, re.I)
        if fecha:
            campos["fecha_emision"] = (
                f"{fecha.group(3)}-{fecha.group(2)}-{fecha.group(1)}",
                fecha.group(0),
            )
    if jabsa and "fecha_emision" not in campos:
        invertida = re.search(r"(\d{2})/(\d{2})/(20\d{2})\s*Fecha\s+Emision", texto, re.I)
        if invertida:
            campos["fecha_emision"] = (
                f"{invertida.group(3)}-{invertida.group(2)}-{invertida.group(1)}",
                invertida.group(0),
            )
    if campos.get("importe_total"):
        campos["moneda"] = ("PEN", "S/ (total)")
    return campos
