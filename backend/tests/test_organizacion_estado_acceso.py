from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CuentaAcceso
from app.security import contexto_desde_token, crear_sesion
from tests.conftest import AuthPrueba


def test_estado_acceso_organizacion(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    auth_prueba.como_admin()
    for rol in ("USUARIO", "RESPONSABLE"):
        alta = client.post("/api/v1/miembros", json={"nombre": f"Estado {rol}", "rol": rol})
        assert alta.status_code == 201, alta.text
        miembro = alta.json()["miembro"]
        ruta = f"/api/v1/miembros/{miembro['id']}/estado-acceso"
        respuesta = client.patch(ruta, json={"activo": False})
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["acceso_activo"] is False
        assert respuesta.json()["activo"] is True
        assert next(
            m for m in client.get("/api/v1/miembros").json() if m["id"] == miembro["id"]
        )["acceso_activo"] is False
        assert client.patch(ruta, json={"activo": True}).json()["acceso_activo"] is True

    alta = client.post(
        "/api/v1/gestores",
        json={"nombre": "Gestor estado", "usuario_id": str(auth_prueba.usuario_id)},
    )
    assert alta.status_code == 201, alta.text
    gestor = alta.json()["gestor"]
    ruta = f"/api/v1/gestores/{gestor['id']}/estado-acceso"
    cuenta = session.scalar(select(CuentaAcceso).where(CuentaAcceso.login == gestor["codigo"]))
    assert cuenta is not None
    _, token = crear_sesion(session, cuenta, "GESTOR")
    session.commit()
    auth_prueba.como_usuario(auth_prueba.usuario_id)
    assert client.patch(ruta, json={"activo": False}).status_code == 403
    auth_prueba.como_admin()
    assert client.patch(ruta, json={"activo": False}).json()["acceso_activo"] is False
    session.expire_all()
    assert contexto_desde_token(session, token) is None
    assert client.post(f"/api/v1/gestores/{gestor['id']}/restablecer-acceso").status_code == 200
    assert next(
        g for g in client.get("/api/v1/gestores").json() if g["id"] == gestor["id"]
    )["acceso_activo"] is False
    assert client.patch(ruta, json={"activo": True}).json()["acceso_activo"] is True
    session.expire_all()
    assert contexto_desde_token(session, token) is None
    auth_prueba.como_usuario(auth_prueba.usuario_id)
    assert client.patch(
        f"/api/v1/miembros/{auth_prueba.usuario_id}/estado-acceso", json={"activo": False}
    ).status_code == 403
