"""Configurar nuevas landing globales como no publicadas por defecto.

Revision ID: 0041
Revises: 0040

No altera filas existentes ni su estado editorial.
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0041"
down_revision: str | None = "0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "configuracion_landing_global",
        "activa",
        existing_type=sa.Boolean(),
        existing_nullable=False,
        server_default=sa.false(),
    )


def downgrade() -> None:
    op.alter_column(
        "configuracion_landing_global",
        "activa",
        existing_type=sa.Boolean(),
        existing_nullable=False,
        server_default=sa.true(),
    )
