"""Casos OCR: reglas de elegibilidad y privacidad de la referencia."""

import uuid
from types import SimpleNamespace

from app.services.casos_ocr import clave_diagnostico, motivo_pendiente


def _documento(datos: dict[str, object]) -> SimpleNamespace:
    return SimpleNamespace(datos_extraidos=datos)


def test_crea_caso_para_fallo_existente() -> None:
    doc = _documento(
        {"automatizacion_documental": {"estado": "FALLIDO", "motivos": ["No hay serie"]}}
    )
    assert motivo_pendiente(doc) == "No hay serie"


def test_no_crea_caso_para_documento_sin_error() -> None:
    doc = _documento({"automatizacion_documental": {"estado": "RELACIONADO"}})
    assert motivo_pendiente(doc) is None


def test_referencia_chat_no_expone_datos_privados() -> None:
    identificador = uuid.UUID("00000000-0000-0000-0000-000000000123")
    assert clave_diagnostico(identificador) == "OCR-00000000-0000-0000-0000-000000000123"
