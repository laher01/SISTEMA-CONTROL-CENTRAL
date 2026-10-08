"""mensajeria privada y adjuntos entre cuentas

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_mensajes",
        sa.Column("remitente_cuenta_id", sa.Uuid(), nullable=False),
        sa.Column("destinatario_cuenta_id", sa.Uuid(), nullable=False),
        sa.Column("texto", sa.String(2000), nullable=False, server_default=""),
        sa.Column("archivo_nombre", sa.String(255), nullable=True),
        sa.Column("archivo_mime", sa.String(100), nullable=True),
        sa.Column("archivo_sha256", sa.String(64), nullable=True),
        sa.Column("archivo_ruta", sa.String(500), nullable=True),
        sa.Column("archivo_tamano", sa.BigInteger(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(["remitente_cuenta_id"], ["cuentas_acceso.id"]),
        sa.ForeignKeyConstraint(["destinatario_cuenta_id"], ["cuentas_acceso.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for columna in (
        "remitente_cuenta_id",
        "destinatario_cuenta_id",
        "tenant_id",
        "created_at",
    ):
        op.create_index(op.f(f"ix_chat_mensajes_{columna}"), "chat_mensajes", [columna])


def downgrade() -> None:
    for columna in (
        "created_at",
        "tenant_id",
        "destinatario_cuenta_id",
        "remitente_cuenta_id",
    ):
        op.drop_index(op.f(f"ix_chat_mensajes_{columna}"), table_name="chat_mensajes")
    op.drop_table("chat_mensajes")
