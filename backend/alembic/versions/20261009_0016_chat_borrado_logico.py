"""Soft delete de mensajes para control global SaaS.

Revision ID: 0016
Revises: 0015
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chat_mensajes", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("chat_mensajes", sa.Column("eliminado_por_cuenta_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_chat_eliminado_por_cuenta", "chat_mensajes", "cuentas_acceso",
        ["eliminado_por_cuenta_id"], ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_chat_eliminado_por_cuenta", "chat_mensajes", type_="foreignkey")
    op.drop_column("chat_mensajes", "eliminado_por_cuenta_id")
    op.drop_column("chat_mensajes", "deleted_at")
