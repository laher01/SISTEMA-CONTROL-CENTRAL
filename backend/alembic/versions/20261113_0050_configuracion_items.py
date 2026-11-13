"""Configuración y precios de ítems."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0050"
down_revision: str | None = "0049"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "productos_items",
        sa.Column("fuera_rubro", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("productos_items", sa.Column("combinado_en_id", sa.Uuid()))
    op.create_foreign_key(
        "fk_items_combinado_en",
        "productos_items",
        "productos_items",
        ["combinado_en_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.add_column("lineas_comprobantes_items", sa.Column("precio_unitario", sa.Numeric(22, 8)))


def downgrade() -> None:
    op.drop_column("lineas_comprobantes_items", "precio_unitario")
    op.drop_constraint("fk_items_combinado_en", "productos_items", type_="foreignkey")
    op.drop_column("productos_items", "combinado_en_id")
    op.drop_column("productos_items", "fuera_rubro")
