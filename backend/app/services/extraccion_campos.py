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
RUC_FLEXIBLE = re.compile(r"(?<!\d)((?:\d[\s.\-]?){10}\d)(?!\d)")
FECHA_ETIQUETADA = re.compile(
    r"(?:FECHA(?:\s+DE)?\s+(?:EMISION|EMISI[ÓO]N)|EMITIDO\s+EL)\s*[:\-]?\s*"
    r"(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)
FECHA = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}-\d{2}-\d{2})\b")
TOTAL = re.compile(
    r"(?:IMPORTE\s+TOTAL|IMPORTE\s+NETO|MONTO\s+(?:TOTAL|NETO)|"
    r"TOTAL\s+(?:A\s+PAGAR|PAGADO|POR\s+HONORARIOS|HONORARIOS)|TOTAL)\s*[:=]?\s*"
    r"(?:S/\.?|US\$|USD|PEN|\$)?\s*([0-9][0-9.,\s]{0,18})",
    re.IGNORECASE,
)
OPERACION = re.compile(
    r"(?:N(?:RO|ÚMERO|UMERO)?\.?\s*(?:DE\s*)?|C[ÓO]DIGO\s+(?:DE\s*)?)"
    r"(?:OPERACI[ÓO]N|TRANSACCI[ÓO]N)\s*[:#-]?\s*([A-Z0-9-]{4,30})",
    re.IGNORECASE,
)

ETIQUETAS_EMISOR = (
    "RAZÓN SOCIAL EMISOR",
    "RAZON SOCIAL EMISOR",
    "PROVEEDOR",
    "EMISOR",
)
ETIQUETAS_RECEPTOR = (
    "RAZÓN SOCIAL RECEPTOR",
    "RAZON SOCIAL RECEPTOR",
    "CLIENTE",
    "ADQUIRIENTE",
    "SEÑOR(ES)",
    "SEÑORES",
    "SENORES",
)
ETIQUETAS_RUC_EMISOR = (
    "RUC EMISOR",
    "RUC DEL EMISOR",
    "RUC PROVEEDOR",
    "PROVEEDOR",
)
ETIQUETAS_RUC_RECEPTOR = (
    "RUC RECEPTOR",
    "RUC DEL RECEPTOR",
    "RUC CLIENTE",
    "CLIENTE",
    "ADQUIRIENTE",
)
ETIQUETAS_RHE_RECEPTOR = (
    "IDENTIFICADO CON RUC",
    "IDENTIFICADA CON RUC",
    "RUC DEL USUARIO",
    "RUC DEL CLIENTE",
    "RUC DEL RECEPTOR",
)
ETIQUETAS_RHE_NOMBRE_RECEPTOR = (
    "RECIBÍ DE",
    "RECIBI DE",
    "RECIBIDO DE",
)

