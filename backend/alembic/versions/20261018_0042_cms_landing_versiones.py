"""Base persistente de revisiones CMS globales sin alterar landing activa.

Revision ID: 0042
Revises: 0041
"""
import sqlalchemy as sa
from alembic import op

revision: str = "0042"
down_revision: str | None = "0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cms_landing_revision",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(length=24), nullable=False),
        sa.Column("contenido", sa.JSON(), nullable=False),
        sa.Column("actualizado_por", sa.Uuid(), sa.ForeignKey("cuentas_acceso.id")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("id = 1", name="cms_landing_revision_unica"),
    )
    op.create_table(
        "cms_landing_evento",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("version_anterior", sa.Integer(), nullable=False),
        sa.Column("version_nueva", sa.Integer(), nullable=False),
        sa.Column("anterior", sa.String(length=24), nullable=False),
        sa.Column("nuevo", sa.String(length=24), nullable=False),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("cuentas_acceso.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("version_nueva", name="uq_cms_landing_evento_version"),
    )


def downgrade() -> None:
    op.drop_table("cms_landing_evento")
    op.drop_table("cms_landing_revision")
