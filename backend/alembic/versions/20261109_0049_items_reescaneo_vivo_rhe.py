"""Avance por documento en reescaneo y descripciones largas de ítems.

Revision ID: 0049
Revises: 0048
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0049"
down_revision: str | None = "0048"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "trabajos_reescaneo_items",
        sa.Column(
            "solicitado_por_rol",
            sa.String(length=20),
            nullable=False,
            server_default="ADMINISTRADOR",
        ),
    )
    op.add_column(
        "trabajos_reescaneo_items",
        sa.Column("solicitado_por_miembro_id", sa.Uuid(), sa.ForeignKey("miembros.id")),
    )
    op.add_column(
        "trabajos_reescaneo_items",
        sa.Column("solicitado_por_usuario_id", sa.Uuid(), sa.ForeignKey("miembros.id")),
    )
    op.add_column(
        "trabajos_reescaneo_items",
        sa.Column("solicitado_por_gestor_id", sa.Uuid(), sa.ForeignKey("gestores.id")),
    )
    op.add_column(
        "trabajos_reescaneo_items",
        sa.Column("solicitado_por_codigo", sa.String(length=50), nullable=False, server_default=""),
    )
    op.add_column(
        "trabajos_reescaneo_items",
        sa.Column("documento_actual_id", sa.Uuid(), sa.ForeignKey("documentos.id")),
    )
    op.add_column(
        "trabajos_reescaneo_items",
        sa.Column("documento_actual_started_at", sa.DateTime(timezone=True)),
    )
    op.alter_column(
        "productos_items",
        "descripcion",
        existing_type=sa.String(length=500),
        type_=sa.String(length=2000),
        existing_nullable=False,
    )
    op.alter_column(
        "lineas_comprobantes_items",
        "descripcion_original",
        existing_type=sa.String(length=1000),
        type_=sa.String(length=2000),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "lineas_comprobantes_items",
        "descripcion_original",
        existing_type=sa.String(length=2000),
        type_=sa.String(length=1000),
        existing_nullable=False,
    )
    op.alter_column(
        "productos_items",
        "descripcion",
        existing_type=sa.String(length=2000),
        type_=sa.String(length=500),
        existing_nullable=False,
    )
    op.drop_column("trabajos_reescaneo_items", "documento_actual_started_at")
    op.drop_column("trabajos_reescaneo_items", "documento_actual_id")
    op.drop_column("trabajos_reescaneo_items", "solicitado_por_codigo")
    op.drop_column("trabajos_reescaneo_items", "solicitado_por_gestor_id")
    op.drop_column("trabajos_reescaneo_items", "solicitado_por_usuario_id")
    op.drop_column("trabajos_reescaneo_items", "solicitado_por_miembro_id")
    op.drop_column("trabajos_reescaneo_items", "solicitado_por_rol")
