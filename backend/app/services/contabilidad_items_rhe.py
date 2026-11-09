"""Extracción conservadora de un ítem de servicio desde recibo por honorarios."""

import hashlib
import re
import uuid
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.item_models import LineaComprobanteItem, ProductoItem
from app.services.contabilidad_items_rules import sugerir_categoria, texto_normalizado
from app.services.extraccion_campos import extraer_campos

_CONCEPTO = re.compile(
    r"\bpor\s+concepto\s+de\s*:?\s*(.+?)"
    r"(?=\n\s*(?:inciso|fecha\s+de\s+emisi[oó]n|total\s+por\s+honorarios|"
    r"retenci[oó]n|total\s+neto\s+recibido|\d{1,2}\s+de\s+"
    r"(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|"
    r"octubre|noviembre|diciembre)\b)|$)",
    re.IGNORECASE | re.DOTALL,
)


def extraer_item_rhe(texto: str) -> tuple[str, Decimal] | None:
    """Devuelve concepto y honorario bruto solo cuando ambos tienen evidencia clara."""
    if "RECIBO POR HONORARIOS" not in texto.upper():
        return None
    concepto_match = _CONCEPTO.search(texto)
    if concepto_match is None:
        return None
    concepto = " ".join(concepto_match.group(1).split()).strip(" .:-")
    if len(concepto) < 3:
        return None
    campos = extraer_campos(texto, "TEXTO_PDF", 1.0)
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
    existente = session.scalar(
        select(LineaComprobanteItem.id)
        .where(
            LineaComprobanteItem.tenant_id == tenant_id,
            LineaComprobanteItem.documento_id == documento_id,
        )
        .limit(1)
    )
    if existente is not None:
        return 0
    unidad = "SERVICIO"
    clave = hashlib.sha256(f"{texto_normalizado(descripcion)}|{unidad}".encode()).hexdigest()
    producto = session.scalar(
        select(ProductoItem).where(
            ProductoItem.tenant_id == tenant_id,
            ProductoItem.clave_catalogo == clave,
        )
    )
    if producto is None:
        producto = ProductoItem(
            tenant_id=tenant_id,
            clave_catalogo=clave,
            descripcion=descripcion,
            categoria=sugerir_categoria(descripcion),
            unidad_base=unidad,
            clasificacion_confirmada=False,
            activo=True,
        )
        session.add(producto)
        session.flush()
    session.add(
        LineaComprobanteItem(
            tenant_id=tenant_id,
            documento_id=documento_id,
            producto_id=producto.id,
            numero_linea=1,
            descripcion_original=descripcion,
            cantidad=Decimal("1"),
            unidad=unidad,
            importe_linea=importe,
        )
    )
    return 1
