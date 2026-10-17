"""Regresiones conversacionales NEXUS en la pantalla del gestor."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("mensaje", ["HOLA NEXUS", "QUE TAL COMO ESTA HOY", "¿Cómo estás?"])
def test_saludo_no_muestra_compras_ni_documentacion(client: TestClient, mensaje: str) -> None:
    respuesta = client.post(
        "/api/v1/nexus/chat",
        json={"mensaje": mensaje, "ruta": "/", "expediente_id": None},
    )
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["accion"] == "SALUDO"
    assert datos["motor"] == "CONVERSACIONAL_LOCAL"
    assert datos["seccion"] == "DASHBOARD"
    assert datos["fuentes"] == []
    assert "Puedo ayudarte" in datos["respuesta"]
    assert "Mes actual" not in datos["respuesta"]
    assert "motor conversacional externo" not in datos["respuesta"]
