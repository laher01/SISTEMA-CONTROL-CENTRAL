from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import Miembro, Tenant
from tests.conftest import AuthPrueba


def test_alta_administrador_desde_superadmin(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    session.execute(text("CREATE SEQUENCE IF NOT EXISTS secuencia_administraciones"))
    session.commit()
    datos = {
        "nombre_administrador": "Luis Arevalo Herrera",
        "nombre_espacio": "Administración Luis Arévalo Herrera",
        "origen": "SUPERADMIN",
    }
    assert client.post("/api/v1/configuracion/administraciones", json=datos).status_code == 403
    auth_prueba.como_superadmin()
    r = client.post("/api/v1/configuracion/administraciones", json=datos)
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["codigo"] == "LAH-001-AD"
    assert cuerpo["login"] == "ADMIN01"
    assert cuerpo["clave_temporal"]
    tenant = session.scalar(select(Tenant).where(Tenant.codigo == "LAH-001-AD"))
    assert tenant is not None
    assert tenant.id != auth_prueba.contexto.tenant_id
    assert (
        session.scalar(
            select(Miembro).where(Miembro.tenant_id == tenant.id, Miembro.rol == "ADMINISTRADOR")
        )
        is not None
    )
    assert client.post("/api/v1/configuracion/administraciones", json=datos).status_code == 409
