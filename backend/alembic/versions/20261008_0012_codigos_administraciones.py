"""Código público único y secuencia de Administraciones.

Revision ID: 0012
Revises: 0011
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("codigo", sa.String(length=40), nullable=True))
    op.add_column(
        "tenants",
        sa.Column("origen_alta", sa.String(length=25), nullable=False, server_default="LEGADO"),
    )
    op.add_column(
        "tenants",
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="ACTIVO"),
    )
    op.create_index("ix_tenants_codigo", "tenants", ["codigo"], unique=True)
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE SEQUENCE secuencia_administraciones START WITH 1 INCREMENT BY 1")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP SEQUENCE secuencia_administraciones")
    op.drop_index("ix_tenants_codigo", table_name="tenants")
    op.drop_column("tenants", "estado")
    op.drop_column("tenants", "origen_alta")
    op.drop_column("tenants", "codigo")
