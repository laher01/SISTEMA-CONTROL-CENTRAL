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


def test_alta_tenant_independiente_no_autorizada_para_admin(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    payload = {
        "nombre_administrador": "Marina Torres",
        "nombre_espacio": "Pesquera de Ensayo",
        "subdominio": "pesquera-ensayo",
        "origen": "SUPERADMIN",
    }
    auth_prueba.como_admin()
    rechazado = client.post("/api/v1/configuracion/administraciones", json=payload)
    assert rechazado.status_code == 403

    auth_prueba.como_superadmin()
    creado = client.post("/api/v1/configuracion/administraciones", json=payload)
    assert creado.status_code == 201, creado.text
    datos = creado.json()
    assert datos["login"] == "ADMIN01"
    assert datos["subdominio"] == "pesquera-ensayo"
    assert datos["clave_temporal"]

    from sqlalchemy import select
    from app.models import CuentaAcceso
    tenant = session.scalar(select(Tenant).where(Tenant.nombre == "Pesquera de Ensayo"))
    assert tenant is not None
    admin = session.scalar(select(Miembro).where(
        Miembro.tenant_id == tenant.id,
        Miembro.codigo == "ADMIN01",
    ))
    assert admin is not None and admin.rol == "ADMINISTRADOR"
    cuenta = session.scalar(select(CuentaAcceso).where(
        CuentaAcceso.tenant_id == tenant.id,
        CuentaAcceso.miembro_id == admin.id,
    ))
    assert cuenta is not None and cuenta.cambio_clave_obligatorio

    repetido = client.post("/api/v1/configuracion/administraciones", json=payload)
    assert repetido.status_code == 409


def test_expedientes_globales_solo_superadmin(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    tenant = Tenant(nombre="Inspección auditada", codigo="INS-902-AD", estado="ACTIVO")
    session.add(tenant)
    session.commit()
    auth_prueba.como_admin()
    prohibido = client.get(
        f"/api/v1/configuracion/administraciones/{tenant.id}/expedientes"
    )
    assert prohibido.status_code == 403
    auth_prueba.como_superadmin()
    permitido = client.get(
        f"/api/v1/configuracion/administraciones/{tenant.id}/expedientes"
    )
    assert permitido.status_code == 200, permitido.text
    assert permitido.json()["expedientes"] == []
    invalido = client.get(
        f"/api/v1/configuracion/administraciones/{tenant.id}/expedientes?limite=101"
    )
    assert invalido.status_code == 422
