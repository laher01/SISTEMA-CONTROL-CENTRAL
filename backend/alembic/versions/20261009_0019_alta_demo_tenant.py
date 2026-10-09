"""Datos de alta demo del espacio administrativo.

Revision ID: 0019
Revises: 0018
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("plan_demo", sa.String(24), nullable=True))
    op.add_column("tenants", sa.Column("correo_contacto", sa.String(200), nullable=True))
    op.add_column("tenants", sa.Column("dni_contacto", sa.String(8), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "dni_contacto")
    op.drop_column("tenants", "correo_contacto")
    op.drop_column("tenants", "plan_demo")
