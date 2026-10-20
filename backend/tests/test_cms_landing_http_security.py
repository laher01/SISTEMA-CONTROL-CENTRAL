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
    respuesta = client.put(
        URL + "/borrador", headers=ORIGEN, json={"version": 0, "contenido": CONTENIDO}
    )
    assert respuesta.status_code == 401


def test_cms_http_no_autoriza_rol_tenant(client: TestClient) -> None:
    assert client.get(URL).status_code == 403
    respuesta = client.post(
        URL + "/transicion", headers=ORIGEN, json={"version": 1, "destino": "publicado"}
    )
    assert respuesta.status_code == 403


def test_cms_http_superadmin_origen_y_version(client: TestClient, auth_prueba) -> None:
    auth_prueba.como_superadmin()
    solicitud = {"version": 0, "contenido": CONTENIDO}
    assert client.put(URL + "/borrador", json=solicitud).status_code == 403
    externo = client.put(
        URL + "/borrador",
        headers={"Origin": "https://otro-dominio.example"},
        json=solicitud,
    )
    assert externo.status_code == 403
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


def test_cms_http_token_invalido_sin_override_devuelve_401(client: TestClient, settings) -> None:
    # El token no existe en la base de datos: probar dependencia real de cookie.
    app.dependency_overrides.pop(get_contexto_actual, None)
    client.cookies.set(settings.session_cookie_name, "token-inexistente-o-revocado")
    respuesta = client.get(URL)
    assert respuesta.status_code == 401
