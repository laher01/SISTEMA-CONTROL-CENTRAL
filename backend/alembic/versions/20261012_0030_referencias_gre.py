"""Referencia fiscal provisional para conciliación de guías remitente.

Revision ID: 0030
Revises: 0029
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "referencias_gre",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column("documento_id", sa.Uuid(), nullable=False),
        sa.Column("serie", sa.String(4), nullable=False),
        sa.Column("correlativo", sa.String(8), nullable=False),
        sa.Column("emisor_ruc", sa.String(11), nullable=False),
        sa.Column("receptor_ruc", sa.String(11), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=True),
        sa.Column("gestor_id", sa.Uuid(), nullable=True),
        sa.Column("expediente_id", sa.Uuid(), nullable=True),
        sa.Column("resuelta_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["documento_id"], ["documentos.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["miembros.id"]),
        sa.ForeignKeyConstraint(["gestor_id"], ["gestores.id"]),
        sa.ForeignKeyConstraint(["expediente_id"], ["expedientes.id"]),
        sa.UniqueConstraint("tenant_id", "documento_id"),
    )
    op.create_index(
        "ix_referencias_gre_busqueda_factura",
        "referencias_gre",
        ["tenant_id", "serie", "correlativo", "emisor_ruc", "receptor_ruc"],
    )
    for columna in ("tenant_id", "documento_id", "expediente_id"):
        op.create_index(f"ix_referencias_gre_{columna}", "referencias_gre", [columna])


def downgrade() -> None:
    op.drop_table("referencias_gre")
