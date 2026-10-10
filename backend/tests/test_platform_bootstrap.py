"""El alta global crea PLATFORM sin alterar los administradores existentes."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app import cli
from app.models import CuentaAcceso, Miembro, Tenant
from app.services.expedientes import obtener_tenant


def test_bootstrap_platform_aislado(engine, settings, monkeypatch):
    monkeypatch.setattr(cli, "get_sessionmaker", lambda: sessionmaker(engine))
    with sessionmaker(engine)() as session:
        nexomar = obtener_tenant(session, settings.tenant_default)
        admin = Miembro(
            tenant_id=nexomar.id, codigo="ADMIN01", nombre="Administrador de prueba",
            rol="ADMINISTRADOR", activo=True,
        )
        session.add(admin)
        session.flush()
        cuenta = CuentaAcceso(
            tenant_id=nexomar.id, miembro_id=admin.id, login="ADMIN01",
            password_hash="hash-no-modificar", activo=True,
        )
        session.add(cuenta)
        session.commit()
        cuenta_id, nexomar_id = cuenta.id, nexomar.id

    with pytest.raises(SystemExit):
        cli._bootstrap_admin("ADMIN01", "Impostor", True)
    with pytest.raises(SystemExit):
        cli._bootstrap_admin("SUPADMIN01", "Superadmin", False)
    cli._bootstrap_admin("SUPADMIN01", "Superadmin", True)
    with pytest.raises(SystemExit):
        cli._bootstrap_admin("SUPADMIN01", "Superadmin", True)

    with sessionmaker(engine)() as session:
        cuenta = session.get(CuentaAcceso, cuenta_id)
        assert cuenta is not None
        assert cuenta.login == "ADMIN01"
        assert cuenta.password_hash == "hash-no-modificar"
        platform = session.scalar(select(Tenant).where(Tenant.codigo == "PLATFORM"))
        assert platform is not None and platform.id != nexomar_id
        sup = session.scalar(select(Miembro).where(
            Miembro.tenant_id == platform.id, Miembro.codigo == "SUPADMIN01"
        ))
        assert sup is not None and sup.rol == "SUPERADMIN"
