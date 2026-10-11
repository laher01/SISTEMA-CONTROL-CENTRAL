"""GERENTE no debe consultar producción desglosada por usuarios o gestores."""

from fastapi.testclient import TestClient

from tests.conftest import AuthPrueba


def test_gerente_sin_acceso_a_produccion_detallada(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    auth_prueba.como_gerente()
    assert client.get("/api/v1/produccion/resumen").status_code == 403
    assert client.get("/api/v1/produccion/compras").status_code == 403


def test_administracion_conserva_acceso_produccion(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    auth_prueba.como_admin()
    assert client.get("/api/v1/produccion/resumen").status_code == 200
    assert client.get("/api/v1/produccion/compras").status_code == 200
