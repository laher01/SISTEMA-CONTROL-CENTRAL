"""Extracción conservadora de un ítem de servicio desde recibo por honorarios."""

import re
import uuid
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.services.contabilidad_items_ubl import ItemUBL, _registrar_lineas
from app.services.extraccion_campos import extraer_campos

_CONCEPTO = re.compile(
    r"\b(?:por\s+concepto\s+de\s*:?|(?:concepto|descripci[oó]n del servicio)\s*:)\s*(.+?)"
    r"(?=\n\s*(?:inciso|fecha\s+de\s+emisi[oó]n|total\s+por\s+honorarios|"
    r"observaci[oó]n|retenci[oó]n|total\s+neto\s+recibido|\d{1,2}\s+de\s+"
    r"(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|"
    r"octubre|noviembre|diciembre)\b)|$)",
    re.IGNORECASE | re.DOTALL,
)


def extraer_item_rhe(texto: str) -> tuple[str, Decimal] | None:
    """Devuelve concepto y honorario bruto solo cuando ambos tienen evidencia clara."""
    if not re.search(r"\bRECIBO\s+POR\s+HONORARIOS\b", texto, re.I):
        return None
    concepto_match = _CONCEPTO.search(texto)
    if concepto_match is None:
        return None
    concepto = " ".join(concepto_match.group(1).split()).strip(" .:-")
    if len(concepto) < 3 or re.fullmatch(
        r"(?:de|del|la|el|y)(?: (?:de|del|la|el|y))*", concepto, re.I
    ):
        return None
    texto_fiscal = re.sub(r"RECIBO\s+POR\s+HONORARIOS", "RECIBO POR HONORARIOS", texto, flags=re.I)
    campos = extraer_campos(texto_fiscal, "TEXTO_PDF", 1.0)
    bruto = (campos or {}).get("campos", {})
    total = bruto.get("importe_total") if isinstance(bruto, dict) else None
    if not isinstance(total, dict) or not isinstance(total.get("valor"), str):
        return None
    try:
        importe = Decimal(total["valor"])
    except InvalidOperation:
        return None
    if not importe.is_finite() or importe <= 0:
        return None
    return concepto[:2000], importe


def registrar_item_rhe(
    session: Session,
    tenant_id: uuid.UUID,
    documento_id: uuid.UUID,
    texto: str,
) -> int:
    """Registra una línea de servicio por RHE; no inventa conceptos o importes."""
    extraido = extraer_item_rhe(texto)
    if extraido is None:
        return 0
    descripcion, importe = extraido
    return _registrar_lineas(
        session,
        tenant_id,
        documento_id,
        [ItemUBL(1, descripcion, Decimal(1), "SERVICIO", importe)],
    )
