import io
from collections.abc import Iterable
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from app.models import Documento
from app.storage import AlmacenLocal

ORDEN_DOCUMENTOS = {
    "FACT": 0,
    "RHE": 0,
    "GRR": 1,
    "GRT": 2,
    "VCHR": 3,
    "COT": 4,
    "OC": 5,
    "REQ": 6,
}


def pdf_con_documentos(
    documentos: Iterable[Documento],
    almacen: AlmacenLocal,
    titulo: str,
) -> tuple[PdfWriter, int, int]:
    """Produce PDF legible con imagenes, PDFs y originales embebidos.

    El manifiesto de portada identifica los originales. Archivos que no son
    renderizables se incluyen como adjuntos, nunca se descartan.
    """
    ordenados = sorted(
        documentos,
        key=lambda d: (ORDEN_DOCUMENTOS.get(str(d.tipo_documento), 9), d.created_at, str(d.id)),
    )
    if not ordenados:
        raise ValueError("El expediente no contiene documentos")
    if len(ordenados) > 100 or sum(d.tamano_bytes for d in ordenados) > 100 * 1024 * 1024:
        raise ValueError("El expediente excede el limite del PDF consolidado")

    writer = PdfWriter()
    portada = Image.new("RGB", (1240, 1754), "white")
    lapiz = ImageDraw.Draw(portada)
    lapiz.text((80, 70), "FACT CENTRAL - EXPEDIENTE DIGITAL", fill="black")
    lapiz.text((80, 125), titulo[:100], fill="black")
    lapiz.text((80, 170), "Originales incluidos como adjuntos dentro de este PDF.", fill="black")
    y = 230
    for numero, documento in enumerate(ordenados, start=1):
        etiqueta = f"{numero:03d} {documento.tipo_documento or 'OTRO'} {documento.nombre_original}"
        lapiz.text((80, y), etiqueta[:135], fill="black")
        y += 27
        if y > 1640:
            break
    buffer = io.BytesIO()
    portada.save(buffer, format="PDF")
    writer.append(io.BytesIO(buffer.getvalue()))

    visibles = 0
    adjuntos = 0
    for numero, doc in enumerate(ordenados, start=1):
        contenido = Path(almacen.ruta_absoluta(doc.ruta_storage)).read_bytes()
        extension = Path(doc.nombre_original).suffix.lower()
        es_pdf = contenido[:5] == b"%PDF-"
        es_imagen = extension in (".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff")
        try:
            if es_pdf:
                writer.append(io.BytesIO(contenido))
                visibles += 1
            elif es_imagen:
                with Image.open(io.BytesIO(contenido)) as imagen:
                    if imagen.width * imagen.height > 30_000_000:
                        raise ValueError("Imagen demasiado grande")
                    rgb = ImageOps.exif_transpose(imagen).convert("RGB")
                    paginas = io.BytesIO()
                    rgb.save(paginas, format="PDF")
                    writer.append(io.BytesIO(paginas.getvalue()))
                    visibles += 1
        except (PdfReadError, OSError, UnidentifiedImageError, ValueError) as exc:
            raise ValueError(f"No se pudo representar el archivo: {doc.nombre_original}") from exc
        nombre_adjunto = f"{numero:03d}-{doc.id}{extension if extension else '.bin'}"
        writer.add_attachment(filename=nombre_adjunto, data=contenido)
        adjuntos += 1
    return writer, visibles, adjuntos
