"""asigna actores S.P.T. por tenant sin reutilizar roles de otros módulos

Revision ID: 0054
Revises: 0053
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0054"
down_revision: str | None = "0053"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pesca_asignaciones_rol",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("cuenta_id", sa.Uuid(), nullable=False),
        sa.Column("rol", sa.String(length=40), nullable=False),
        sa.Column("activa", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("asignado_por_cuenta_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["asignado_por_cuenta_id"], ["cuentas_acceso.id"]),
        sa.ForeignKeyConstraint(["cuenta_id"], ["cuentas_acceso.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "cuenta_id", "rol"),
    )
    op.create_index("ix_pesca_asignaciones_rol_tenant_id", "pesca_asignaciones_rol", ["tenant_id"])
    op.create_index("ix_pesca_asignaciones_rol_cuenta_id", "pesca_asignaciones_rol", ["cuenta_id"])
    op.create_index("ix_pesca_asignaciones_rol_rol", "pesca_asignaciones_rol", ["rol"])
    op.create_table(
        "pesca_auditoria_roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("actor_cuenta_id", sa.Uuid(), nullable=False),
        sa.Column("cuenta_objetivo_id", sa.Uuid(), nullable=False),
        sa.Column("rol", sa.String(length=40), nullable=False),
        sa.Column("accion", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_cuenta_id"], ["cuentas_acceso.id"]),
        sa.ForeignKeyConstraint(["cuenta_objetivo_id"], ["cuentas_acceso.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pesca_auditoria_roles_tenant_id", "pesca_auditoria_roles", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_pesca_auditoria_roles_tenant_id", table_name="pesca_auditoria_roles")
    op.drop_table("pesca_auditoria_roles")
    op.drop_index("ix_pesca_asignaciones_rol_rol", table_name="pesca_asignaciones_rol")
    op.drop_index("ix_pesca_asignaciones_rol_cuenta_id", table_name="pesca_asignaciones_rol")
    op.drop_index("ix_pesca_asignaciones_rol_tenant_id", table_name="pesca_asignaciones_rol")
    op.drop_table("pesca_asignaciones_rol")
