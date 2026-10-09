"""Añadir rol Responsable y relación opcional de usuarios.

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("miembros", sa.Column("responsable_id", sa.Uuid(), nullable=True))
    op.create_index("ix_miembros_responsable_id", "miembros", ["responsable_id"])
    op.create_foreign_key(
        "fk_miembros_responsable_id_miembros",
        "miembros",
        "miembros",
        ["responsable_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_miembros_responsable_id_miembros", "miembros", type_="foreignkey")
    op.drop_index("ix_miembros_responsable_id", table_name="miembros")
    op.drop_column("miembros", "responsable_id")
