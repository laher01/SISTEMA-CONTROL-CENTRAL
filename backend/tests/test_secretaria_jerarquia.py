"""Pruebas de regresión del alcance documental de Secretaría."""

from datetime import date
from uuid import uuid4

from fastapi.testclient import TestClient

from tests.conftest import AuthPrueba
from tests.xml import factura


def test_secretaria_jerarquia_no_altera_resumen_y_filtra(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("factura_secretaria.xml", factura(numero="F001-00000977"))},
    )
    assert subida.status_code == 201, subida.text
    auth_prueba.como_admin()
    periodo = {"desde": date(2025, 1, 1).isoformat(), "hasta": date(2027, 12, 31).isoformat()}
    respuesta = client.get("/api/v1/dashboard/secretaria-expedientes", params=periodo)
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["total_expedientes"] >= 1
    assert all(
        "responsable" in fila
        and "responsable_codigo" in fila
        and "usuario" in fila
        and "gestor" in fila
        for fila in datos["filas"]
    )
    for filtro in ("responsable_id", "usuario_id", "gestor_id"):
        filtrada = client.get(
            "/api/v1/dashboard/secretaria-expedientes",
            params={**periodo, filtro: str(uuid4())},
        )
        assert filtrada.status_code == 200, filtrada.text
        assert filtrada.json()["total_expedientes"] == 0
        assert filtrada.json()["total_pen"] == "0"


def test_documentos_y_expedientes_exponen_propietario_sin_inventarlo(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("factura_identidad.xml", factura(numero="F001-00000978"))},
    )
    assert subida.status_code == 201, subida.text
    documento_id = subida.json()["id"]
    usuario_id = subida.json()["usuario_id"]
    auth_prueba.como_admin()
    documentos = client.get("/api/v1/documentos")
    assert documentos.status_code == 200, documentos.text
    fila = next(d for d in documentos.json() if d["id"] == documento_id)
    assert fila["usuario_id"] == usuario_id
    assert fila["usuario_nombre"]
    assert "responsable_nombre" in fila
    assert "gestor_nombre" in fila
    if fila["expediente_id"]:
        expedientes = client.get("/api/v1/expedientes")
        assert expedientes.status_code == 200, expedientes.text
        expediente = next(e for e in expedientes.json() if e["id"] == fila["expediente_id"])
        assert expediente["usuario_nombre"] == fila["usuario_nombre"]
        assert expediente["usuario_codigo"] == fila["usuario_codigo"]
