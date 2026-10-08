from datetime import date

from fastapi.testclient import TestClient

from tests.conftest import AuthPrueba
from tests.xml import factura


def test_secretaria_resumen_por_receptor(client: TestClient, auth_prueba: AuthPrueba) -> None:
    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("comprobante.xml", factura(numero="F001-00000901"))},
    )
    assert subida.status_code == 201, subida.text
    parametros = {"desde": date(2025, 1, 1).isoformat(), "hasta": date(2027, 12, 31).isoformat()}
    auth_prueba.como_admin()
    respuesta = client.get("/api/v1/dashboard/secretaria-clientes", params=parametros)
    assert respuesta.status_code == 200, respuesta.text
    assert len(respuesta.json()) == 1
    assert respuesta.json()[0]["expedientes"] == 1


def test_secretaria_rechaza_periodo_invalido(client: TestClient, auth_prueba: AuthPrueba) -> None:
    auth_prueba.como_admin()
    respuesta = client.get(
        "/api/v1/dashboard/secretaria-clientes",
        params={"desde": "2026-10-10", "hasta": "2026-10-01"},
    )
    assert respuesta.status_code == 422
