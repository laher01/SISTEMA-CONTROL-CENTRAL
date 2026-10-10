"""El inventario global solo se expone a SUPERADMIN."""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Miembro, Tenant
from tests.conftest import AuthPrueba


def test_estructura_tenant_requiere_superadmin(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    nuevo = Tenant(nombre="Tenant de ensayo separado", codigo="ENS-901-AD", estado="ACTIVO")
    session.add(nuevo)
    session.flush()
    session.add(Miembro(
        tenant_id=nuevo.id, codigo="ADMIN01", nombre="Admin Prueba",
        rol="ADMINISTRADOR", activo=True,
    ))
    session.commit()

    auth_prueba.como_admin()
    r = client.get(f"/api/v1/configuracion/administraciones/{nuevo.id}/estructura")
    assert r.status_code == 403

    auth_prueba.como_superadmin()
    r = client.get(f"/api/v1/configuracion/administraciones/{nuevo.id}/estructura")
    assert r.status_code == 200, r.text
    datos = r.json()
    assert datos["codigo"] == "ENS-901-AD"
    assert datos["miembros"][0]["codigo"] == "ADMIN01"
    assert "password_hash" not in str(datos)
