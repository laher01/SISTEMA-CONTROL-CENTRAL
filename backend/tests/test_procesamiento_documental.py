import io
import subprocess

import pytest
from pypdf import PdfWriter

from app.enums import TipoDocumento
from app.services import procesamiento_documental as pd


def pdf_vacio() -> bytes:
    salida = io.BytesIO()
    escritor = PdfWriter()
    escritor.add_blank_page(width=100, height=100)
    escritor.write(salida)
    return salida.getvalue()


def test_pdf_sin_capa_texto_solicita_ocr() -> None:
    resultado = pd.procesar(pdf_vacio(), 10_000)
    assert resultado.metodo == "TEXTO_PDF"
    assert resultado.paginas == 1
    assert resultado.texto == ""
    assert resultado.requiere_ocr is True


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
