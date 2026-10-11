"""El estado OAuth es informativo y exclusivo de Administración."""

from fastapi.testclient import TestClient

from tests.conftest import AuthPrueba


def test_estado_proveedores_no_revela_credenciales(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    auth_prueba.como_admin()
    respuesta = client.get("/api/v1/correo/estado-proveedores")
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert set(datos) == {"google_configurado", "microsoft_configurado"}
    assert all(isinstance(valor, bool) for valor in datos.values())
    auth_prueba.como_gerente()
    assert client.get("/api/v1/correo/estado-proveedores").status_code == 403
