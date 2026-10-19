"""Regresión: un documento retirado nunca vuelve a entrar al motor OCR."""

import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.routes import documentos as documentos_routes
from app.models import Documento


def test_ocr_no_reprocesa_documento_retirado_ni_usa_cache(
    client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": ("fallido-ocr.pdf", b"%PDF-1.7 contenido de prueba")},
    )
    assert respuesta.status_code == 201, respuesta.text
    documento = session.get(Documento, uuid.UUID(respuesta.json()["id"]))
    assert documento is not None
    documento.deleted_at = datetime.now(UTC)
    session.flush()

    def prohibido(*args: object, **kwargs: object) -> None:
        raise AssertionError("No se debe consultar cache ni aplicar OCR a retirados")

    monkeypatch.setattr(documentos_routes, "procesar_con_cache", prohibido)
    monkeypatch.setattr(documentos_routes, "aplicar_automaticamente", prohibido)
    with pytest.raises(HTTPException) as error:
        documentos_routes._procesar_y_aplicar(session, object(), object(), date.today(), documento)
    assert error.value.status_code == 404


def test_ocr_revalida_retirada_durante_extraccion(
    client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": ("durante-ocr.pdf", b"%PDF-1.7 contenido de carrera")},
    )
    assert respuesta.status_code == 201, respuesta.text
    documento = session.get(Documento, uuid.UUID(respuesta.json()["id"]))
    assert documento is not None

    def extraccion_con_retirada(*args: object, **kwargs: object) -> dict[str, object]:
        documento.deleted_at = datetime.now(UTC)
        session.flush()
        return {"texto": "lectura provisional"}

    def sin_efecto(*args: object, **kwargs: object) -> None:
        return None

    def vinculacion_prohibida(*args: object, **kwargs: object) -> None:
        raise AssertionError("No aplicar relaciones a documento retirado")

    monkeypatch.setattr(documentos_routes, "procesar_con_cache", extraccion_con_retirada)
    monkeypatch.setattr(documentos_routes, "aplicar_perfiles_aprendidos", sin_efecto)
    monkeypatch.setattr(documentos_routes, "guardar_procesamiento", sin_efecto)
    monkeypatch.setattr(documentos_routes, "aplicar_automaticamente", vinculacion_prohibida)
    original = tmp_path / "original.pdf"
    original.write_bytes(b"%PDF-1.7 contenido de carrera")
    almacen = SimpleNamespace(ruta_absoluta=lambda _: original)
    settings = SimpleNamespace(storage_dir=tmp_path, max_extracted_chars=1000, max_ocr_pdf_pages=2)
    with pytest.raises(HTTPException) as error:
        documentos_routes._procesar_y_aplicar(session, settings, almacen, date.today(), documento)
    assert error.value.status_code == 404
