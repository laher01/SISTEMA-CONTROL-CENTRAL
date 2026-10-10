"""Cuentas sintéticas exclusivas del PostgreSQL desechable de GitHub Actions."""
import os

from sqlalchemy.orm import Session

from app.core.db import get_engine
from app.models import CuentaAcceso, Miembro, Tenant
from app.security import hash_clave

assert os.environ.get("FC_E2E_ISOLATED") == "true", "Solo ejecutar en CI aislado"
assert "localhost" in os.environ.get("FC_DATABASE_URL", ""), "DB debe ser local"

with Session(get_engine()) as session:
    for codigo_tenant, codigo_usuario, rol in [
        ("PLATFORM", "SUPADMIN01", "SUPERADMIN"),
        ("PRUEBAS", "ADMIN01", "ADMINISTRADOR"),
    ]:
        tenant = Tenant(nombre=codigo_tenant, codigo=codigo_tenant, estado="ACTIVO")
        session.add(tenant)
        session.flush()
        miembro = Miembro(
            tenant_id=tenant.id, codigo=codigo_usuario, nombre="Usuario E2E", rol=rol, activo=True,
        )
        session.add(miembro)
        session.flush()
        session.add(CuentaAcceso(
            tenant_id=tenant.id,
            miembro_id=miembro.id,
            login=codigo_usuario,
            password_hash=hash_clave("ClaveE2e123!"),
            activo=True,
            cambio_clave_obligatorio=False,
        ))
    session.commit()
print("DOS_TENANTS_E2E_CREADOS")
