"""Regresión: SUPADMIN01 no reemplaza la identidad ADMIN01 existente."""
import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app import cli
from app.models import CuentaAcceso, Miembro
from app.services.expedientes import obtener_tenant


def test_bootstrap_superadmin_preserva_admin(engine, settings, monkeypatch):
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    monkeypatch.setattr(cli, "get_sessionmaker", lambda: sessionmaker(engine))
    with sessionmaker(engine)() as s:
        tenant = obtener_tenant(s, settings.tenant_default)
        admin = Miembro(
            tenant_id=tenant.id, codigo="ADMIN01", nombre="Admin Nexomar",
            rol="ADMINISTRADOR", activo=True,
        )
        s.add(admin)
        s.flush()
        cuenta = CuentaAcceso(
            tenant_id=tenant.id, login="ADMIN01", miembro_id=admin.id,
            password_hash="clave-vigente-no-modificar", activo=True,
            cambio_clave_obligatorio=False,
        )
        s.add(cuenta)
        s.commit()
        admin_id = admin.id
        cuenta_id = cuenta.id

    with pytest.raises(SystemExit):
        cli._bootstrap_admin("ADMIN01", "No permitido", True)
    with pytest.raises(SystemExit):
        cli._bootstrap_admin("SUPADMIN01", "Superadmin", False)
    cli._bootstrap_admin("SUPADMIN01", "Superadmin", True)
    with pytest.raises(SystemExit):
        cli._bootstrap_admin("SUPADMIN01", "Superadmin", True)

    with sessionmaker(engine)() as s:
        admin = s.get(Miembro, admin_id)
        cuenta = s.get(CuentaAcceso, cuenta_id)
        assert admin is not None and admin.rol == "ADMINISTRADOR"
        assert cuenta is not None and cuenta.password_hash == "clave-vigente-no-modificar"
        assert cuenta.login == "ADMIN01"
        sup = s.scalar(select(Miembro).where(
            Miembro.tenant_id == admin.tenant_id, Miembro.codigo == "SUPADMIN01",
        ))
        assert sup is not None and sup.rol == "SUPERADMIN"
        assert s.scalar(select(CuentaAcceso).where(
            CuentaAcceso.tenant_id == admin.tenant_id,
            CuentaAcceso.miembro_id == sup.id,
        )) is not None
