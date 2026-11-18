"""Resumen de observaciones tributarias, sin determinar procedencia fiscal."""

import re
from decimal import Decimal
from io import BytesIO

from pypdf import PdfReader

_FILA = re.compile(
    r"^(20\d{2}(?:0[1-9]|1[0-2]))\s+6\s+(\d{11})\s+.+?\s+"
    r"(-?\d[\d,]*\.\d{2})\s+(-?\d[\d,]*\.\d{2})\s+(-?\d[\d,]*\.\d{2})$"
)


def resumir_observaciones_sunat(contenido: bytes) -> dict[str, object]:
    """Extrae únicamente cifras observadas; requiere verificación independiente."""
    if len(contenido) > 20 * 1024 * 1024 or not contenido.startswith(b"%PDF-"):
        raise ValueError("PDF inválido o demasiado grande")
    lector = PdfReader(BytesIO(contenido))
    if lector.is_encrypted or len(lector.pages) > 100:
        raise ValueError("PDF protegido o demasiado extenso")
    periodos: dict[str, int] = {}
    proveedores: set[str] = set()
    neto = igv = total = Decimal("0.00")
    diferencias = 0
    filas = 0
    filas_no_leidas = 0
    en_anexo = False
    for pagina in lector.pages:
        texto = pagina.extract_text() or ""
        if "ANEXO 01.3" in texto:
            en_anexo = False
        if "ANEXO 01.2" in texto and "DETALLE DE COMPROBANTES" in texto:
            en_anexo = True
        if not en_anexo:
            continue
        for linea in texto.splitlines():
            coincidencia = _FILA.fullmatch(linea.strip())
            if coincidencia is None:
                if re.match(r"^20\d{4}\s+6\s+\d{11}\b", linea.strip()):
                    filas_no_leidas += 1
                continue
            periodo, proveedor, base, impuesto, importe = coincidencia.groups()
            b, i, t = (Decimal(v.replace(",", "")) for v in (base, impuesto, importe))
            neto += b
            igv += i
            total += t
            diferencias += int(b + i != t)
            filas += 1
            proveedores.add(proveedor)
            periodos[periodo] = periodos.get(periodo, 0) + 1
    if not filas:
        raise ValueError("No se identificó el anexo de comprobantes observados")
    return {
        "estado": "OBSERVADO_PENDIENTE_VERIFICACION",
        "filas_leidas": filas,
        "filas_no_leidas": filas_no_leidas,
        "proveedores": len(proveedores),
        "periodos": periodos,
        "base_observada": str(neto),
        "igv_observado": str(igv),
        "total_observado": str(total),
        "filas_con_diferencia_aritmetica": diferencias,
        "lectura_requiere_revision": True,
    }
