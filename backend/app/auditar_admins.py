"""Inspección previa a separación de Superadmin y Administrador.

Solo lectura. Ejecutar dentro del contenedor backend con acceso a PostgreSQL.
No imprime credenciales ni modifica ningún registro.
"""

from sqlalchemy import select

from app.core.db import get_sessionmaker
from app.enums import RolMiembro
from app.models import CuentaAcceso, Miembro, Tenant


def main() -> None:
    with get_sessionmaker()() as session:
        tenants = session.scalars(select(Tenant).order_by(Tenant.nombre)).all()
        print(f"Tenants encontrados: {len(tenants)}")
        for tenant in tenants:
            miembros = session.scalars(
                select(Miembro).where(
                    Miembro.tenant_id == tenant.id,
                    Miembro.rol.in_((RolMiembro.ADMINISTRADOR, RolMiembro.SUPERADMIN)),
                    Miembro.deleted_at.is_(None),
                )
            ).all()
            print(
                f"Tenant: {tenant.nombre}; codigo={tenant.codigo}; subdominio={tenant.subdominio}"
            )
            for miembro in miembros:
                cuenta = session.scalar(
                    select(CuentaAcceso).where(
                        CuentaAcceso.tenant_id == tenant.id,
                        CuentaAcceso.miembro_id == miembro.id,
                        CuentaAcceso.deleted_at.is_(None),
                    )
                )
                print(
                    f"  rol={miembro.rol}; codigo={miembro.codigo}; "
                    f"login={cuenta.login if cuenta else 'SIN_CUENTA'}; "
                    f"activa={bool(cuenta and cuenta.activo)}"
                )


if __name__ == "__main__":
    main()
