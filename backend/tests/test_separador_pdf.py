import io

import pytest
from pypdf import PdfWriter

from app.services.procesamiento_documental import DocumentoNoProcesable
from app.services.separador_pdf import analizar_paquete, extraer_fragmento


def _paquete(paginas: list[str]) -> bytes:
    # Pruebas de división sin redes ni datos privados: PdfWriter añade
    # anotaciones de texto como contenido de páginas mediante reportlab.
    from reportlab.pdfgen import canvas

    salida = PdfWriter()
    for contenido in paginas:
        memoria = io.BytesIO()
        hoja = canvas.Canvas(memoria)
        for indice, linea in enumerate(contenido.splitlines()):
            hoja.drawString(20, 780 - 20 * indice, linea)
        hoja.save()
        memoria.seek(0)
        from pypdf import PdfReader

        salida.add_page(PdfReader(memoria).pages[0])
    memoria_final = io.BytesIO()
    salida.write(memoria_final)
    return memoria_final.getvalue()


def test_paquete_facturas_multiemisor_y_continuacion() -> None:
    pdf = _paquete([
        "FACTURA ELECTRONICA\nRUC: 20612873446\nE001-9050",
        "Anexo o segunda pagina de la factura precedente",
        "FACTURA ELECTRONICA\nRUC: 20615266796\nE001-2272",
        "FACTURA ELECTRONICA\nRUC: 20612873446\nE001-9051",
    ])
    partes = analizar_paquete(pdf)
    assert [(p.inicio, p.fin, p.serie, p.correlativo) for p in partes] == [
        (0, 2, "E001", "9050"),
        (2, 3, "E001", "2272"),
        (3, 4, "E001", "9051"),
    ]
    from pypdf import PdfReader

    assert len(PdfReader(io.BytesIO(extraer_fragmento(pdf, partes[0]))).pages) == 2


def test_paquete_incierto_no_se_divide() -> None:
    pdf = _paquete(["Anexo sin cabecera", "FACTURA ELECTRONICA\nRUC: 20612873446\nE001-9050"])
    with pytest.raises(DocumentoNoProcesable):
        analizar_paquete(pdf)


def test_paquete_una_sola_factura_no_se_fragmenta() -> None:
    pdf = _paquete(["FACTURA ELECTRONICA\nRUC: 20612873446\nE001-9050", "Segunda pagina"])
    with pytest.raises(DocumentoNoProcesable):
        analizar_paquete(pdf)
