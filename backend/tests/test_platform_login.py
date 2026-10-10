"""Inicio de sesión real por espacio: PLATFORM no suplanta la cuenta de un tenant."""

from sqlalchemy import select

from app.models import CuentaAcceso, Miembro, Tenant
from app.security import hash_clave


def test_login_superadmin_solo_platform_y_admin_tenant(client, session, settings):
    password = "ClaveSeguraDePruebas2026!"
    platform = Tenant(nombre="FACT CENTRAL PLATAFORMA", codigo="PLATFORM", estado="ACTIVO")
    nexomar = Tenant(nombre="NEXOMAR ENSAYO", codigo="NEX-TEST", estado="ACTIVO")
    session.add_all([platform, nexomar])
    session.flush()
    sup = Miembro(tenant_id=platform.id, codigo="SUPADMIN01", nombre="SaaS", rol="SUPERADMIN", activo=True)
    admin = Miembro(tenant_id=nexomar.id, codigo="ADMIN01", nombre="Nexomar", rol="ADMINISTRADOR", activo=True)
    session.add_all([sup, admin])
    session.flush()
    session.add_all([
        CuentaAcceso(tenant_id=platform.id, miembro_id=sup.id, login="SUPADMIN01", password_hash=hash_clave(password), activo=True, cambio_clave_obligatorio=False),
        CuentaAcceso(tenant_id=nexomar.id, miembro_id=admin.id, login="ADMIN01", password_hash=hash_clave(password), activo=True, cambio_clave_obligatorio=False),
    ])
    session.commit()

    super_login = client.post("/api/v1/auth/login", json={
        "espacio": "PLATFORM", "login": "SUPADMIN01", "clave": password,
    })
    assert super_login.status_code == 200, super_login.text
    assert super_login.json()["rol"] == "SUPERADMIN"

    incorrecto = client.post("/api/v1/auth/login", json={
        "espacio": "NEX-TEST", "login": "SUPADMIN01", "clave": password,
    })
    assert incorrecto.status_code == 401

    admin_login = client.post("/api/v1/auth/login", json={
        "espacio": "NEX-TEST", "login": "ADMIN01", "clave": password,
    })
    assert admin_login.status_code == 200, admin_login.text
    assert admin_login.json()["rol"] == "ADMINISTRADOR"

    incorrecto_admin = client.post("/api/v1/auth/login", json={
        "espacio": "PLATFORM", "login": "ADMIN01", "clave": password,
    })
    assert incorrecto_admin.status_code == 401

    assert session.scalar(select(CuentaAcceso).where(
        CuentaAcceso.tenant_id == nexomar.id, CuentaAcceso.login == "ADMIN01"
    )) is not None
