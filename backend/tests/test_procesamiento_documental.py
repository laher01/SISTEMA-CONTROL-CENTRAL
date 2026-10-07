import io
import subprocess

import pytest
from pypdf import PdfWriter

from app.enums import TipoDocumento
from app.services import procesamiento_documental as pd
from app.services.extraccion_campos import extraer_campos


def pdf_vacio(paginas: int = 1) -> bytes:
    salida = io.BytesIO()
    escritor = PdfWriter()
    for _ in range(paginas):
        escritor.add_blank_page(width=100, height=100)
    escritor.write(salida)
    return salida.getvalue()


def test_pdf_sin_capa_texto_solicita_ocr_si_no_hay_motor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pd.shutil, "which", lambda _: None)
    resultado = pd.procesar(pdf_vacio(), 10_000)
    assert resultado.metodo == "TEXTO_PDF"
    assert resultado.paginas == 1
    assert resultado.texto == ""
    assert resultado.requiere_ocr is True


def test_pdf_escaneado_se_procesa_por_pagina(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pd.shutil, "which", lambda _: "/usr/bin/tesseract")
    monkeypatch.setattr(pd, "_idioma_disponible", lambda _: "spa")
    resultados = iter([("FACTURA ELECTRONICA F001-123", 0.91), ("TOTAL 2500.00", 0.81)])
    monkeypatch.setattr(pd, "_ejecutar_tesseract", lambda *_: next(resultados))
    resultado = pd.procesar(pdf_vacio(2), 10_000)
    assert resultado.metodo == "OCR_PDF"
    assert resultado.motor == "pdfium+tesseract"
    assert resultado.paginas == 2
    assert resultado.confianza == pytest.approx(0.86)
    assert "--- Página 1 ---" in resultado.texto
    assert "--- Página 2 ---" in resultado.texto
    assert resultado.sugerencia is not None
    assert resultado.sugerencia.tipo == TipoDocumento.FACT


def test_pdf_invalido_se_rechaza() -> None:
    with pytest.raises(pd.DocumentoNoProcesable, match="dañado"):
        pd.procesar(b"%PDF-esto no es un pdf", 10_000)


def test_sugerencia_es_evidencia_y_no_clasificacion_automatica() -> None:
    sugerencia = pd.sugerir_tipo("FACTURA ELECTRÓNICA F001-123")
    assert sugerencia is not None
    assert sugerencia.tipo == TipoDocumento.FACT
    assert sugerencia.confianza == pytest.approx(0.8)
    assert sugerencia.a_dict()["requiere_confirmacion"] is True


