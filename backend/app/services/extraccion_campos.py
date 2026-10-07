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
    "RAZÓN SOCIAL",
    "RAZON SOCIAL",
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
    "INFORMACION",
    "INFORMACIÓN",
    "REPRESENTACION IMPRESA",
    "REPRESENTACIÓN IMPRESA",
    "OBSERVACION",
    "OBSERVACIÓN",
    "REFERENCIA",
    "DETALLE",
    "DESCRIPCION",
    "DESCRIPCIÓN",
    "AVENIDA",
    "AV.",
    "JR.",
    "JIRON",
    "CALLE",
    "CARRETERA",
    "MZ.",
    "MANZANA",
    "LOTE",
    "URB.",
    "URBANIZACION",
    "DISTRITO",
    "PROVINCIA",
    "DEPARTAMENTO",
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

    formato = detectar_formato_documental(texto)
    es_rhe = _es_rhe(texto)
    if es_rhe:
        _extraer_partes_rhe(texto, rucs, campos, fuente, factor)
    else:
        _extraer_rucs_etiquetados(texto, campos, fuente, factor)
        _aplicar_parser_especializado(texto, formato, rucs, campos, fuente, factor)

    _extraer_razones_vinculadas_a_ruc(texto, campos, fuente, factor)

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
    resultado: dict[str, object] = {
        "version": 3,
        "formato_documental": formato,
        "campos": campos,
    }
    if candidatos:
        resultado["candidatos"] = candidatos
    return resultado



def _aplicar_parser_especializado(
    texto: str,
    formato: str,
    rucs: list[str],
    campos: dict[str, dict[str, object]],
    fuente: str,
    factor: float,
) -> None:
    """Completa partes usando estructuras conocidas sin anular la trazabilidad."""
    if formato == "SUNAT_FACTURA":
        _parsear_factura_sunat(texto, rucs, campos, fuente, factor)
    elif formato == "OSE_FACTURALAYA":
        _parsear_facturalaya(texto, rucs, campos, fuente, factor)
    elif formato == "OSE_FACTUHOST":
        _parsear_factuhost(texto, rucs, campos, fuente, factor)
    elif formato == "OSE_EFACT":
        _parsear_efact(texto, rucs, campos, fuente, factor)


def _poner_campo(
    campos: dict[str, dict[str, object]],
    nombre: str,
    valor: str,
    confianza: float,
    evidencia: str,
    fuente: str,
) -> None:
    if valor:
        campos[nombre] = CampoExtraido(valor, confianza, evidencia).a_dict(fuente)


def _lineas_limpias(texto: str) -> list[str]:
    return [" ".join(linea.split()).strip(" :\t") for linea in texto.splitlines()]


def _indice_linea(lineas: list[str], patron: str) -> int | None:
    regex = re.compile(patron, re.IGNORECASE)
    for indice, linea in enumerate(lineas):
        if regex.search(_sin_tildes(linea)):
            return indice
    return None


def _razon_emisor_encabezado(lineas: list[str], limite: int) -> tuple[str, str] | None:
    candidatos: list[str] = []
    for linea in lineas[:limite]:
        if not linea:
            continue
        normal = _sin_tildes(linea).upper()
        if any(
            token in normal
            for token in (
                "FACTURA ELECTRONICA",
                "RUC:",
                "R.U.C.",
                "RUC ",
                "TEL:",
                "TELEFONO",
                "EMAIL:",
                "WWW.",
                "HTTP",
            )
        ):
            continue
        if _parece_direccion(linea):
            if candidatos:
                break
            continue
        if _razon_social_valida(linea):
            candidatos.append(linea)
        elif candidatos:
            break
    if not candidatos:
        return None

    # Preferir la última línea con forma societaria; si no existe, la primera
    # razón válida del encabezado (personas naturales también emiten factura).
    societarias = [
        x
        for x in candidatos
        if re.search(r"\b(?:E\.?I\.?R\.?L\.?|S\.?A\.?C\.?|S\.?R\.?L\.?|S\.?A\.?)\b", x, re.I)
    ]
    valor = societarias[-1] if societarias else candidatos[0]
    if (
        re.fullmatch(r"(?:E\.?I\.?R\.?L\.?|S\.?A\.?C\.?|S\.?R\.?L\.?|S\.?A\.?)", valor, re.I)
        and len(candidatos) >= 2
    ):
        anterior = candidatos[candidatos.index(valor) - 1]
        valor = f"{anterior} {valor}"
    return valor[:300], " ".join(candidatos)[:300]


