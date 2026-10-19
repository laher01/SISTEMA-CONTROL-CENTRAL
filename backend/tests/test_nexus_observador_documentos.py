"""NEXUS lee estados documentales existentes sin activar OCR ni mutar expedientes."""

from fastapi.testclient import TestClient


def test_nexus_observa_documentos_sin_reprocesar(client: TestClient) -> None:
    respuesta = client.post(
        "/api/v1/nexus/chat",
        json={
            "mensaje": "¿Cómo van mis documentos?",
            "ruta": "/documentos",
            "expediente_id": None,
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["accion"] == "RESUMEN_DOCUMENTOS"
    assert datos["motor"] == "ESPECIALISTA_DOCUMENTOS"
    assert datos["seccion"] == "DOCUMENTOS"
    assert datos["llm_usado"] is False
    assert datos["fuentes"] == []
    assert "no he reprocesado ni cambiado archivos" in datos["respuesta"]
    assert "documentos_por_estado" in datos["datos"]


def test_nexus_no_inventa_documentos_al_consultar_vacio(client: TestClient) -> None:
    respuesta = client.post(
        "/api/v1/nexus/chat",
        json={
            "mensaje": "¿Qué documentos tengo?",
            "ruta": "/documentos",
            "expediente_id": None,
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["accion"] == "RESUMEN_DOCUMENTOS"
