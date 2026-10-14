"""Huella comercial opcional y exclusiva por tenant.

Revision ID: 0034
Revises: 0033
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0034"
down_revision: str | None = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documentos", sa.Column("huella_comercial", sa.String(64), nullable=True))
    op.create_unique_constraint(
        "uq_documentos_tenant_id_huella_comercial",
        "documentos",
        ["tenant_id", "huella_comercial"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_documentos_tenant_id_huella_comercial", "documentos", type_="unique")
    op.drop_column("documentos", "huella_comercial")
