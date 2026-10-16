"""Pruebas de resiliencia del motor conversacional NEXUS 2.0."""

import urllib.error

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.services import nexus as nexus_service


def test_nexus_llm_timeout_usa_fallback_contextual(
    client: TestClient,
    settings: Settings,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "nexus_llm_url", "https://llm.example.test/chat")

    def proveedor_no_disponible(*args, **kwargs):
        raise urllib.error.URLError("timeout simulado")

    monkeypatch.setattr(nexus_service, "_http_json", proveedor_no_disponible)

    respuesta = client.post(
        "/api/v1/nexus/chat",
        json={
            "mensaje": "Explícame el contexto operativo de esta pantalla",
            "ruta": "/registros",
            "expediente_id": None,
        },
    )

    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["motor"] == "CONTEXTUAL"
    assert datos["accion"] == "CONTEXTO_NEXUS"
    assert datos["llm_usado"] is False
    assert datos["seccion"] == "REGISTROS"
    assert "timeout simulado" not in datos["respuesta"]


def test_nexus_llm_respuesta_sin_texto_usa_fallback(
    client: TestClient,
    settings: Settings,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "nexus_llm_url", "https://llm.example.test/chat")

    def proveedor_sin_contenido(*args, **kwargs):
        return {"choices": [{"message": {"content": ""}}]}

    monkeypatch.setattr(nexus_service, "_http_json", proveedor_sin_contenido)

    respuesta = client.post(
        "/api/v1/nexus/chat",
        json={
            "mensaje": "Explícame el contexto operativo de esta pantalla",
            "ruta": "/empresas",
            "expediente_id": None,
        },
    )

    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["motor"] == "CONTEXTUAL"
    assert datos["llm_usado"] is False
    assert datos["seccion"] == "EMPRESAS"
    assert "El motor conversacional externo todavía no está configurado" not in datos["respuesta"]
