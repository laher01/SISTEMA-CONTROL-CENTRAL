"""Extracción conservadora de campos desde texto PDF/OCR.

Los valores son sugerencias: cada uno conserva evidencia, método y confianza para
que una persona o una etapa posterior pueda confirmarlos antes de afectar el CORE.
"""

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class CampoExtraido:
    valor: str
    confianza: float
    evidencia: str

    def a_dict(self, fuente: str) -> dict[str, object]:
        return {
            "valor": self.valor,
            "confianza": round(self.confianza, 4),
            "fuente": fuente,
            "evidencia": self.evidencia[:160],
            "requiere_confirmacion": True,
        }


REFERENCIA = re.compile(r"\b([A-Z0-9]{4})\s*[-–—]\s*0*(\d{1,8})\b", re.IGNORECASE)
RUC = re.compile(r"(?<!\d)(\d{11})(?!\d)")
FECHA_ETIQUETADA = re.compile(
    r"(?:FECHA(?:\s+DE)?\s+(?:EMISION|EMISI[ÓO]N)|EMITIDO\s+EL)\s*[:\-]?\s*"
    r"(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)
FECHA = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}-\d{2}-\d{2})\b")
TOTAL = re.compile(
    r"(?:IMPORTE\s+TOTAL|TOTAL\s+(?:A\s+PAGAR|PAGADO)|TOTAL)\s*[:=]?\s*"
    r"(?:S/\.?|US\$|USD|PEN|\$)?\s*([0-9][0-9.,\s]{0,18})",
    re.IGNORECASE,
)
OPERACION = re.compile(
    r"(?:N(?:RO|ÚMERO|UMERO)?\.?\s*(?:DE\s*)?|C[ÓO]DIGO\s+(?:DE\s*)?)"
    r"(?:OPERACI[ÓO]N|TRANSACCI[ÓO]N)\s*[:#-]?\s*([A-Z0-9-]{4,30})",
    re.IGNORECASE,
)


def extraer_campos(
    texto: str, metodo: str, confianza_texto: float | None
) -> dict[str, object] | None:
    if not texto.strip():
        return None
    fuente = "OCR" if metodo.startswith("OCR") else "TEXTO_PDF"
    factor = confianza_texto if confianza_texto is not None else 0.75
    campos: dict[str, dict[str, object]] = {}

    referencia = REFERENCIA.search(texto)
    if referencia:
        evidencia = referencia.group(0)
        campos["serie"] = CampoExtraido(
            referencia.group(1).upper(), min(0.98, 0.96 * factor), evidencia
        ).a_dict(fuente)
        campos["correlativo"] = CampoExtraido(
            str(int(referencia.group(2))), min(0.98, 0.96 * factor), evidencia
        ).a_dict(fuente)

    rucs = list(dict.fromkeys(RUC.findall(texto)))
    candidatos: dict[str, list[dict[str, object]]] = {}
    if rucs:
        candidatos["ruc"] = [
            CampoExtraido(ruc, min(0.95, 0.9 * factor), _contexto(texto, ruc)).a_dict(fuente)
            for ruc in rucs
        ]
        for nombre, etiquetas in (
            ("ruc_emisor", ("RUC EMISOR", "PROVEEDOR", "SEÑOR(ES)")),
            ("ruc_receptor", ("RUC RECEPTOR", "CLIENTE", "ADQUIRIENTE")),
        ):
            encontrado = _ruc_cercano_a_etiqueta(texto, etiquetas)
            if encontrado:
                campos[nombre] = CampoExtraido(
                    encontrado, min(0.92, 0.88 * factor), _contexto(texto, encontrado)
                ).a_dict(fuente)

    fecha_match = FECHA_ETIQUETADA.search(texto) or FECHA.search(texto)
    if fecha_match and (fecha := _normalizar_fecha(fecha_match.group(1))):
        base = 0.94 if FECHA_ETIQUETADA.match(fecha_match.group(0)) else 0.78
        campos["fecha_emision"] = CampoExtraido(
            fecha, min(0.97, base * factor), fecha_match.group(0)
        ).a_dict(fuente)

    moneda = _moneda(texto)
    if moneda:
        campos["moneda"] = CampoExtraido(
            moneda[0], min(0.95, moneda[1] * factor), moneda[2]
        ).a_dict(fuente)

    total_match = TOTAL.search(texto)
    if total_match and (importe := _normalizar_importe(total_match.group(1))) is not None:
        campos["importe_total"] = CampoExtraido(
            format(importe, ".2f"), min(0.96, 0.94 * factor), total_match.group(0)
        ).a_dict(fuente)

    operacion = OPERACION.search(texto)
    if operacion:
        campos["numero_operacion"] = CampoExtraido(
            operacion.group(1).upper(), min(0.94, 0.9 * factor), operacion.group(0)
        ).a_dict(fuente)

    if not campos and not candidatos:
        return None
    resultado: dict[str, object] = {"version": 1, "campos": campos}
    if candidatos:
        resultado["candidatos"] = candidatos
    return resultado


def _contexto(texto: str, valor: str, radio: int = 45) -> str:
    indice = texto.find(valor)
    if indice < 0:
        return valor
    return " ".join(texto[max(0, indice - radio) : indice + len(valor) + radio].split())


def _ruc_cercano_a_etiqueta(texto: str, etiquetas: tuple[str, ...]) -> str | None:
    normalizado = _sin_tildes(texto).upper()
    for etiqueta in etiquetas:
        indice = normalizado.find(_sin_tildes(etiqueta).upper())
        if indice >= 0 and (coincidencia := RUC.search(texto[indice : indice + 180])):
            return coincidencia.group(1)
    return None


def _normalizar_fecha(valor: str) -> str | None:
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", valor):
            return date.fromisoformat(valor).isoformat()
        dia, mes, anio = re.split(r"[/-]", valor)
        return date(int(anio), int(mes), int(dia)).isoformat()
    except ValueError:
        return None


def _normalizar_importe(valor: str) -> Decimal | None:
    limpio = valor.replace(" ", "").rstrip(".,")
    if not limpio:
        return None
    if "," in limpio and "." in limpio:
        if limpio.rfind(",") > limpio.rfind("."):
            limpio = limpio.replace(".", "").replace(",", ".")
        else:
            limpio = limpio.replace(",", "")
    elif "," in limpio:
        partes = limpio.split(",")
        limpio = "".join(partes) if len(partes[-1]) == 3 else limpio.replace(",", ".")
    elif limpio.count(".") > 1:
        partes = limpio.split(".")
        limpio = "".join(partes[:-1]) + "." + partes[-1]
    try:
        return Decimal(limpio).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def _moneda(texto: str) -> tuple[str, float, str] | None:
    reglas = (
        ("USD", re.compile(r"\bUSD\b|US\$|D[ÓO]LARES?", re.IGNORECASE), 0.95),
        ("PEN", re.compile(r"\bPEN\b|S/\.?|SOLES?", re.IGNORECASE), 0.92),
    )
    for codigo, patron, confianza in reglas:
        if coincidencia := patron.search(texto):
            return codigo, confianza, coincidencia.group(0)
    return None


def _sin_tildes(valor: str) -> str:
    return "".join(
        caracter
        for caracter in unicodedata.normalize("NFKD", valor)
        if not unicodedata.combining(caracter)
    )
