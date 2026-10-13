"""Relaciones documentales N:M (la referencia GRE usa 0030).

Revision ID: 0031
Revises: 0030
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "relaciones_documentos",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("origen_id", sa.Uuid(), sa.ForeignKey("documentos.id"), nullable=False),
        sa.Column("destino_id", sa.Uuid(), sa.ForeignKey("documentos.id"), nullable=False),
        sa.Column("tipo", sa.String(40), nullable=False),
        sa.Column("evidencia", sa.String(500), nullable=False),
        sa.Column("confirmado_por_cuenta_id", sa.Uuid(), sa.ForeignKey("cuentas_acceso.id")),
        sa.UniqueConstraint("tenant_id", "origen_id", "destino_id", "tipo"),
    )
    op.create_index("ix_relaciones_documentos_tenant_id", "relaciones_documentos", ["tenant_id"])
    op.create_index("ix_relaciones_documentos_origen_id", "relaciones_documentos", ["origen_id"])
    op.create_index("ix_relaciones_documentos_destino_id", "relaciones_documentos", ["destino_id"])


def downgrade() -> None:
    op.drop_table("relaciones_documentos")