def _bloque_despues_de_etiqueta(
    lineas: list[str],
    etiqueta: str,
    *,
    detener: tuple[str, ...],
    max_lineas: int = 4,
) -> tuple[str, str] | None:
    etiqueta_norm = _sin_tildes(etiqueta).upper()
    for i, linea in enumerate(lineas):
        normal = _sin_tildes(linea).upper()
        pos = normal.find(etiqueta_norm)
        if pos < 0:
            continue
        partes: list[str] = []
        resto = linea[pos + len(etiqueta) :].strip(" :-\t")
        if resto:
            partes.append(resto)
        for siguiente in lineas[i + 1 : i + 1 + max_lineas]:
            norm_sig = _sin_tildes(siguiente).upper()
            if any(norm_sig.startswith(_sin_tildes(fin).upper()) for fin in detener):
                break
            if siguiente:
                partes.append(siguiente)
        valor = " ".join(partes).strip()
        valor = _recortar_razon(valor, quitar_etiqueta=False)
        if _razon_social_valida(valor):
            return valor[:300], " ".join(lineas[i : i + 1 + max_lineas])[:300]
    return None


def _parsear_factura_sunat(
    texto: str,
    rucs: list[str],
    campos: dict[str, dict[str, object]],
    fuente: str,
    factor: float,
) -> None:
    if len(rucs) < 2:
        return
    lineas = _lineas_limpias(texto)
    indice_factura = _indice_linea(lineas, r"FACTURA\s+ELECTRONICA")
    if indice_factura is None:
        return

    ruc_emisor, ruc_receptor = rucs[0], rucs[1]
    _poner_campo(
        campos,
        "ruc_emisor",
        ruc_emisor,
        min(0.96, 0.94 * factor),
        _contexto(texto, ruc_emisor),
        fuente,
    )
    _poner_campo(
        campos,
        "ruc_receptor",
        ruc_receptor,
        min(0.96, 0.94 * factor),
        _contexto(texto, ruc_receptor),
        fuente,
    )

    emisor = _razon_emisor_encabezado(lineas, indice_factura)
    if emisor:
        _poner_campo(
            campos,
            "razon_social_emisor",
            emisor[0],
            min(0.97, 0.95 * factor),
            emisor[1],
            fuente,
        )

    receptor = _bloque_despues_de_etiqueta(
        lineas,
        "SEÑOR(ES)",
        detener=("RUC", "DIRECCION DEL CLIENTE", "TIPO DE MONEDA", "OBSERVACION"),
        max_lineas=4,
    )
    if receptor:
        _poner_campo(
            campos,
            "razon_social_receptor",
            receptor[0],
            min(0.97, 0.95 * factor),
            receptor[1],
            fuente,
        )


def _parsear_facturalaya(
    texto: str,
    rucs: list[str],
    campos: dict[str, dict[str, object]],
    fuente: str,
    factor: float,
) -> None:
    if len(rucs) < 2:
        return
    lineas = _lineas_limpias(texto)
    ruc_emisor, ruc_receptor = rucs[0], rucs[1]
    _poner_campo(campos, "ruc_emisor", ruc_emisor, min(0.95, 0.93 * factor), _contexto(texto, ruc_emisor), fuente)
    _poner_campo(campos, "ruc_receptor", ruc_receptor, min(0.95, 0.93 * factor), _contexto(texto, ruc_receptor), fuente)

    # Facturalaya suele incluir "NOMBRE - RUC" en el encabezado.
    for linea in lineas:
        if ruc_emisor in re.sub(r"\D", "", linea):
            candidato = re.sub(r"[-–—]?\s*" + re.escape(ruc_emisor) + r"\s*$", "", linea).strip(" -:")
            if _razon_social_valida(candidato):
                _poner_campo(campos, "razon_social_emisor", candidato, min(0.96, 0.94 * factor), linea, fuente)
                break

    receptor = _bloque_despues_de_etiqueta(
        lineas,
        "RAZÓN SOCIAL",
        detener=("R.U.C", "RUC", "DIRECCION", "DIRECCIÓN", "FORMA DE PAGO"),
        max_lineas=3,
    )
    if receptor:
        _poner_campo(campos, "razon_social_receptor", receptor[0], min(0.97, 0.95 * factor), receptor[1], fuente)