NO_RAZON = (
    "FACTURA",
    "BOLETA",
    "RECIBO POR HONORARIOS",
    "GUIA DE REMISION",
    "RUC",
    "FECHA DE EMISION",
    "DIRECCION",
    "DOMICILIO",
    "MONEDA",
    "TOTAL",
    "IMPORTE",
    "TELEFONO",
    "CELULAR",
    "CORREO",
    "EMAIL",
    "PAGINA",
    "SUNAT",
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

    rucs = _rucs_en_texto(texto)
    candidatos: dict[str, list[dict[str, object]]] = {}
    if rucs:
        candidatos["ruc"] = [
            CampoExtraido(ruc, min(0.95, 0.9 * factor), _contexto(texto, ruc)).a_dict(fuente)
            for ruc in rucs
        ]

    es_rhe = _es_rhe(texto)
    if es_rhe:
        _extraer_partes_rhe(texto, rucs, campos, fuente, factor)
    else:
        _extraer_rucs_etiquetados(texto, campos, fuente, factor)

    _extraer_razones_etiquetadas(texto, campos, fuente, factor)
    _completar_razones_por_ruc(texto, campos, fuente, factor)

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
    resultado: dict[str, object] = {"version": 2, "campos": campos}
    if candidatos:
        resultado["candidatos"] = candidatos
    return resultado


def _extraer_rucs_etiquetados(
    texto: str,
    campos: dict[str, dict[str, object]],
    fuente: str,
    factor: float,
) -> None:
    for nombre, etiquetas in (
        ("ruc_emisor", ETIQUETAS_RUC_EMISOR),
        ("ruc_receptor", ETIQUETAS_RUC_RECEPTOR),
    ):
        encontrado = _ruc_cercano_a_etiqueta(texto, etiquetas)
        if encontrado:
            campos[nombre] = CampoExtraido(
                encontrado, min(0.92, 0.88 * factor), _contexto(texto, encontrado)
            ).a_dict(fuente)


def _extraer_partes_rhe(
    texto: str,
    rucs: list[str],
    campos: dict[str, dict[str, object]],
    fuente: str,
    factor: float,
) -> None:
    receptor = _ruc_cercano_a_etiqueta(texto, ETIQUETAS_RHE_RECEPTOR)
    if receptor is None:
        receptor = _ruc_cercano_a_etiqueta(texto, ETIQUETAS_RUC_RECEPTOR)
    if receptor:
        campos["ruc_receptor"] = CampoExtraido(
            receptor, min(0.95, 0.92 * factor), _contexto(texto, receptor)
        ).a_dict(fuente)

    emisor = _ruc_cercano_a_etiqueta(texto, ETIQUETAS_RUC_EMISOR)
    if emisor:
        campos["ruc_emisor"] = CampoExtraido(
            emisor, min(0.95, 0.92 * factor), _contexto(texto, emisor)
        ).a_dict(fuente)

    if receptor and "ruc_emisor" not in campos:
        otros = [ruc for ruc in rucs if ruc != receptor]
        if len(otros) == 1:
            campos["ruc_emisor"] = CampoExtraido(
                otros[0], min(0.9, 0.86 * factor), _contexto(texto, otros[0])
            ).a_dict(fuente)

    if emisor and "ruc_receptor" not in campos:
        otros = [ruc for ruc in rucs if ruc != emisor]
        if len(otros) == 1:
            campos["ruc_receptor"] = CampoExtraido(
                otros[0], min(0.9, 0.86 * factor), _contexto(texto, otros[0])
            ).a_dict(fuente)

    if "ruc_emisor" not in campos and "ruc_receptor" not in campos and len(rucs) == 2:
        campos["ruc_emisor"] = CampoExtraido(
            rucs[0], min(0.88, 0.84 * factor), _contexto(texto, rucs[0])
        ).a_dict(fuente)
        campos["ruc_receptor"] = CampoExtraido(
            rucs[1], min(0.88, 0.84 * factor), _contexto(texto, rucs[1])
        ).a_dict(fuente)

    nombre_receptor = _razon_social_cercana_a_etiqueta(texto, ETIQUETAS_RHE_NOMBRE_RECEPTOR)
    if nombre_receptor:
        campos["razon_social_receptor"] = CampoExtraido(
            nombre_receptor, min(0.92, 0.9 * factor), nombre_receptor
        ).a_dict(fuente)


def _extraer_razones_etiquetadas(
    texto: str,
    campos: dict[str, dict[str, object]],
    fuente: str,
    factor: float,
) -> None:
    for nombre, etiquetas in (
        ("razon_social_emisor", ETIQUETAS_EMISOR),
        ("razon_social_receptor", ETIQUETAS_RECEPTOR),
    ):
        if nombre in campos:
            continue
        encontrado = _razon_social_cercana_a_etiqueta(texto, etiquetas)
        if encontrado:
            campos[nombre] = CampoExtraido(
                encontrado, min(0.9, 0.86 * factor), encontrado
            ).a_dict(fuente)


def _completar_razones_por_ruc(
    texto: str,
    campos: dict[str, dict[str, object]],
    fuente: str,
    factor: float,
) -> None:
    for nombre_razon, nombre_ruc in (
        ("razon_social_emisor", "ruc_emisor"),
        ("razon_social_receptor", "ruc_receptor"),
    ):
        if nombre_razon in campos or nombre_ruc not in campos:
            continue
        ruc = str(campos[nombre_ruc]["valor"])
        encontrado = _razon_social_cercana_a_ruc(texto, ruc)
        if encontrado:
            campos[nombre_razon] = CampoExtraido(
                encontrado, min(0.86, 0.82 * factor), encontrado
            ).a_dict(fuente)


def _rucs_en_texto(texto: str) -> list[str]:
    encontrados: list[str] = []
    for coincidencia in RUC_FLEXIBLE.finditer(texto):
        ruc = re.sub(r"\D", "", coincidencia.group(1))
        if len(ruc) == 11 and ruc not in encontrados:
            encontrados.append(ruc)
    return encontrados


def _contexto(texto: str, valor: str, radio: int = 45) -> str:
    indice = texto.find(valor)
    if indice < 0:
        return valor
    return " ".join(texto[max(0, indice - radio) : indice + len(valor) + radio].split())


def _ruc_cercano_a_etiqueta(texto: str, etiquetas: tuple[str, ...]) -> str | None:
    normalizado = _sin_tildes(texto).upper()
    for etiqueta in etiquetas:
        indice = normalizado.find(_sin_tildes(etiqueta).upper())
        if indice < 0:
            continue
        fragmento = texto[indice : indice + 240]
        rucs = _rucs_en_texto(fragmento)
        if rucs:
            return rucs[0]
    return None


def _razon_social_cercana_a_etiqueta(texto: str, etiquetas: tuple[str, ...]) -> str | None:
    lineas = texto.splitlines()
    normalizadas = [_sin_tildes(linea).upper() for linea in lineas]
    for indice, linea_norm in enumerate(normalizadas):
        for etiqueta in etiquetas:
            etiqueta_norm = _sin_tildes(etiqueta).upper()
            pos = linea_norm.find(etiqueta_norm)
            if pos < 0:
                continue
            original = lineas[indice]
            candidato = original[pos + len(etiqueta) :].strip(" :-\t")
            candidato = _recortar_razon(candidato)
            if not candidato and indice + 1 < len(lineas):
                candidato = _recortar_razon(lineas[indice + 1])
            if _razon_social_valida(candidato):
                return candidato[:300]
    return None


def _razon_social_cercana_a_ruc(texto: str, ruc: str) -> str | None:
    lineas = texto.splitlines()
    for indice, linea in enumerate(lineas):
        if ruc not in re.sub(r"[\s.\-]", "", linea):
            continue

        antes = re.split(r"\bRUC\b", linea, maxsplit=1, flags=re.IGNORECASE)[0]
        antes = _recortar_razon(antes)
        if _razon_social_valida(antes):
            return antes[:300]

        for distancia in (1, 2, 3):
            previo = indice - distancia
            if previo >= 0:
                candidato = _recortar_razon(lineas[previo])
                if _razon_social_valida(candidato):
                    return candidato[:300]

        for distancia in (1, 2):
            siguiente = indice + distancia
            if siguiente < len(lineas):
                candidato = _recortar_razon(lineas[siguiente])
                if _razon_social_valida(candidato):
                    return candidato[:300]
    return None


def _recortar_razon(valor: str) -> str:
    candidato = " ".join(valor.split()).strip(" -:;,")
    candidato = re.split(
        r"\b(?:RUC|IDENTIFICAD[OA]\s+CON\s+RUC|DIRECCI[ÓO]N|DOMICILIO|FECHA|"
        r"MONEDA|TOTAL|POR\s+CONCEPTO|LA\s+SUMA)\b\s*[:\-]?",
        candidato,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    candidato = re.sub(
        r"^(?:RAZ[ÓO]N\s+SOCIAL|PROVEEDOR|EMISOR|CLIENTE|ADQUIRIENTE|"
        r"SEÑOR\(ES\)|SEÑORES|SENORES|RECIB[IÍ]\s+DE|RECIBIDO\s+DE)\s*[:\-]?\s*",
        "",
        candidato,
        flags=re.IGNORECASE,
    )
    return " ".join(candidato.split()).strip(" -:;,")


def _razon_social_valida(valor: str) -> bool:
    if len(valor) < 3 or len(valor) > 300:
        return False
    if re.fullmatch(r"\d{11}", valor):
        return False
    if not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", valor):
        return False
    normalizado = _sin_tildes(valor).upper().strip()
    if any(normalizado == invalido or normalizado.startswith(f"{invalido} ") for invalido in NO_RAZON):
        return False
    if "HTTP://" in normalizado or "HTTPS://" in normalizado or "WWW." in normalizado:
        return False
    return True


def _es_rhe(texto: str) -> bool:
    normalizado = _sin_tildes(texto).upper()
    return "RECIBO POR HONORARIOS" in normalizado


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
