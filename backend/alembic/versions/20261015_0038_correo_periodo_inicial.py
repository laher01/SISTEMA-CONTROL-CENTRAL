"""Período inicial de importación de buzones, sin alterar las cuentas existentes.

Revision ID: 0038
Revises: 0037
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0038"
down_revision: str | None = "0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("correo_buzones", sa.Column("importar_desde", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("correo_buzones", "importar_desde")
