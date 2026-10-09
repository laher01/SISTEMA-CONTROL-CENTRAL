from fastapi.testclient import TestClient

from tests.conftest import AuthPrueba


def test_inventario_tenants_exclusivo_superadmin(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    respuesta = client.get("/api/v1/configuracion/administraciones")
    assert respuesta.status_code == 403
    auth_prueba.como_admin()
    respuesta = client.get("/api/v1/configuracion/administraciones")
    assert respuesta.status_code == 403
    auth_prueba.como_superadmin()
    respuesta = client.get("/api/v1/configuracion/administraciones")
    assert respuesta.status_code == 200, respuesta.text
    registros = respuesta.json()
    assert len(registros) == 1
    assert registros[0]["nombre"] == "pruebas"
    assert registros[0]["usuarios"] == 1
    assert registros[0]["cuentas_activas"] == 1
    assert registros[0]["estado_suscripcion"] == "NO_IMPLEMENTADO"
