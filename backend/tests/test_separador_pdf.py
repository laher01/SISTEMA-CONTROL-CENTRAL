import io

import pytest
from pypdf import PdfWriter

from app.services.procesamiento_documental import DocumentoNoProcesable
from app.services.separador_pdf import analizar_paquete, extraer_fragmento


def _paquete(paginas: list[str]) -> bytes:
    from pypdf.generic import (
        DecodedStreamObject,
        DictionaryObject,
        NameObject,
    )

    salida = PdfWriter()
    for contenido in paginas:
        hoja = salida.add_blank_page(width=595, height=842)
        fuente = DictionaryObject(
            {
                NameObject("/F1"): DictionaryObject(
                    {
                        NameObject("/Type"): NameObject("/Font"),
                        NameObject("/Subtype"): NameObject("/Type1"),
                        NameObject("/BaseFont"): NameObject("/Helvetica"),
                    }
                ),
            }
        )
        hoja[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): fuente})
        lineas = contenido.splitlines()
        operadores = ["BT /F1 10 Tf 20 780 Td"]
        for linea in lineas:
            operadores.append(f"({linea}) Tj 0 -20 Td")
        operadores.append("ET")
        stream = DecodedStreamObject()
        stream.set_data("\\n".join(operadores).encode("ascii"))
        hoja[NameObject("/Contents")] = salida._add_object(stream)
    memoria_final = io.BytesIO()
    salida.write(memoria_final)
    return memoria_final.getvalue()


def test_paquete_facturas_multiemisor_y_continuacion() -> None:
    pdf = _paquete(
        [
            "FACTURA ELECTRONICA\nRUC: 20612873446\nE001-9050",
            "Anexo o segunda pagina de la factura precedente",
            "FACTURA ELECTRONICA\nRUC: 20615266796\nE001-2272",
            "FACTURA ELECTRONICA\nRUC: 20612873446\nE001-9051",
        ]
    )
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
