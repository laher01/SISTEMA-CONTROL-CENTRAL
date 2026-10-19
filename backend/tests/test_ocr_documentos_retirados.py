"""Regresión: un documento retirado nunca vuelve a entrar al motor OCR."""

import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import Engine
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


def test_cache_ocr_aislado_por_tenant(tmp_path: Path) -> None:
    from app.services.cache_ocr import procesar_con_cache

    llamadas = 0

    def extraer() -> dict[str, object]:
        nonlocal llamadas
        llamadas += 1
        return {"texto": f"resultado-{llamadas}", "requiere_ocr": False}

    contenido = b"archivo de ejemplo del mismo hash"
    a = procesar_con_cache(contenido, "empresa-a", tmp_path, 1000, 2, extraer)
    b = procesar_con_cache(contenido, "empresa-b", tmp_path, 1000, 2, extraer)
    a_repetida = procesar_con_cache(contenido, "empresa-a", tmp_path, 1000, 2, extraer)
    assert llamadas == 2
    assert a == a_repetida
    assert a != b


def test_ocr_detecta_retirada_confirmada_por_otra_sesion(
    client: TestClient,
    session: Session,
    engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from sqlalchemy.orm import sessionmaker

    if engine.dialect.name == "sqlite":
        pytest.skip("La prueba de transacciones concurrentes requiere PostgreSQL")

    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": ("concurrente.pdf", b"%PDF-1.7 lectura simultanea")},
    )
    assert respuesta.status_code == 201, respuesta.text
    documento = session.get(Documento, uuid.UUID(respuesta.json()["id"]))
    assert documento is not None

    original = tmp_path / "archivo.pdf"
    original.write_bytes(b"%PDF-1.7 lectura simultanea")
    almacen = SimpleNamespace(ruta_absoluta=lambda _: original)
    settings = SimpleNamespace(storage_dir=tmp_path, max_extracted_chars=1000, max_ocr_pdf_pages=2)

    def extraer_y_retirar(*args: object, **kwargs: object) -> dict[str, object]:
        with sessionmaker(engine)() as otra_sesion:
            otro = otra_sesion.get(Documento, documento.id)
            assert otro is not None
            otro.deleted_at = datetime.now(UTC)
            otra_sesion.commit()
        return {"texto": "texto reconocido", "requiere_ocr": False}

    def sin_efecto(*args: object, **kwargs: object) -> None:
        return None

    def no_vincular(*args: object, **kwargs: object) -> None:
        raise AssertionError("No vincular después de retirada confirmada por MISD")

    monkeypatch.setattr(documentos_routes, "procesar_con_cache", extraer_y_retirar)
    monkeypatch.setattr(documentos_routes, "aplicar_perfiles_aprendidos", sin_efecto)
    monkeypatch.setattr(documentos_routes, "guardar_procesamiento", sin_efecto)
    monkeypatch.setattr(documentos_routes, "aplicar_automaticamente", no_vincular)
    with pytest.raises(HTTPException) as error:
        documentos_routes._procesar_y_aplicar(session, settings, almacen, date.today(), documento)
    assert error.value.status_code == 404


def test_lote_continua_si_misd_retiro_un_candidato(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    retirado = SimpleNamespace(id=uuid.uuid4(), deleted_at=datetime.now(UTC))
    siguiente = SimpleNamespace(id=uuid.uuid4(), deleted_at=None)
    procesados: list[uuid.UUID] = []

    class SesionLote:
        def scalars(self, _consulta: object) -> list[SimpleNamespace]:
            return [retirado, siguiente]

        def rollback(self) -> None:
            pass

        def get(self, _modelo: object, documento_id: uuid.UUID) -> SimpleNamespace:
            assert documento_id == retirado.id
            return retirado

        def refresh(self, _documento: SimpleNamespace) -> None:
            pass

        def commit(self) -> None:
            pass

    def procesar(
        _session: object,
        _settings: object,
        _almacen: object,
        _hoy: date,
        documento: SimpleNamespace,
        **_kwargs: object,
    ) -> SimpleNamespace:
        procesados.append(documento.id)
        if documento.id == retirado.id:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        return SimpleNamespace(relacionado=False, estado="REVISION_REQUERIDA")

    monkeypatch.setattr(documentos_routes, "_aplicar_ambito_documentos", lambda q, _auth: q)
    monkeypatch.setattr(documentos_routes, "_automatizacion_ya_evaluada", lambda _d: False)
    monkeypatch.setattr(documentos_routes, "_procesar_y_aplicar", procesar)
    resultado = documentos_routes.procesar_pendientes(
        SesionLote(), object(), object(), date.today(), uuid.uuid4(),
        object(), limit=50,
    )
    assert procesados == [retirado.id, siguiente.id]
    assert resultado.relacionados == 0
    assert resultado.revision_requerida == 1
    assert resultado.fallidos == 0


def test_lote_no_silencia_404_de_documento_vigente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vigente = SimpleNamespace(id=uuid.uuid4(), deleted_at=None)

    class SesionLote:
        def scalars(self, _consulta: object) -> list[SimpleNamespace]:
            return [vigente]

        def rollback(self) -> None:
            pass

        def get(self, _modelo: object, _id: uuid.UUID) -> SimpleNamespace:
            return vigente

        def refresh(self, _documento: SimpleNamespace) -> None:
            pass

    def fallo(*_args: object, **_kwargs: object) -> None:
        raise HTTPException(status_code=404, detail="Otra entidad inexistente")

    monkeypatch.setattr(documentos_routes, "_aplicar_ambito_documentos", lambda q, _auth: q)
    monkeypatch.setattr(documentos_routes, "_automatizacion_ya_evaluada", lambda _d: False)
    monkeypatch.setattr(documentos_routes, "_procesar_y_aplicar", fallo)
    with pytest.raises(HTTPException) as error:
        documentos_routes.procesar_pendientes(
            SesionLote(), object(), object(), date.today(), uuid.uuid4(),
            object(), limit=50,
        )
    assert error.value.status_code == 404
