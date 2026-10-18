"""Lector conservador de transferencias BCP: sugerencias, no comprobantes fiscales."""

import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation

MESES = {
    "ENERO": 1,
    "FEBRERO": 2,
    "MARZO": 3,
    "ABRIL": 4,
    "MAYO": 5,
    "JUNIO": 6,
    "JULIO": 7,
    "AGOSTO": 8,
    "SEPTIEMBRE": 9,
    "SETIEMBRE": 9,
    "OCTUBRE": 10,
    "NOVIEMBRE": 11,
    "DICIEMBRE": 12,
}


def extraer_transferencia_bcp(texto: str) -> dict[str, tuple[str, str]]:
    normal = "".join(
        c for c in unicodedata.normalize("NFKD", texto.upper()) if not unicodedata.combining(c)
    )
    if "BCP" not in normal or "TRANSFERENCIA EXITOSA" not in normal:
        return {}
    campos: dict[str, tuple[str, str]] = {"banco": ("BCP", "BCP transferencia exitosa")}
    operacion = re.search(
        r"(?is)N[ÚU]MERO\s+DE\s+OPERACI[ÓO]N\s*[:#]?\s*(\d{6,20})\b",
        texto,
    )
    if operacion:
        campos["numero_operacion"] = (operacion.group(1), operacion.group(0))
    importe = re.search(r"(?im)^\s*S/\s*([\d,]+\.\d{2})\s*$", texto)
    if importe:
        try:
            valor = Decimal(importe.group(1).replace(",", ""))
            if valor > 0:
                campos["importe_total"] = (str(valor.quantize(Decimal("0.01"))), importe.group(0))
                campos["moneda"] = ("PEN", importe.group(0))
        except InvalidOperation:
            pass
    fecha = re.search(
        r"(?i)\b(\d{1,2})\s+(?:DE\s+)?"
        r"(ENERO|FEBRERO|MARZO|ABRIL|MAYO|JUNIO|JULIO|AGOSTO|"
        r"SEPTIEMBRE|SETIEMBRE|OCTUBRE|NOVIEMBRE|DICIEMBRE)\s+(20\d{2})",
        normal,
    )
    if fecha:
        try:
            fecha_valida = date(int(fecha.group(3)), MESES[fecha.group(2)], int(fecha.group(1)))
            campos["fecha_emision"] = (fecha_valida.isoformat(), fecha.group(0))
        except ValueError:
            pass
    beneficiario = re.search(r"(?im)^\s*Enviado\s+a\s*:?\s*([^\n]+)", texto)
    if beneficiario and beneficiario.group(1).strip():
        campos["beneficiario"] = (beneficiario.group(1).strip(), beneficiario.group(0))
    return campos
