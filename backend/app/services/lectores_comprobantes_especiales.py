"""Lectores acotados de comprobantes bancarios y facturas F109.

No crean expedientes ni identidades fiscales a partir de un nombre de archivo.
Los datos permanecen como sugerencias auditables para confirmación humana.
"""

import re
import unicodedata
from contextlib import suppress
from datetime import date
from decimal import Decimal, InvalidOperation


def _simple(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def _importe(texto: str) -> str | None:
    numero = texto.replace(",", "").replace(" ", "")
    try:
        valor = Decimal(numero)
    except InvalidOperation:
        return None
    if valor <= 0:
        return None
    return str(valor.quantize(Decimal("0.01")))


def leer_comprobante_especial(
    texto: str,
) -> dict[str, tuple[str, str]]:
    """Devuelve campo → (valor, evidencia). Sin afirmaciones de identidad sin etiqueta."""
    normal = _simple(texto).upper()
    campos: dict[str, tuple[str, str]] = {}

    if "FACTURA ELECTRONICA" in normal:
        # F109 Nº 0016490, con o sin guion; no asumir siempre E001/F001.
        numero = re.search(
            r"(?im)\b([FE]\d{3})\s*(?:[-–—]|N\s*[°º.]?\s*[:.]?)\s*(\d{1,10})\b",
            texto,
        )
        if numero:
            campos["serie"] = (numero.group(1).upper(), numero.group(0))
            campos["correlativo"] = (str(int(numero.group(2))), numero.group(0))
        # RUC del proveedor en la cabecera, con puntos, espacios y Nº.
        emisor = re.search(r"(?i)R\s*\.?\s*U\s*\.?\s*C\s*\.?\s*N\s*[°º.]?\s*(\d{11})", texto)
        if emisor:
            campos["ruc_emisor"] = (emisor.group(1), emisor.group(0))
        # No inferir el RUC receptor de la cabecera; exigir etiqueta de cliente.
        cliente = re.search(
            r"(?is)\bSE[ÑN]OR\s*\(\s*ES\s*\).*?\bRUC\s*:?\s*(\d{11})\b",
            texto[:1800],
        )
        if cliente:
            campos["ruc_receptor"] = (cliente.group(1), cliente.group(0)[-90:])
        total = re.search(
            r"(?i)IMPORTE\s+TOTAL\s*(?:S/\s*)?([\d,]+\.\d{2})",
            texto,
        )
        if total and (valor := _importe(total.group(1))) is not None:
            campos["importe_total"] = (valor, total.group(0))
        return campos

    if "BCP" not in normal or "TRANSFERENCIA EXITOSA" not in normal:
        return campos

    campos["banco"] = ("BCP", "BCP — Transferencia exitosa")
    operacion = re.search(
        r"(?is)N[ÚU]MERO\s+DE\s+OPERACI[ÓO]N\s*[:#]?\s*(\d{6,20})\b",
        texto,
    )
    if operacion:
        # Conservar el identificador bancario como string, incluyendo ceros.
        campos["numero_operacion"] = (operacion.group(1), operacion.group(0))
    importe = re.search(r"(?im)^\s*S/\s*([\d,]+\.\d{2})\s*$", texto)
    if importe and (valor := _importe(importe.group(1))) is not None:
        campos["importe_total"] = (valor, importe.group(0))
        campos["moneda"] = ("PEN", importe.group(0))
    fecha = re.search(
        r"(?i)\b(\d{1,2})\s+(?:DE\s+)?"
        r"(ENERO|FEBRERO|MARZO|ABRIL|MAYO|JUNIO|JULIO|AGOSTO|"
        r"SEPTIEMBRE|SETIEMBRE|OCTUBRE|NOVIEMBRE|DICIEMBRE)\s+(20\d{2})",
        normal,
    )
    if fecha:
        meses = [
            "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
            "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE",
            "NOVIEMBRE", "DICIEMBRE",
        ]
        mes = "SEPTIEMBRE" if fecha.group(2) == "SETIEMBRE" else fecha.group(2)
        with suppress(ValueError):
            campos["fecha_emision"] = (
                date(int(fecha.group(3)), meses.index(mes) + 1, int(fecha.group(1))).isoformat(),
                fecha.group(0),
            )
    # El beneficiario queda como evidencia comercial, nunca como RUC.
    beneficiario = re.search(r"(?im)^\s*Enviado\s+a\s*[:]?\s*([^\n]+)", texto)
    if beneficiario and beneficiario.group(1).strip():
        campos["beneficiario"] = (beneficiario.group(1).strip(), beneficiario.group(0))
    return campos
