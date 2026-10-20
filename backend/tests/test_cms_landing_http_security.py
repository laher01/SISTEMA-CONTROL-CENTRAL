"""Regresiones HTTP del CMS: autenticación, origen, permisos, versión y gate."""

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.deps import get_contexto_actual
from app.main import app
from tests.test_cms_landing_api import CONTENIDO

URL = "/api/v1/plataforma/cms"
ORIGEN = {"Origin": "https://testserver"}


def test_cms_http_requiere_sesion(client: TestClient) -> None:
    def denegar():
        raise HTTPException(status_code=401, detail="Sesión revocada")

    app.dependency_overrides[get_contexto_actual] = denegar
    assert client.get(URL).status_code == 401
    assert client.put(
        URL + "/borrador",
        headers=ORIGEN,
        json={"version": 0, "contenido": CONTENIDO},
    ).status_code == 401


def test_cms_http_no_autoriza_rol_tenant(client: TestClient) -> None:
    assert client.get(URL).status_code == 403
    assert client.post(
        URL + "/transicion",
        headers=ORIGEN,
        json={"version": 1, "destino": "publicado"},
    ).status_code == 403


def test_cms_http_superadmin_origen_y_version(client: TestClient, auth_prueba) -> None:
    auth_prueba.como_superadmin()
    solicitud = {"version": 0, "contenido": CONTENIDO}
    assert client.put(URL + "/borrador", json=solicitud).status_code == 403
    assert client.put(
        URL + "/borrador",
        headers={"Origin": "https://otro-dominio.example"},
        json=solicitud,
    ).status_code == 403
    creada = client.put(URL + "/borrador", headers=ORIGEN, json=solicitud)
    assert creada.status_code == 200
    assert creada.json()["version"] == 1
    repetida = client.put(URL + "/borrador", headers=ORIGEN, json=solicitud)
    assert repetida.status_code == 409
    consulta = client.get(URL)
    assert consulta.status_code == 200
    assert consulta.json()["version"] == 1


def test_cms_publico_no_filtra_snapshot_sin_activacion(client: TestClient) -> None:
    r = client.get(URL + "/publico")
    assert r.status_code == 200
    assert r.json() == {"disponible": False, "contenido": None}
