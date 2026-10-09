"""Cartera de empresas compartible por Gerente.

Revision ID: 0023
Revises: 0022
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gerentes_empresas",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("gerente_id", sa.Uuid(), sa.ForeignKey("miembros.id"), nullable=False),
        sa.Column("empresa_id", sa.Uuid(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "gerente_id",
            "empresa_id",
            name="uq_gerentes_empresas_tenant_gerente_empresa",
        ),
    )
    for column in ("tenant_id", "gerente_id", "empresa_id"):
        op.create_index(f"ix_gerentes_empresas_{column}", "gerentes_empresas", [column])


def downgrade() -> None:
    for column in ("tenant_id", "gerente_id", "empresa_id"):
        op.drop_index(f"ix_gerentes_empresas_{column}", table_name="gerentes_empresas")
    op.drop_table("gerentes_empresas")
