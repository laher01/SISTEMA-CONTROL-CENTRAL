"""Datos comerciales por Gerencia sin duplicar empresas fiscales.

Revision ID: 0025
Revises: 0024
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("gerentes_empresas", sa.Column("alias_comercial", sa.String(200), nullable=True))
    op.add_column("gerentes_empresas", sa.Column("rol_comercial", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("gerentes_empresas", "rol_comercial")
    op.drop_column("gerentes_empresas", "alias_comercial")
