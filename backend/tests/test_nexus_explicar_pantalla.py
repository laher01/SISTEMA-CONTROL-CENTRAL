"""La ayuda de pantalla debe ser comprensible aun sin motor conversacional externo."""

from fastapi.testclient import TestClient


def test_nexus_explica_dashboard_sin_prometer_vision_de_pantalla(client: TestClient) -> None:
    response = client.post(
        "/api/v1/nexus/chat",
        json={"mensaje": "que ves en mi pantalla", "ruta": "/", "expediente_id": None},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["accion"] == "EXPLICAR_PANTALLA"
    assert data["seccion"] == "DASHBOARD"
    assert data["motor"] == "CONTEXTUAL"
    assert "no veo directamente" in data["respuesta"]
    assert "motor conversacional externo" not in data["respuesta"]
    assert data["requiere_configuracion_externa"] is False


def test_nexus_explica_seccion_actual(client: TestClient) -> None:
    response = client.post(
        "/api/v1/nexus/chat",
        json={"mensaje": "qué está pasando en esta pantalla", "ruta": "/registros"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["seccion"] == "REGISTROS"
    assert "sección Registros" in data["respuesta"]
