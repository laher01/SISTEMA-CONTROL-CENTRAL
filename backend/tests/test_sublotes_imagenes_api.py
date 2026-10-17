"""Pruebas aisladas del endpoint de sublotes sin modificar datos productivos."""

import asyncio
import io
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile

from app.api.routes import documentos


class SesionFalsa:
    def __init__(self) -> None:
        self.reversiones = 0

    def rollback(self) -> None:
        self.reversiones += 1


def imagen_png() -> UploadFile:
    return UploadFile(
        filename="captura.png",
        file=io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"datos-prueba"),
    )


def ejecutar(archivos: list[UploadFile], sesion: SesionFalsa):
    return asyncio.run(
        documentos.subir_sublote_imagenes(
            session=sesion,
            settings=None,
            almacen=None,
            hoy=None,
            tenant_id=uuid.uuid4(),
            auth=None,
            archivos=archivos,
        )
    )


def test_sublote_rechaza_mas_de_diez(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_subir(**kwargs):
        pytest.fail("No debe registrar un sublote inválido")

    monkeypatch.setattr(documentos, "subir_documento", no_subir)
    with pytest.raises(HTTPException) as error:
        ejecutar([imagen_png() for _ in range(11)], SesionFalsa())
    assert error.value.status_code == 422


def test_sublote_continua_tras_duplicado(monkeypatch: pytest.MonkeyPatch) -> None:
    llamados = 0

    async def subir_simulado(**kwargs):
        nonlocal llamados
        llamados += 1
        if llamados == 1:
            raise HTTPException(409, {"duplicado": True, "mensaje": "Ya registrado"})
        return SimpleNamespace(id=uuid.uuid4())

    monkeypatch.setattr(documentos, "subir_documento", subir_simulado)
    sesion = SesionFalsa()
    resultado = ejecutar([imagen_png(), imagen_png()], sesion)
    assert resultado["total"] == 2
    assert resultado["procesados"] == 1
    assert resultado["duplicados"] == 1
    assert sesion.reversiones == 1


def test_conflicto_autorizacion_no_es_duplicado(monkeypatch: pytest.MonkeyPatch) -> None:
    async def denegar(**kwargs):
        raise HTTPException(409, {"codigo": "EMISOR_REQUIERE_AUTORIZACION"})

    monkeypatch.setattr(documentos, "subir_documento", denegar)
    resultado = ejecutar([imagen_png()], SesionFalsa())
    assert resultado["duplicados"] == 0
    assert resultado["errores"] == 1


def test_sublote_rechaza_archivo_no_imagen(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_subir(**kwargs):
        pytest.fail("Un archivo sin firma de imagen nunca debe llegar a ingesta")

    monkeypatch.setattr(documentos, "subir_documento", no_subir)
    archivo = UploadFile(filename="malicioso.png", file=io.BytesIO(b"%PDF-1.7"))
    resultado = ejecutar([archivo], SesionFalsa())
    assert resultado["procesados"] == 0
    assert resultado["errores"] == 1


@pytest.mark.parametrize("cantidad", [0, 11])
def test_sublote_limites_rechazan_sin_registrar(
    monkeypatch: pytest.MonkeyPatch, cantidad: int
) -> None:
    async def no_subir(**kwargs):
        pytest.fail("Un sublote inválido no debe registrar documentos")

    monkeypatch.setattr(documentos, "subir_documento", no_subir)
    with pytest.raises(HTTPException) as error:
        ejecutar([imagen_png() for _ in range(cantidad)], SesionFalsa())
    assert error.value.status_code == 422


def test_diez_imagenes_se_procesan_en_orden(monkeypatch: pytest.MonkeyPatch) -> None:
    llamados = 0

    async def subir_simulado(**kwargs):
        nonlocal llamados
        llamados += 1
        return SimpleNamespace(id=uuid.uuid4())

    monkeypatch.setattr(documentos, "subir_documento", subir_simulado)
    resultado = ejecutar([imagen_png() for _ in range(10)], SesionFalsa())
    assert resultado["total"] == 10
    assert resultado["procesados"] == 10
    assert [fila["indice"] for fila in resultado["resultados"]] == list(range(10))
    assert llamados == 10
