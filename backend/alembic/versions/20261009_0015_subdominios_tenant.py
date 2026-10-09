"""Subdominio opcional y único para Administraciones.

Revision ID: 0015
Revises: 0014
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("subdominio", sa.String(63), nullable=True))
    op.create_index("ix_tenants_subdominio", "tenants", ["subdominio"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_tenants_subdominio", table_name="tenants")
    op.drop_column("tenants", "subdominio")
