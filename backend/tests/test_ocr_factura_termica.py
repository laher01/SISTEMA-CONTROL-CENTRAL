import io

import pytest
from pypdf import PdfWriter

from app.enums import TipoDocumento
from app.services import procesamiento_documental as pd
from app.services.extraccion_campos import extraer_campos
from app.services.procesamiento_documental import (
    ResultadoProcesamiento,
    _leer_tsv,
    _requiere_lectura_auxiliar,
    sugerir_tipo,
)


def test_ticket_termico_ocr_conserva_lineas_y_montos():
    # Valores sintéticos: nunca incluir datos privados del comprobante original en Git.
    filas = [
        ("RUC", "20600000001", 1),
        ("FACTURA", "ELECTRONICA", 2),
        ("Emisión", "21/11/2026", 3),
        ("Documento", "20600000002", 4),
        ("Op.", "Gravadas:", 5),
        ("S/", "52.54", 6),
        ("I.G.V", "S/", 7),
        ("9.46", "", 8),
        ("Total:", "S/", 9),
        ("62.00", "", 10),
    ]
    cabecera = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tconf\ttext\n"
    tsv = cabecera + "".join(
        f"5\t1\t1\t1\t{linea}\t{indice}\t94\t{palabra}\n"
        for uno, dos, linea in filas
        for indice, palabra in enumerate((uno, dos), start=1)
        if palabra
    )
    texto, confianza = _leer_tsv(tsv, 10000)
    assert "FACTURA ELECTRONICA\n" in texto
    assert "Total: S/\n62.00" in texto
    assert confianza == 0.94
    assert sugerir_tipo(texto).tipo == TipoDocumento.FACT


def test_ticket_sin_serie_no_acepta_identidad_inventada():
    texto = (
        "DULCE COMERCIAL\nRUC 20600000001\nFACTURA ELECTRONICA\n"
        "F F O L - OOOI36\nEmisión : 21/11/2026 20:53:35\n"
        "Documento: 20600000002\nTotal: S/ 62.00\nYAPE S/ 62.00"
    )
    assert _requiere_lectura_auxiliar(texto)
    campos = extraer_campos(texto, "OCR_PDF", 0.88)["campos"]
    assert campos["importe_total"]["valor"] == "62.00"
    assert "serie" not in campos
    assert "correlativo" not in campos


def test_cabecera_degradada_solo_sugiere_tipo():
    sugerencia = sugerir_tipo("FACTURA ELEC RONT\nTOTAL S/ 62.00")
    assert sugerencia.tipo == TipoDocumento.FACT
    assert sugerencia.confianza < 0.8


def test_con_serie_clara_no_repite_ocr():
    assert not _requiere_lectura_auxiliar("FACTURA ELECTRONICA\nF001-000123\nTotal S/ 62.00")


def test_lectura_auxiliar_no_modifica_campos_fiscales():
    resultado = ResultadoProcesamiento(
        texto="FACTURA ELECTRONICA\nRUC 20600000001\nTotal S/ 62.00",
        metodo="OCR_PDF",
        motor="tesseract",
        paginas=1,
        confianza=0.8,
        texto_ocr_revision="FFOL - 000136",
    ).a_dict()
    assert resultado["ocr_revision"]["requiere_confirmacion"] is True
    assert "serie" not in resultado["extraccion_estructurada"]["campos"]


def test_pdf_termico_dispara_ocr_auxiliar_sin_autocompletar_identidad(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    salida = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=130, height=380)
    writer.write(salida)
    monkeypatch.setattr(pd.shutil, "which", lambda _: "/usr/bin/tesseract")
    monkeypatch.setattr(pd, "_idioma_disponible", lambda _: "spa")
    llamadas: list[int | None] = []

    def ocr(_exe: str, _ruta: object, _idioma: str, _limite: int, psm: int | None = None):
        llamadas.append(psm)
        if psm == 6:
            return "FFOL - 000136", 0.50
        return "FACTURA ELECTRONICA\nRUC 20600000001\nTotal: S/ 62.00", 0.91

    monkeypatch.setattr(pd, "_ejecutar_tesseract", ocr)
    resultado = pd._procesar_pdf_escaneado(salida.getvalue(), 10000, 5, [""])
    datos = resultado.a_dict()
    assert llamadas == [None, 6]
    assert datos["ocr_revision"]["requiere_confirmacion"] is True
    assert "FFOL" in datos["ocr_revision"]["texto"]
    assert "serie" not in datos["extraccion_estructurada"]["campos"]


def test_pdf_con_serie_clara_omite_ocr_auxiliar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    salida = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=130, height=380)
    writer.write(salida)
    monkeypatch.setattr(pd.shutil, "which", lambda _: "/usr/bin/tesseract")
    monkeypatch.setattr(pd, "_idioma_disponible", lambda _: "spa")
    llamadas: list[int | None] = []

    def ocr(_exe: str, _ruta: object, _idioma: str, _limite: int, psm: int | None = None):
        llamadas.append(psm)
        return "FACTURA ELECTRONICA\nF001-000123\nTotal: S/ 62.00", 0.91

    monkeypatch.setattr(pd, "_ejecutar_tesseract", ocr)
    resultado = pd._procesar_pdf_escaneado(salida.getvalue(), 10000, 5, [""])
    assert llamadas == [None]
    assert "ocr_revision" not in resultado.a_dict()


def test_cabecera_electro_truncada_con_evidencia_fiscal_requiere_revision() -> None:
    # Representa la transcripción OCR real con RUC ficticio; no publica el ticket.
    texto = (
        "COMERCIO SINTETICO\nRUC 20999999991\nFACTURA ELECTRO\n"
        "FFOL = 000138\nEmisión: 21/11/2026\n"
        "Documento : 20999999992\nTotal: S/ 62.00"
    )
    sugerencia = sugerir_tipo(texto)
    assert sugerencia is not None
    assert sugerencia.tipo == TipoDocumento.FACT
    assert sugerencia.confianza < 0.8
    assert _requiere_lectura_auxiliar(texto)
    campos = extraer_campos(texto, "OCR_PDF", 0.86)["campos"]
    assert "serie" not in campos
    assert "correlativo" not in campos


def test_electro_sin_evidencia_fiscal_no_es_factura() -> None:
    assert sugerir_tipo("FACTURA ELECTRO\nPRODUCTOS ELECTRODOMESTICOS") is None
    assert not _requiere_lectura_auxiliar("FACTURA ELECTRO\nPRODUCTOS ELECTRODOMESTICOS")


def test_cabecera_electro_con_ruc_emisor_ilegible_en_pdf_real() -> None:
    # Simula texto de la rasterización PDF a 216 dpi, con RUC emisor dañado.
    texto = (
        "COMERCIO PRUEBA\nRG er O20\nFACTURA ELECTRO\n"
        "FFO1 - PESA\nEmisión : 21/11/2026 20:53:35\n"
        "Documento : 20999999992\nTotal: S/ 62.00"
    )
    tipo = sugerir_tipo(texto)
    assert tipo is not None
    assert tipo.tipo == TipoDocumento.FACT
    assert tipo.confianza < 0.7
    assert _requiere_lectura_auxiliar(texto)
    campos = extraer_campos(texto, "OCR_PDF", 0.76)["campos"]
    assert "serie" not in campos
    assert "ruc_emisor" not in campos


def test_cabecera_electro_sin_fecha_no_confunde_comprobante() -> None:
    texto = "FACTURA ELECTRO\nDocumento: 20999999992\nTotal: S/ 62.00"
    assert sugerir_tipo(texto) is None
