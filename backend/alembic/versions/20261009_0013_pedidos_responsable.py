"""Pedido bruto a Responsable, sin distribución automática.

Revision ID: 0013
Revises: 0012
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("pedidos_gerencia", sa.Column("responsable_id", sa.Uuid(), nullable=True))
    op.create_index("ix_pedidos_gerencia_responsable_id", "pedidos_gerencia", ["responsable_id"])
    op.create_foreign_key(
        "fk_pedidos_gerencia_responsable_id_miembros",
        "pedidos_gerencia", "miembros", ["responsable_id"], ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_pedidos_gerencia_responsable_id_miembros",
        "pedidos_gerencia", type_="foreignkey",
    )
    op.drop_index("ix_pedidos_gerencia_responsable_id", table_name="pedidos_gerencia")
    op.drop_column("pedidos_gerencia", "responsable_id")
