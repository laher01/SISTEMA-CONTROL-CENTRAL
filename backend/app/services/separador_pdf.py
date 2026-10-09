"""Separación conservadora de comprobantes concatenados.

Nunca adivina límites de documentos: páginas sin cabecera se asocian al
documento anterior y una primera página sin cabecera requiere revisión.
No altera el PDF fuente, ni crea registros durante el análisis.
"""

import io
import re
from dataclasses import dataclass

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from app.services.procesamiento_documental import DocumentoNoProcesable

TIPOS = (
    ("FACT", re.compile(r"FACTURA\s+ELECTR[OÓ]NICA", re.I)),
    ("RHE", re.compile(r"RECIBO\s+POR\s+HONORARIOS\s+ELECTR[OÓ]NICO", re.I)),
    ("GRE", re.compile(r"GU[IÍ]A\s+DE\s+REMISI[OÓ]N", re.I)),
    ("GRT", re.compile(r"GU[IÍ]A\s+DE\s+REMISI[OÓ]N\s+(?:DEL\s+)?TRANSPORTISTA", re.I)),
)
SERIE = re.compile(r"\b([A-Z][A-Z0-9]{3})\s*[-–—]\s*(\d{1,10})\b", re.I)
RUC = re.compile(r"\b(?:20|10)\d{9}\b")


@dataclass(frozen=True)
class Fragmento:
    inicio: int
    fin: int
    tipo: str
    serie: str
    correlativo: str
    ruc_emisor: str

    def descripcion(self) -> dict[str, object]:
        return {
            "pagina_inicio": self.inicio + 1,
            "pagina_fin": self.fin,
            "tipo": self.tipo,
            "serie": self.serie,
            "correlativo": self.correlativo,
            "ruc_emisor": self.ruc_emisor,
        }


def _cabecera(texto: str) -> tuple[str, str, str, str] | None:
    # La cabecera se busca en la parte superior, no en descripciones y notas.
    cabecera = texto[:2000]
    tipo = next((clave for clave, patron in reversed(TIPOS) if patron.search(cabecera)), None)
    serie = SERIE.search(cabecera)
    ruc = RUC.search(cabecera)
    if not tipo or not serie or not ruc:
        return None
    return tipo, serie.group(1).upper(), str(int(serie.group(2))), ruc.group(0)


def analizar_paquete(contenido: bytes, max_paginas: int = 200) -> list[Fragmento]:
    try:
        lector = PdfReader(io.BytesIO(contenido), strict=False)
        if lector.is_encrypted and lector.decrypt("") == 0:
            raise DocumentoNoProcesable("Paquete PDF protegido por contraseña")
        cantidad = len(lector.pages)
        if cantidad < 2:
            raise DocumentoNoProcesable("El paquete debe contener al menos dos páginas")
        if cantidad > max_paginas:
            raise DocumentoNoProcesable(f"El paquete supera el límite de {max_paginas} páginas")
        segmentos: list[Fragmento] = []
        for i, pagina in enumerate(lector.pages):
            texto = (pagina.extract_text() or "").strip()
            cabecera = _cabecera(texto)
            if cabecera is None:
                if not segmentos:
                    raise DocumentoNoProcesable(
                        "La primera página no contiene una cabecera fiscal identificable"
                    )
                # Página de continuación: no separarla sin evidencia documental.
                continue
            tipo, serie, correlativo, ruc = cabecera
            if segmentos:
                anterior = segmentos[-1]
                if (tipo, serie, correlativo, ruc) == (
                    anterior.tipo, anterior.serie, anterior.correlativo, anterior.ruc_emisor
                ):
                    continue
                segmentos[-1] = Fragmento(
                    anterior.inicio, i, anterior.tipo, anterior.serie,
                    anterior.correlativo, anterior.ruc_emisor
                )
            segmentos.append(Fragmento(i, cantidad, tipo, serie, correlativo, ruc))
        if len(segmentos) < 2:
            raise DocumentoNoProcesable(
                "No se identificaron al menos dos comprobantes distintos en el paquete"
            )
        return segmentos
    except (PdfReadError, OSError, ValueError, IndexError) as exc:
        raise DocumentoNoProcesable("No se pudo leer la estructura del paquete PDF") from exc


def extraer_fragmento(contenido: bytes, fragmento: Fragmento) -> bytes:
    lector = PdfReader(io.BytesIO(contenido), strict=False)
    escritor = PdfWriter()
    for indice in range(fragmento.inicio, fragmento.fin):
        escritor.add_page(lector.pages[indice])
    salida = io.BytesIO()
    escritor.write(salida)
    return salida.getvalue()
