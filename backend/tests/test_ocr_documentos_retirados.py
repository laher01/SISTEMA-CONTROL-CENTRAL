"""Regresión: un documento retirado nunca vuelve a entrar al motor OCR."""

import uuid
from datetime import UTC, date, datetime

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
