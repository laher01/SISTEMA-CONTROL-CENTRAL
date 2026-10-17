"""Estado global auditado de landing.

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
    op.create_table(
        "configuracion_landing_global",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("activa", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("actualizado_por", sa.Uuid(), sa.ForeignKey("cuentas_acceso.id")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.execute("INSERT INTO configuracion_landing_global (id, activa, version) VALUES (1, TRUE, 1)")
    op.create_table(
        "auditoria_landing_global",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("cuenta_id", sa.Uuid(), sa.ForeignKey("cuentas_acceso.id"), nullable=False),
        sa.Column("anterior", sa.Boolean(), nullable=False),
        sa.Column("nuevo", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("auditoria_landing_global")
    op.drop_table("configuracion_landing_global")