def _parsear_factuhost(
    texto: str,
    rucs: list[str],
    campos: dict[str, dict[str, object]],
    fuente: str,
    factor: float,
) -> None:
    if len(rucs) < 2:
        return
    lineas = _lineas_limpias(texto)
    ruc_emisor, ruc_receptor = rucs[0], rucs[1]
    _poner_campo(campos, "ruc_emisor", ruc_emisor, min(0.96, 0.94 * factor), _contexto(texto, ruc_emisor), fuente)
    _poner_campo(campos, "ruc_receptor", ruc_receptor, min(0.96, 0.94 * factor), _contexto(texto, ruc_receptor), fuente)

    indice_ruc = next((i for i, linea in enumerate(lineas) if ruc_emisor in re.sub(r"\D", "", linea)), None)
    if indice_ruc is not None:
        emisor = _razon_emisor_encabezado(lineas, indice_ruc)
        if emisor:
            _poner_campo(campos, "razon_social_emisor", emisor[0], min(0.97, 0.95 * factor), emisor[1], fuente)

    receptor = _bloque_despues_de_etiqueta(
        lineas,
        "CLIENTE",
        detener=("RUC", "DIRECCION", "DIRECCIÓN", "MONEDA", "FECHA"),
        max_lineas=3,
    )
    if receptor:
        _poner_campo(campos, "razon_social_receptor", receptor[0], min(0.97, 0.95 * factor), receptor[1], fuente)


def _parsear_efact(
    texto: str,
    rucs: list[str],
    campos: dict[str, dict[str, object]],
    fuente: str,
    factor: float,
) -> None:
    if len(rucs) < 2:
        return
    lineas = _lineas_limpias(texto)
    ruc_emisor, ruc_receptor = rucs[0], rucs[1]
    _poner_campo(campos, "ruc_emisor", ruc_emisor, min(0.95, 0.93 * factor), _contexto(texto, ruc_emisor), fuente)
    _poner_campo(campos, "ruc_receptor", ruc_receptor, min(0.95, 0.93 * factor), _contexto(texto, ruc_receptor), fuente)

    indice_ruc = next((i for i, linea in enumerate(lineas) if ruc_emisor in re.sub(r"\D", "", linea)), None)
    if indice_ruc is not None:
        candidatos = [
            linea
            for linea in lineas[indice_ruc + 1 : indice_ruc + 6]
            if _razon_social_valida(linea)
            and not re.match(r"^(?:NRO\.?|F\d{3}\b)", _sin_tildes(linea), re.I)
        ]
        preferidos = [
            linea
            for linea in candidatos
            if re.search(r"\b(?:E\.?I\.?R\.?L\.?|S\.?A\.?C\.?|S\.?R\.?L\.?|S\.?A\.?)\b", linea, re.I)
        ]
        if preferidos or candidatos:
            razon = (preferidos or candidatos)[0]
            _poner_campo(campos, "razon_social_emisor", razon, min(0.94, 0.92 * factor), razon, fuente)

    receptor = _bloque_despues_de_etiqueta(
        lineas,
        "CLIENTE",
        detener=("RUC", "DIRECCION", "DIRECCIÓN", "CIUDAD", "FECHA"),
        max_lineas=4,
    )
    if receptor:
        _poner_campo(campos, "razon_social_receptor", receptor[0], min(0.95, 0.93 * factor), receptor[1], fuente)


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

    if receptor:
        nombre_receptor = _razon_social_etiquetada_para_ruc(
            texto,
            receptor,
            ETIQUETAS_RHE_NOMBRE_RECEPTOR,
        )
        if nombre_receptor:
            valor, evidencia = nombre_receptor
            campos["razon_social_receptor"] = CampoExtraido(
                valor,
                min(0.97, 0.95 * factor),
                evidencia,
            ).a_dict(fuente)


