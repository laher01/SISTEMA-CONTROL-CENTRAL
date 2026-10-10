"""Matriz regresiva de permisos operativos y aislamiento del tenant."""

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from tests.conftest import AuthPrueba


@pytest.mark.parametrize(
    ("rol", "esperado"),
    [
        ("SUPERADMIN", 403),
        ("ADMINISTRADOR", 200),
        ("GERENTE", 403),
        ("SECRETARIA", 403),
        ("RESPONSABLE", 403),
        ("USUARIO", 403),
        ("GESTOR", 403),
    ],
)
def test_inventario_de_miembros_restringido_a_administracion(
    client: TestClient, auth_prueba: AuthPrueba, rol: str, esperado: int
) -> None:
    auth_prueba.contexto = replace(auth_prueba.contexto, rol=rol)
    respuesta = client.get("/api/v1/miembros")
    assert respuesta.status_code == esperado, respuesta.text


@pytest.mark.parametrize(
    ("rol", "esperado"),
    [
        ("SUPERADMIN", 200),
        ("ADMINISTRADOR", 200),
        ("GERENTE", 403),
        ("SECRETARIA", 403),
        ("RESPONSABLE", 403),
        ("USUARIO", 403),
        ("GESTOR", 403),
    ],
)
def test_visibilidad_global_de_tenants_solo_superadmin(
    client: TestClient, auth_prueba: AuthPrueba, rol: str, esperado: int
) -> None:
    auth_prueba.contexto = replace(auth_prueba.contexto, rol=rol)
    respuesta = client.get("/api/v1/configuracion/administraciones")
    if rol == "SUPERADMIN":
        assert respuesta.status_code == 200, respuesta.text
    else:
        assert respuesta.status_code == 403, respuesta.text


@pytest.mark.parametrize("rol", ["GERENTE", "SECRETARIA", "RESPONSABLE", "USUARIO", "GESTOR"])
def test_roles_no_admin_no_pueden_crear_miembros(
    client: TestClient, auth_prueba: AuthPrueba, rol: str
) -> None:
    auth_prueba.contexto = replace(auth_prueba.contexto, rol=rol)
    respuesta = client.post(
        "/api/v1/miembros",
        json={"codigo": "NOAUTORIZADO01", "nombre": "Prueba Seguridad", "rol": "USUARIO"},
    )
    assert respuesta.status_code == 403, respuesta.text


@pytest.mark.parametrize("rol", ["GERENTE", "SECRETARIA", "RESPONSABLE", "USUARIO", "GESTOR"])
def test_roles_no_admin_no_asignan_gerencias(
    client: TestClient, auth_prueba: AuthPrueba, rol: str
) -> None:
    import uuid

    auth_prueba.contexto = replace(auth_prueba.contexto, rol=rol)
    respuesta = client.put(
        "/api/v1/gerencias/vinculos",
        json={
            "gerente_id": str(uuid.uuid4()),
            "responsable_id": str(uuid.uuid4()),
            "activo": True,
        },
    )
    assert respuesta.status_code == 403, respuesta.text


@pytest.mark.parametrize(
    ("ruta", "metodo"),
    [
        ("/api/v1/documentos", "GET"),
        ("/api/v1/expedientes", "GET"),
        ("/api/v1/empresas", "GET"),
        ("/api/v1/miembros", "GET"),
        ("/api/v1/configuracion/acceso", "GET"),
        ("/api/v1/registros/opciones", "GET"),
        ("/api/v1/configuracion/mantenimiento/administradores", "GET"),
    ],
)
def test_superadmin_no_accede_a_api_operativa(
    client: TestClient, auth_prueba: AuthPrueba, ruta: str, metodo: str
) -> None:
    auth_prueba.como_superadmin()
    respuesta = client.request(metodo, ruta)
    assert respuesta.status_code == 403, respuesta.text


def test_superadmin_conserva_inventario_global(client: TestClient, auth_prueba: AuthPrueba) -> None:
    auth_prueba.como_superadmin()
    respuesta = client.get("/api/v1/configuracion/administraciones")
    assert respuesta.status_code == 200, respuesta.text
