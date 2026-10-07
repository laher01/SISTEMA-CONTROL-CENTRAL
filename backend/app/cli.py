import argparse

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import get_sessionmaker
from app.enums import RolMiembro
from app.models import Miembro
from app.security import crear_o_restablecer_cuenta
from app.services.expedientes import obtener_tenant


def main() -> None:
    parser = argparse.ArgumentParser(description="Administración inicial de FACT CENTRAL")
    sub = parser.add_subparsers(dest="comando", required=True)

    bootstrap = sub.add_parser("bootstrap-admin", help="Crear/restablecer el Administrador inicial")
    bootstrap.add_argument("--codigo", default="ADMIN01")
    bootstrap.add_argument("--nombre", default="Administrador FACT CENTRAL")

    args = parser.parse_args()
    if args.comando == "bootstrap-admin":
        _bootstrap_admin(args.codigo, args.nombre)


def _bootstrap_admin(codigo: str, nombre: str) -> None:
    settings = get_settings()
    with get_sessionmaker()() as session:
        tenant = obtener_tenant(session, settings.tenant_default)
        codigo_normalizado = codigo.strip().upper()
        miembro = session.scalar(
            select(Miembro).where(
                Miembro.tenant_id == tenant.id,
                Miembro.codigo == codigo_normalizado,
                Miembro.deleted_at.is_(None),
            )
        )
        if miembro is None:
            miembro = Miembro(
                tenant_id=tenant.id,
                codigo=codigo_normalizado,
                nombre=nombre.strip(),
                rol=RolMiembro.SUPERADMIN,
                activo=True,
            )
            session.add(miembro)
            session.flush()
        elif miembro.rol != RolMiembro.SUPERADMIN:
            raise SystemExit("El código indicado ya existe y no es Administrador")

        _, temporal = crear_o_restablecer_cuenta(
            session,
            tenant.id,
            codigo_normalizado,
            miembro_id=miembro.id,
        )
        session.commit()
        print(f"LOGIN={codigo_normalizado}")
        print(f"CLAVE_TEMPORAL={temporal}")
        print("Debe cambiar la clave al iniciar sesión por primera vez.")


if __name__ == "__main__":
    main()
