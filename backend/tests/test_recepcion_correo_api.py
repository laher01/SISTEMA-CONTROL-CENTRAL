"""Control de acceso de buzones y remitentes antes de activar OAuth."""

from fastapi.testclient import TestClient

from tests.conftest import AuthPrueba


def test_usuario_no_administra_buzones(client: TestClient) -> None:
    respuesta = client.get("/api/v1/recepcion-correo/buzones")
    assert respuesta.status_code == 403
    respuesta = client.post(
        "/api/v1/recepcion-correo/buzones",
        json={"direccion": "facturas@example.com", "proveedor": "GMAIL"},
    )
    assert respuesta.status_code == 403


def test_usuario_no_registra_remitente(client: TestClient) -> None:
    respuesta = client.post(
        "/api/v1/recepcion-correo/remitentes",
        json={"direccion": "proveedor@example.com"},
    )
    assert respuesta.status_code == 403


def test_administrador_no_usurpa_buzon_responsable(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    auth_prueba.como_admin()
    respuesta = client.post(
        "/api/v1/recepcion-correo/buzones",
        json={"direccion": "facturas@example.com", "proveedor": "OUTLOOK"},
    )
    assert respuesta.status_code == 403