def _extraer_razones_vinculadas_a_ruc(
    texto: str,
    campos: dict[str, dict[str, object]],
    fuente: str,
    factor: float,
) -> None:
    for nombre_razon, nombre_ruc, etiquetas, permitir_linea_anterior in (
        ("razon_social_emisor", "ruc_emisor", ETIQUETAS_EMISOR, True),
        ("razon_social_receptor", "ruc_receptor", ETIQUETAS_RECEPTOR, False),
    ):
        if nombre_razon in campos:
            continue
        dato_ruc = campos.get(nombre_ruc)
        if not dato_ruc:
            continue
        ruc = str(dato_ruc["valor"])

        etiquetada = _razon_social_etiquetada_para_ruc(texto, ruc, etiquetas)
        if etiquetada:
            valor, evidencia = etiquetada
            campos[nombre_razon] = CampoExtraido(
                valor,
                min(0.97, 0.95 * factor),
                evidencia,
            ).a_dict(fuente)
            continue

        cercana = _razon_social_cercana_a_ruc(
            texto,
            ruc,
            permitir_linea_anterior=permitir_linea_anterior,
        )
        if cercana:
            valor, evidencia = cercana
            campos[nombre_razon] = CampoExtraido(
                valor,
                min(0.90, 0.88 * factor),
                evidencia,
            ).a_dict(fuente)


def _razon_social_etiquetada_para_ruc(
    texto: str,
    ruc: str,
    etiquetas: tuple[str, ...],
) -> tuple[str, str] | None:
    lineas = texto.splitlines()
    normalizadas = [_sin_tildes(linea).upper() for linea in lineas]
    for indice, linea_norm in enumerate(normalizadas):
        for etiqueta in etiquetas:
            etiqueta_norm = _sin_tildes(etiqueta).upper()
            pos = linea_norm.find(etiqueta_norm)
            if pos < 0:
                continue

            fin = min(len(lineas), indice + 2)
            bloque = "\n".join(lineas[indice:fin])
            if ruc not in re.sub(r"[\s.\-]", "", bloque):
                continue

            original = lineas[indice]
            prefijo = linea_norm[max(0, pos - 8) : pos]
            if "RUC" in prefijo:
                continue
            resto = original[pos + len(etiqueta) :].strip(" :-\t")
            candidato = _recortar_razon(resto, quitar_etiqueta=False)
            if not candidato and indice + 1 < fin:
                candidato = _recortar_razon(lineas[indice + 1], quitar_etiqueta=False)
            if _razon_social_valida(candidato):
                return candidato[:300], " ".join(bloque.split())[:300]
    return None


def _razon_social_cercana_a_ruc(
    texto: str,
    ruc: str,
    *,
    permitir_linea_anterior: bool,
) -> tuple[str, str] | None:
    lineas = texto.splitlines()
    for indice, linea in enumerate(lineas):
        linea_compacta = re.sub(r"[\s.\-]", "", linea)
        if ruc not in linea_compacta:
            continue

        antes = re.split(r"\bRUC\b", linea, maxsplit=1, flags=re.IGNORECASE)[0]
        antes = re.sub(r"[-–—:]?\s*" + re.escape(ruc) + r"\s*$", "", antes).strip()
        antes = _recortar_razon(antes)
        if _razon_social_valida(antes):
            return antes[:300], " ".join(linea.split())[:300]

        if permitir_linea_anterior and indice > 0:
            candidato = _recortar_razon(lineas[indice - 1])
            if _razon_social_valida(candidato) and not _parece_direccion(candidato):
                evidencia = " ".join(lineas[indice - 1 : indice + 1]).strip()
                return candidato[:300], evidencia[:300]
    return None


def _rucs_en_texto(texto: str) -> list[str]:
    encontrados: list[str] = []
    for coincidencia in RUC_FLEXIBLE.finditer(texto):
        ruc = re.sub(r"\D", "", coincidencia.group(1))
        if len(ruc) == 11 and ruc.startswith(("10", "20")) and ruc not in encontrados:
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


