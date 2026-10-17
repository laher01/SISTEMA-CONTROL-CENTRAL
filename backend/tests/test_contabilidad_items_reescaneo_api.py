"""Autorización por rol y tenant de la previsualización XML de solo lectura."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.item_models import LineaComprobanteItem

RUTA = "/api/v1/contabilidad-items/reescaneo/vista-previa"


@pytest.mark.parametrize("rol", ["USUARIO", "GERENTE", "GESTOR", "RESPONSABLE"])
def test_previsualizacion_deniega_roles_no_administradores(
    client: TestClient, auth_prueba, rol: str
):
    if rol == "USUARIO":
        auth_prueba.como_usuario(uuid.uuid4())
    elif rol == "GERENTE":
        auth_prueba.como_gerente()
    elif rol == "GESTOR":
        auth_prueba.como_gestor(uuid.uuid4(), uuid.uuid4())
    elif rol == "RESPONSABLE":
        auth_prueba.contexto = auth_prueba.contexto.__class__(
            **{**vars(auth_prueba.contexto), "rol": "RESPONSABLE"}
        )
    respuesta = client.get(RUTA)
    assert respuesta.status_code == 403


def test_previsualizacion_admin_vacia_y_sin_escrituras(
    client: TestClient, auth_prueba, session: Session
):
    auth_prueba.como_admin()
    respuesta = client.get(RUTA)
    assert respuesta.status_code == 200
    assert respuesta.json() == []
    assert session.scalar(select(func.count()).select_from(LineaComprobanteItem)) == 0


def test_previsualizacion_rechaza_paginacion_invalida(client: TestClient, auth_prueba):
    auth_prueba.como_admin()
    assert client.get(RUTA, params={"limite": 101}).status_code == 422
    assert client.get(RUTA, params={"despues_id": "no-uuid"}).status_code == 422