def test_ocr_imagen_registra_confianza(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pd.shutil, "which", lambda _: "/usr/bin/tesseract")

    def ejecutar(comando: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if "--list-langs" in comando:
            return subprocess.CompletedProcess(
                comando, 0, "List of available languages:\nspa\neng\n", ""
            )
        tsv = (
            "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
            "5\t1\t1\t1\t1\t1\t0\t0\t10\t10\t90\tCONSTANCIA\n"
            "5\t1\t1\t1\t1\t2\t11\t0\t10\t10\t80\tDE\n"
            "5\t1\t1\t1\t1\t3\t22\t0\t10\t10\t70\tPAGO\n"
        )
        return subprocess.CompletedProcess(comando, 0, tsv, "")

    monkeypatch.setattr(pd.subprocess, "run", ejecutar)
    resultado = pd.procesar(b"\x89PNG\r\n\x1a\ncontenido", 10_000)
    assert resultado.texto == "CONSTANCIA DE PAGO"
    assert resultado.confianza == pytest.approx(0.8)
    assert resultado.idioma == "spa+eng"
    assert resultado.sugerencia is not None
    assert resultado.sugerencia.tipo == TipoDocumento.VCHR


def test_extrae_campos_de_factura_con_trazabilidad() -> None:
    texto = """FACTURA ELECTRÓNICA F001-00000123
    RUC EMISOR: 20500000002 CLIENTE RUC: 20100000001
    Fecha de emisión: 17/09/2026 Moneda: SOLES TOTAL S/ 2,500.40"""
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert isinstance(campos, dict)
    assert campos["serie"]["valor"] == "F001"
    assert campos["correlativo"]["valor"] == "123"
    assert campos["ruc_emisor"]["valor"] == "20500000002"
    assert campos["ruc_receptor"]["valor"] == "20100000001"
    assert campos["fecha_emision"]["valor"] == "2026-09-17"
    assert campos["moneda"]["valor"] == "PEN"
    assert campos["importe_total"]["valor"] == "2500.40"
    assert campos["importe_total"]["fuente"] == "TEXTO_PDF"
    assert campos["importe_total"]["requiere_confirmacion"] is True


def test_extrae_voucher_ocr_sin_confundir_miles_y_decimales() -> None:
    texto = "OPERACIÓN EXITOSA Nro. operación: AB-908771 TOTAL PAGADO US$ 1.234,56"
    resultado = extraer_campos(texto, "OCR_IMAGEN", 0.8)
    assert resultado is not None
    campos = resultado["campos"]
    assert isinstance(campos, dict)
    assert campos["numero_operacion"]["valor"] == "AB-908771"
    assert campos["moneda"]["valor"] == "USD"
    assert campos["importe_total"]["valor"] == "1234.56"
    assert campos["numero_operacion"]["fuente"] == "OCR"
    assert campos["numero_operacion"]["confianza"] < 0.9


def test_fecha_imposible_no_se_publica() -> None:
    resultado = extraer_campos("FECHA DE EMISIÓN: 31/02/2026", "OCR_PDF", 0.9)
    assert resultado is None


def test_extrae_razones_sociales_de_factura() -> None:
    texto = """FACTURA ELECTRÓNICA F001-00000123
    PROVEEDOR: PESQUERA DEL PACIFICO S.A.C. RUC: 20500000002
    CLIENTE: NEXOMAR NEGOCIOS E.I.R.L. RUC: 20100000001
    Fecha de emisión: 17/09/2026 Moneda: SOLES TOTAL S/ 2,500.40"""
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert isinstance(campos, dict)
    assert campos["razon_social_emisor"]["valor"] == "PESQUERA DEL PACIFICO S.A.C."
    assert campos["razon_social_receptor"]["valor"] == "NEXOMAR NEGOCIOS E.I.R.L."


def test_extrae_partes_y_campos_de_recibo_por_honorarios() -> None:
    texto = """RECIBO POR HONORARIOS ELECTRÓNICO
    JUAN PEREZ LOPEZ
    RUC: 10456789012
    E001-00000038
    RECIBÍ DE: NEXOMAR NEGOCIOS E.I.R.L.
    IDENTIFICADO CON RUC NÚMERO: 20100000001
    FECHA DE EMISIÓN: 02/10/2026
    TOTAL POR HONORARIOS: S/ 350.00"""
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert isinstance(campos, dict)
    assert campos["serie"]["valor"] == "E001"
    assert campos["correlativo"]["valor"] == "38"
    assert campos["ruc_emisor"]["valor"] == "10456789012"
    assert campos["ruc_receptor"]["valor"] == "20100000001"
    assert campos["razon_social_emisor"]["valor"] == "JUAN PEREZ LOPEZ"
    assert campos["razon_social_receptor"]["valor"] == "NEXOMAR NEGOCIOS E.I.R.L."
    assert campos["fecha_emision"]["valor"] == "2026-10-02"
    assert campos["moneda"]["valor"] == "PEN"
    assert campos["importe_total"]["valor"] == "350.00"


def test_extrae_razon_social_junto_al_ruc_sin_etiqueta_proveedor() -> None:
    texto = """PESQUERA YATARUMI S.A.C.
    RUC: 20492560601
    FACTURA ELECTRÓNICA E001-00003321
    CLIENTE: COMERCIAL DEL MAR S.A.C.
    RUC RECEPTOR: 20600612876
    FECHA DE EMISIÓN: 02/10/2026
    TOTAL: S/ 1,250.00"""
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    campos = resultado["campos"]
    assert isinstance(campos, dict)
    assert campos["ruc_receptor"]["valor"] == "20600612876"
    assert campos["razon_social_receptor"]["valor"] == "COMERCIAL DEL MAR S.A.C."
