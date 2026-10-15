"""El PDF ordenado empieza en el comprobante, sin portada adicional."""

import io
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from pypdf import PdfReader, PdfWriter

from app.services.pdf_consolidado import pdf_con_documentos


def test_pdf_ordenado_no_agrega_hoja_resumen(tmp_path):
    fuente = PdfWriter()
    fuente.add_blank_page(width=595, height=842)
    original = io.BytesIO()
    fuente.write(original)
    ruta = tmp_path / "factura.pdf"
    ruta.write_bytes(original.getvalue())
    documento = SimpleNamespace(
        tipo_documento="FACT",
        created_at=datetime(2026, 10, 14, tzinfo=UTC),
        id=uuid.uuid4(),
        nombre_original="factura.pdf",
        tamano_bytes=ruta.stat().st_size,
        ruta_storage="factura.pdf",
    )
    almacen = SimpleNamespace(ruta_absoluta=lambda _: ruta)

    writer, visibles, adjuntos = pdf_con_documentos(
        [documento], almacen, "FACT E001-1532"
    )
    salida = io.BytesIO()
    writer.write(salida)
    lector = PdfReader(io.BytesIO(salida.getvalue()))
    assert len(lector.pages) == 1
    assert visibles == 1
    assert adjuntos == 1
    assert len(lector.attachments) == 1
