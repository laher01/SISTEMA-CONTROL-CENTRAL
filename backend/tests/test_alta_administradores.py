from fastapi.testclient import TestClient
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from app.models import CuentaAcceso, Miembro, Tenant
from tests.conftest import AuthPrueba


def test_alta_administrador_desde_superadmin(
    client: TestClient, auth_prueba: AuthPrueba, session: Session, engine: Engine
) -> None:
    if engine.dialect.name == "postgresql":
        with engine.begin() as conexion:
            conexion.execute(text("CREATE SEQUENCE IF NOT EXISTS secuencia_administraciones"))
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
    cuenta_nueva = session.scalar(
        select(CuentaAcceso).where(
            CuentaAcceso.tenant_id == tenant.id,
            CuentaAcceso.login == "ADMIN01",
        )
    )
    assert cuenta_nueva is not None
    assert cuenta_nueva.miembro_id is not None
    assert cuenta_nueva.tenant_id != auth_prueba.contexto.tenant_id

    inventario = client.get("/api/v1/configuracion/administraciones")
    assert inventario.status_code == 200, inventario.text
    tenants = inventario.json()
    assert {item["id"] for item in tenants} == {
        str(auth_prueba.contexto.tenant_id),
        str(tenant.id),
    }
    assert next(item for item in tenants if item["id"] == str(tenant.id))["documentos"] == 0

    assert client.post("/api/v1/configuracion/administraciones", json=datos).status_code == 409
