"""Identidad conservadora de cotizaciones: nunca asignar el RUC del cliente al emisor."""

import hashlib
import json
import re
import unicodedata

RUC = r"((?:10|20)\\d{9})"
EMISOR = re.compile(
    rf"\\b(?:RUC\\s+(?:DEL\\s+)?(?:EMISOR|PROVEEDOR)|"
    rf"(?:EMISOR|PROVEEDOR)\\s*RUC)\\s*[:#-]?\\s*{RUC}\\b",
    re.I,
)
CLIENTE = re.compile(
    rf"\\b(?:CLIENTE|RECEPTOR)\\s*(?:RUC)?\\s*[:#-]?\\s*{RUC}\\b|"
    rf"\\bRUC\\s+(?:DEL\\s+)?(?:CLIENTE|RECEPTOR)\\s*[:#-]?\\s*{RUC}\\b",
    re.I,
)


def identidad_cotizacion(texto: str, numero: str) -> dict[str, str | None]:
    """Genera huella solo con emisor y número inequívocos; si no, revisión."""
    plano = unicodedata.normalize("NFKD", texto)
    plano = "".join(c for c in plano if not unicodedata.combining(c))
    emisor = EMISOR.search(plano[:4000])
    cliente = CLIENTE.search(plano[:4000])
    proveedor_ruc = emisor.group(1) if emisor else None
    cliente_ruc = next((g for g in cliente.groups() if g), None) if cliente else None
    normalizado = re.sub(r"\\s+", "", numero).upper()
    if not proveedor_ruc or not normalizado or proveedor_ruc == cliente_ruc:
        return {
            "version": "COT-1",
            "emisor_ruc": proveedor_ruc,
            "cliente_ruc": cliente_ruc,
            "huella": None,
            "estado": "REVISION",
        }
    payload = json.dumps(
        ["COT-1", proveedor_ruc, normalizado],
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "version": "COT-1",
        "emisor_ruc": proveedor_ruc,
        "cliente_ruc": cliente_ruc,
        "huella": hashlib.sha256(payload).hexdigest(),
        "estado": "IDENTIFICADO",
    }
