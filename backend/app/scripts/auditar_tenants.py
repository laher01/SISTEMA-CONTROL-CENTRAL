"""Inspección no destructiva de datos por Administración (tenant).

Ejecutar desde backend: uv run python -m app.scripts.auditar_tenants
O: uv run python -m app.scripts.auditar_tenants --tenant-id UUID

Este comando NUNCA elimina registros ni ficheros.
"""

import argparse
import uuid

from sqlalchemy import func, select

from app.core.db import get_sessionmaker
from app.models import Base, Tenant


def main() -> None:
    parser = argparse.ArgumentParser(description="Auditoría de espacios administrativos")
    parser.add_argument("--tenant-id", type=uuid.UUID, help="UUID del espacio a inspeccionar")
    args = parser.parse_args()
    with get_sessionmaker()() as session:
        if args.tenant_id is None:
            tenants = session.scalars(select(Tenant).order_by(Tenant.nombre)).all()
            print("TENANTS (ningún dato se eliminará):")
            for item in tenants:
                print(f"{item.id} | {item.nombre}")
            print(f"Total: {len(tenants)}")
            return

        tenant = session.get(Tenant, args.tenant_id)
        if tenant is None:
            parser.error("Tenant no encontrado")
        print(f"Administración: {tenant.nombre} | UUID: {tenant.id}")
        total = 0
        for tabla in sorted(Base.metadata.tables.values(), key=lambda t: t.name):
            if tabla.name == "tenants" or "tenant_id" not in tabla.c:
                continue
            cantidad = (
                session.scalar(
                    select(func.count())
                    .select_from(tabla)
                    .where(tabla.c.tenant_id == args.tenant_id)
                )
                or 0
            )
            if cantidad:
                print(f"{tabla.name}: {cantidad}")
                total += cantidad
        print(f"Registros vinculados: {total}")
        print("MODO LECTURA: no se ha eliminado ni modificado información.")


if __name__ == "__main__":
    main()
