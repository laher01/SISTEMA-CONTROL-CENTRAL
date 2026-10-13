"""Persistencia de propuestas de fórmulas NEXUS, sin afectar pagos históricos.

Revision ID: 0030
Revises: 0029
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "formulas_pago_nexus",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("responsable_id", sa.Uuid(), sa.ForeignKey("miembros.id"), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("miembros.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(160), nullable=False),
        sa.Column("descripcion", sa.String(2000), nullable=False),
        sa.Column("plantilla", sa.String(60), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="BORRADOR"),
        sa.Column(
            "creado_por_cuenta_id",
            sa.Uuid(),
            sa.ForeignKey("cuentas_acceso.id"),
            nullable=True,
        ),
        sa.Column(
            "aprobado_por_cuenta_id",
            sa.Uuid(),
            sa.ForeignKey("cuentas_acceso.id"),
            nullable=True,
        ),
        sa.Column("aprobado_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "tenant_id", "responsable_id", "usuario_id", "version",
            name="uq_nexus_formula_version",
        ),
        sa.CheckConstraint("version >= 1", name="ck_nexus_version_positiva"),
        sa.CheckConstraint(
            "estado IN ('BORRADOR', 'APROBADA', 'REVOCADA')",
            name="ck_nexus_estado_valido",
        ),
    )
    op.create_index(
        "ix_nexus_formula_scope",
        "formulas_pago_nexus",
        ["tenant_id", "responsable_id", "usuario_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_nexus_formula_scope", table_name="formulas_pago_nexus")
    op.drop_table("formulas_pago_nexus")