def _recortar_razon(valor: str, quitar_etiqueta: bool = True) -> str:
    candidato = " ".join(valor.split()).strip(" -:;,")
    candidato = re.split(
        r"\b(?:RUC|IDENTIFICAD[OA]\s+CON\s+RUC|DIRECCI[ÓO]N|DOMICILIO|FECHA|"
        r"MONEDA|TOTAL|POR\s+CONCEPTO|LA\s+SUMA)\b\s*[:\-]?",
        candidato,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    if quitar_etiqueta:
        candidato = re.sub(
            r"^(?:RAZ[ÓO]N\s+SOCIAL|PROVEEDOR|EMISOR|CLIENTE|ADQUIRIENTE|"
            r"SEÑOR\(ES\)|SEÑORES|SENORES|RECIB[IÍ]\s+DE|RECIBIDO\s+DE)\s*[:\-]?\s*",
            "",
            candidato,
            flags=re.IGNORECASE,
        )
    return " ".join(candidato.split()).strip(" -:;,")


def razon_social_confiable(valor: str) -> bool:
    return _razon_social_valida(valor)


def _razon_social_valida(valor: str) -> bool:
    if len(valor) < 3 or len(valor) > 300:
        return False
    if re.fullmatch(r"\d{11}", valor) or re.match(r"^\d{11}\b", valor):
        return False
    if not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", valor):
        return False
    normalizado = _sin_tildes(valor).upper().strip()
    if any(
        normalizado == invalido or normalizado.startswith(f"{invalido} ") for invalido in NO_RAZON
    ):
        return False
    if _parece_direccion(valor):
        return False
    return not ("HTTP://" in normalizado or "HTTPS://" in normalizado or "WWW." in normalizado)


def _parece_direccion(valor: str) -> bool:
    normalizado = _sin_tildes(valor).upper()
    indicadores = (
        "DIRECCION",
        "DOMICILIO",
        "AVENIDA",
        " AV.",
        "JR.",
        "JIRON",
        "CALLE",
        "CARRETERA",
        " PUESTO ",
        "PUESTO ",
        "PSTO",
        " MZ",
        "MZA",
        "MANZANA",
        " LOTE",
        " LT ",
        "URB.",
        "URBANIZACION",
        "DISTRITO",
        "PROVINCIA",
        "DEPARTAMENTO",
        "SECTOR",
        "AA.HH",
        "A.H.",
        "ASENTAMIENTO",
        " NRO.",
        " NRO ",
        " KM ",
        " S/N",
    )
    if any(indicador in f" {normalizado} " for indicador in indicadores):
        return True
    tokens = normalizado.split()
    numeros = sum(any(c.isdigit() for c in token) for token in tokens)
    return (
        len(tokens) >= 3
        and numeros >= 2
        and not re.search(
            r"\b(?:SAC|S\.A\.C\.|EIRL|E\.I\.R\.L\.|SRL|S\.R\.L\.|SA|S\.A\.)\b",
            normalizado,
        )
    )


def detectar_formato_documental(texto: str) -> str:
    normalizado = _sin_tildes(texto).upper()
    if "RECIBO POR HONORARIOS" in normalizado:
        return "RHE_SUNAT"
    if "FACTURALAYA" in normalizado:
        return "OSE_FACTURALAYA"
    if "FACTUHOST" in normalizado:
        return "OSE_FACTUHOST"
    if "EFACT" in normalizado or "WWW.EFACT.PE" in normalizado:
        return "OSE_EFACT"
    if "OSE" in normalizado or any(
        marca in normalizado for marca in ("NUBEFACT", "BIZLINK", "DIGIFLOW")
    ):
        return "OSE"
    if "PSE" in normalizado or "PROVEEDOR DE SERVICIOS ELECTRONICOS" in normalizado:
        return "PSE"
    if "TICKET" in normalizado or "BOLETA DE VENTA" in normalizado:
        return "TICKET"
    if (
        "GENERADA EN EL SISTEMA DE SUNAT" in normalizado
        or ("SENOR(ES)" in normalizado and "DIRECCION DEL CLIENTE" in normalizado)
    ):
        return "SUNAT_FACTURA"
    if "SUNAT" in normalizado or re.search(r"\bE\d{3}\s*[-–—]", normalizado):
        return "SUNAT"
    if "FACTURA ELECTRONICA" in normalizado or "FACTURA DE VENTA" in normalizado:
        return "FACTURA_GENERICA"
    return "DESCONOCIDO"


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
