"""Preferencias visuales aisladas por cuenta y validadas sin tocar datos de negocio."""

from dataclasses import replace

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CuentaAcceso
from tests.conftest import AuthPrueba


def test_preferencias_visual_personal_persisten_y_se_validan(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    original = client.get("/api/v1/auth/mi-apariencia")
    assert original.status_code == 200, original.text
    assert original.json()["tema"] == "CLARO"
    datos = {"tema": "OSCURO", "color": "VERDE", "densidad": "COMPACTO", "barra": "MANUAL"}
    guardado = client.put("/api/v1/auth/mi-apariencia", json=datos)
    assert guardado.status_code == 200, guardado.text
    assert client.get("/api/v1/auth/mi-apariencia").json() == datos
    session.expire_all()
    cuenta = session.get(CuentaAcceso, auth_prueba.contexto.cuenta_id)
    assert cuenta is not None
    assert cuenta.preferencias_visuales == datos
    invalido = client.put("/api/v1/auth/mi-apariencia", json={**datos, "color": "#ff0000"})
    assert invalido.status_code == 422
    assert client.get("/api/v1/auth/mi-apariencia").json() == datos


def test_preferencias_estan_disponibles_para_gestor_y_usuario(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    auth_prueba.como_usuario(auth_prueba.contexto.usuario_id)
    assert client.get("/api/v1/auth/mi-apariencia").status_code == 200
    auth_prueba.contexto = replace(auth_prueba.contexto, rol="GESTOR")
    assert client.get("/api/v1/auth/mi-apariencia").status_code == 200
