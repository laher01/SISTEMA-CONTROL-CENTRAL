"""Persistencia del período inicial por buzón para Gmail y Outlook."""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CorreoBuzon
from tests.conftest import AuthPrueba


def test_importacion_inicial_mes_persistida_google_outlook(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    auth_prueba.como_admin()
    for proveedor, direccion in (
        ("GOOGLE", "primero@gmail.com"),
        ("MICROSOFT", "segundo@outlook.com"),
    ):
        respuesta = client.post(
            "/api/v1/correo/buzones",
            json={"direccion": direccion, "proveedor": proveedor, "periodo_inicial": "MES"},
        )
        assert respuesta.status_code == 201, respuesta.text
        buzon = session.scalar(
            select(CorreoBuzon).where(
                CorreoBuzon.tenant_id == auth_prueba.contexto.tenant_id,
                CorreoBuzon.direccion == direccion,
            )
        )
        assert buzon is not None
        assert buzon.importar_desde is not None
        assert date.today() - timedelta(days=31) <= buzon.importar_desde <= date.today()
        assert buzon.activo is False

    listado = client.get("/api/v1/correo/buzones")
    assert listado.status_code == 200, listado.text
    assert all(b["importar_desde"] for b in listado.json())


def test_importacion_inicial_rechaza_periodo_invalido(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    auth_prueba.como_admin()
    respuesta = client.post(
        "/api/v1/correo/buzones",
        json={
            "direccion": "rechazar@gmail.com",
            "proveedor": "GOOGLE",
            "periodo_inicial": "TODOS",
        },
    )
    assert respuesta.status_code == 422
