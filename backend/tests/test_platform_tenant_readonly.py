"""Lectura global del Tenant sin permitir acceso operativo cruzado."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Gestor, Miembro, Tenant
from tests.conftest import AuthPrueba


def test_inspeccion_tenant_solo_superadmin(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    tenant = Tenant(nombre="ADMINISTRACION AISLADA", codigo="AIS-002", estado="ACTIVO")
    session.add(tenant)
    session.flush()
    admin = Miembro(
        tenant_id=tenant.id, codigo="ADMIN01", nombre="Admin aislado",
        rol="ADMINISTRADOR", activo=True,
    )
    otro = Miembro(
        tenant_id=tenant.id, codigo="USR01", nombre="Usuario aislado",
        rol="USUARIO", activo=True,
    )
    session.add_all([admin, otro])
    session.flush()
    session.add(
        Gestor(tenant_id=tenant.id, codigo="GES01", nombre="Gestor aislado", usuario_id=otro.id)
    )
    session.commit()
    url = f"/api/v1/configuracion/administraciones/{tenant.id}/inspeccion"
    assert client.get(url).status_code == 403
    auth_prueba.como_admin()
    assert client.get(url).status_code == 403
    auth_prueba.como_gerente()
    assert client.get(url).status_code == 403
    auth_prueba.como_superadmin()
    resultado = client.get(url)
    assert resultado.status_code == 200, resultado.text
    datos = resultado.json()
    assert datos["solo_lectura"] is True
    assert datos["tenant"]["codigo"] == "AIS-002"
    assert {m["codigo"] for m in datos["miembros"]} == {"ADMIN01", "USR01"}
    assert datos["gestores"][0]["codigo"] == "GES01"
    assert "password_hash" not in resultado.text
    assert "clave_temporal" not in resultado.text
    assert client.post(url).status_code == 405
    assert client.patch(url).status_code == 405
    assert client.delete(url).status_code == 405
