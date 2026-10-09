"""Identidad canónica de RHE sin RUC receptor.

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_expedientes_rhe_identidad_activa",
        "expedientes",
        ["tenant_id", "emisor_id", "tipo_comprobante", "serie", "correlativo"],
        unique=True,
        postgresql_where=sa.text("tipo_comprobante = 'RHE' AND deleted_at IS NULL"),
        sqlite_where=sa.text("tipo_comprobante = 'RHE' AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_expedientes_rhe_identidad_activa", table_name="expedientes")
