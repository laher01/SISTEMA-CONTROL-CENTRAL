"""trazabilidad creador y mantenimiento selectivo

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TABLAS = (
    "miembros",
    "gestores",
    "expedientes",
    "documentos",
    "planes_liquidacion",
    "cuentas_pago_erp",
    "adelantos_erp",
    "pagos_erp",
)


def upgrade() -> None:
    for tabla in TABLAS:
        op.add_column(
            tabla,
            sa.Column("creado_por_cuenta_id", sa.Uuid(), nullable=True),
        )
        op.create_index(
            op.f(f"ix_{tabla}_creado_por_cuenta_id"),
            tabla,
            ["creado_por_cuenta_id"],
            unique=False,
        )
        op.create_foreign_key(
            op.f(f"fk_{tabla}_creado_por_cuenta_id_cuentas_acceso"),
            tabla,
            "cuentas_acceso",
            ["creado_por_cuenta_id"],
            ["id"],
        )


def downgrade() -> None:
    for tabla in reversed(TABLAS):
        op.drop_constraint(
            op.f(f"fk_{tabla}_creado_por_cuenta_id_cuentas_acceso"),
            tabla,
            type_="foreignkey",
        )
        op.drop_index(
            op.f(f"ix_{tabla}_creado_por_cuenta_id"),
            table_name=tabla,
        )
        op.drop_column(tabla, "creado_por_cuenta_id")
