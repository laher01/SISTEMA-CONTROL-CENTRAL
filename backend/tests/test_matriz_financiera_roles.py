"""Límites de autorización: liquidaciones, cobros, comisiones y atribución."""

import uuid
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from tests.conftest import AuthPrueba


@pytest.mark.parametrize("rol", ["GERENTE", "SECRETARIA", "USUARIO", "GESTOR"])
@pytest.mark.parametrize("ruta", ["/api/v1/responsable/pagos/cotizar", "/api/v1/responsable/pagos/programar"])
def test_pago_produccion_prohibido_para_rol_sin_facultad(
    client: TestClient, auth_prueba: AuthPrueba, rol: str, ruta: str
) -> None:
    auth_prueba.contexto = replace(auth_prueba.contexto, rol=rol)
    respuesta = client.post(
        ruta,
        json={
            "usuario_id": str(uuid.uuid4()),
            "desde": "2026-09-01",
            "hasta": "2026-09-30",
            "moneda": "PEN",
            "saldo_ids": [],
            "adelanto_ids": [],
        },
    )
    assert respuesta.status_code == 403, respuesta.text


@pytest.mark.parametrize("rol", ["GERENTE", "SECRETARIA", "RESPONSABLE", "USUARIO", "GESTOR"])
def test_atribucion_de_factura_exclusiva_de_administracion(
    client: TestClient, auth_prueba: AuthPrueba, rol: str
) -> None:
    auth_prueba.contexto = replace(auth_prueba.contexto, rol=rol)
    respuesta = client.put(
        f"/api/v1/gerencias/facturas/{uuid.uuid4()}/atribuir",
        json={"pedido_id": str(uuid.uuid4())},
    )
    assert respuesta.status_code == 403, respuesta.text


@pytest.mark.parametrize("rol", ["GERENTE", "SECRETARIA", "GESTOR"])
def test_roles_sin_facultad_no_calculan_comisiones_ajenas(
    client: TestClient, auth_prueba: AuthPrueba, rol: str
) -> None:
    auth_prueba.contexto = replace(auth_prueba.contexto, rol=rol)
    respuesta = client.post(
        "/api/v1/comisiones/simular",
        json={
            "usuario_id": str(uuid.uuid4()),
            "desde": "2026-09-01",
            "hasta": "2026-09-30",
            "moneda": "PEN",
        },
    )
    assert respuesta.status_code == 403, respuesta.text
