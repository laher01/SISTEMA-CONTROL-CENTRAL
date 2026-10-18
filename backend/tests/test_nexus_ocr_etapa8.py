"""Casos OCR: reglas de elegibilidad y privacidad de la referencia."""

import uuid
from types import SimpleNamespace

from app.services.casos_ocr import clave_diagnostico, motivo_pendiente
from app.services.reglas_ocr import validar_definicion, vista_previa_regla


def _documento(datos: dict[str, object]) -> SimpleNamespace:
    return SimpleNamespace(datos_extraidos=datos)


def test_crea_caso_para_fallo_existente() -> None:
    doc = _documento(
        {"automatizacion_documental": {"estado": "FALLIDO", "motivos": ["No hay serie"]}}
    )
    assert motivo_pendiente(doc) == "FALLIDO"


def test_no_crea_caso_para_documento_sin_error() -> None:
    doc = _documento({"automatizacion_documental": {"estado": "RELACIONADO"}})
    assert motivo_pendiente(doc) is None


def test_referencia_chat_no_expone_datos_privados() -> None:
    identificador = uuid.UUID("00000000-0000-0000-0000-000000000123")
    assert clave_diagnostico(identificador) == "OCR-00000000-0000-0000-0000-000000000123"


def test_regla_aprobable_tiene_gramatica_restringida() -> None:
    regla = validar_definicion(
        {"campo": "serie", "patron": "FACTURA ELECTRONICA", "valor": "F109"}
    )
    assert vista_previa_regla(regla, "FACTURA ELECTRONICA F109") == {
        "campo": "serie",
        "valor_propuesto": "F109",
    }
    assert vista_previa_regla(regla, "DOCUMENTO NO RELACIONADO") is None


def test_regla_rechaza_comandos_o_campos_no_fiscales() -> None:
    import pytest

    with pytest.raises(ValueError):
        validar_definicion(
            {"campo": "__import__", "patron": "FACTURA", "valor": "F109"}
        )
    with pytest.raises(ValueError):
        validar_definicion(
            {"campo": "serie", "patron": "FACTURA", "valor": "F109", "script": "DROP"}
        )
