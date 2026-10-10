"""Corrección controlada de ADMIN01 legado. Nunca toca contraseñas.

Ejemplo:
 python -m app.reparar_admin_nexomar --tenant-id UUID --confirmar
Exige SUPADMIN01 activo en el tenant y ADMIN01 actualmente SUPERADMIN.
"""
import argparse
import uuid

from sqlalchemy import select

from app.core.db import get_sessionmaker
from app.models import CuentaAcceso, Miembro, Tenant


def reparar(tenant_id: uuid.UUID, confirmar: bool = False) -> str:
    with get_sessionmaker()() as session:
        tenant = session.get(Tenant, tenant_id)
        if tenant is None or tenant.estado != "ACTIVO":
            raise ValueError("Tenant inexistente o inactivo")
        miembros = list(session.scalars(select(Miembro).where(
            Miembro.tenant_id == tenant_id,
            Miembro.codigo.in_(("ADMIN01", "SUPADMIN01")),
            Miembro.deleted_at.is_(None),
        )))
        por_codigo = {m.codigo: m for m in miembros}
        admin = por_codigo.get("ADMIN01")
        superadmin = por_codigo.get("SUPADMIN01")
        if admin is None or superadmin is None or superadmin.rol != "SUPERADMIN":
            raise ValueError("Identidades sin verificar: se requiere ADMIN01 y SUPADMIN01")
        for miembro in (admin, superadmin):
            cuenta = session.scalar(select(CuentaAcceso).where(
                CuentaAcceso.tenant_id == tenant_id,
                CuentaAcceso.miembro_id == miembro.id,
                CuentaAcceso.activo.is_(True),
                CuentaAcceso.deleted_at.is_(None),
            ))
            if cuenta is None or cuenta.login != miembro.codigo:
                raise ValueError("La identidad carece de una cuenta activa coincidente")
        if admin.rol == "ADMINISTRADOR":
            return "ADMIN01 ya es ADMINISTRADOR; sin cambios"
        if admin.rol != "SUPERADMIN":
            raise ValueError("Rol previo de ADMIN01 no esperado")
        if not confirmar:
            return "Verificado, sin cambios. Ejecutar con --confirmar después del respaldo."
        admin.rol = "ADMINISTRADOR"
        session.commit()
        return "Rol ADMIN01 corregido; cuenta y hash de contraseña intactos"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-id", type=uuid.UUID, required=True)
    parser.add_argument("--confirmar", action="store_true")
    args = parser.parse_args()
    print(reparar(args.tenant_id, args.confirmar))


if __name__ == "__main__":
    main()
