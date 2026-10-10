"""Cola transaccional de limpieza de archivos.

Revision ID: 0028
Revises: 0027
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "eliminaciones_archivos_pendientes",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("ruta_storage", sa.String(500), nullable=False),
        sa.Column("estado", sa.String(20), server_default="PENDIENTE", nullable=False),
        sa.Column("intentos", sa.Integer(), server_default="0", nullable=False),
        sa.Column("ultimo_error", sa.String(500)),
        sa.Column("completado_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_eliminaciones_archivos_pendientes_tenant_id",
        "eliminaciones_archivos_pendientes",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_eliminaciones_archivos_pendientes_tenant_id",
        table_name="eliminaciones_archivos_pendientes",
    )
    op.drop_table("eliminaciones_archivos_pendientes")
