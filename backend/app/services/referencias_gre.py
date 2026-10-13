"""Referencias fiscales explícitas en una GRE: no inferir por números sueltos.

Solo se consideran facturas indicadas como documentos relacionados; el RUC
junto a la referencia pertenece al EMISOR DE ESA FACTURA, que puede ser
distinto del emisor de la GRE.
"""

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class ReferenciaFacturaGRE:
    serie: str
    correlativo: str
    emisor_ruc: str | None
    receptor_ruc: str | None


def _normalizar(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto.upper()) if not unicodedata.combining(c)
    )


def extraer_referencias_factura_gre(texto: str) -> tuple[ReferenciaFacturaGRE, ...]:
    """Identificar referencias explícitas; conservar ambigüedades para revisión."""
    normal = _normalizar(texto)
    # La sección se reconoce explícitamente; nunca usar el correlativo propio de la guía.
    seccion = re.search(
        r"(?:DOCUMENTO(?:S)?\s+(?:RELACIONADO(?:S)?|REFERENCIADO(?:S)?)|"
        r"FACTURA\s+(?:RELACIONADA|REFERENCIADA))\s*[:\-]?",
        normal,
    )
    if seccion is None:
        return ()
    texto_refs = normal[seccion.end() : seccion.end() + 1600]
    patron = re.compile(
        r"FACTURA(?:\s+ELECTRONICA)?\s*(?:N[RO°º.]*|NUMERO|NO\.?|#)?\s*[:\-]?\s*"
        r"([FE][0-9]{3})\s*[-–—\s]\s*0*([0-9]{1,8})\b"
        r"(?:\s*[-–—,;:]?\s*RUC\s*(?:N[RO°º.]*|#)?\s*[:\-]?\s*([0-9]{11})\b)?",
    )
    destinatario = re.search(
        r"(?:DATOS\s+DEL\s+DESTINATARIO|DESTINATARIO|ADQUIRENTE|RECEPTOR)"
        r"[^\n]{0,250}?(?:REGISTRO\s+UNICO\s+DE\s+CONTRIBUYENTES|RUC)"
        r"\s*(?:N[RO°º.]*|#)?\s*[:\-]?\s*([0-9]{11})\b",
        normal,
    )
    receptor = destinatario.group(1) if destinatario else None
    referencias: dict[tuple[str, str], ReferenciaFacturaGRE] = {}
    for match in patron.finditer(texto_refs):
        serie = match.group(1)
        correlativo = str(int(match.group(2)))
        ruc = match.group(3)
        clave = (serie, correlativo)
        nueva = ReferenciaFacturaGRE(serie, correlativo, ruc, receptor)
        anterior = referencias.get(clave)
        if anterior is not None and anterior.emisor_ruc != nueva.emisor_ruc:
            # Dos RUC distintos para la misma factura: no es una referencia inequívoca.
            return ()
        referencias[clave] = nueva
    return tuple(referencias.values())
