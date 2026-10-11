"""Estado temporal de Google OAuth: nunca conecta ni activa buzones por sí solo.

Revision ID: 0029
Revises: 0028
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "correo_oauth_intentos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("buzon_id", sa.Uuid(), nullable=False),
        sa.Column("cuenta_id", sa.Uuid(), nullable=False),
        sa.Column("state_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("pkce_verifier", sa.String(180), nullable=False),
        sa.Column("vence_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumido_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["buzon_id"], ["correo_buzones.id"]),
        sa.ForeignKeyConstraint(["cuenta_id"], ["cuentas_acceso.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for columna in ("tenant_id", "buzon_id", "cuenta_id"):
        op.create_index(op.f(f"ix_correo_oauth_intentos_{columna}"), "correo_oauth_intentos", [columna])


def downgrade() -> None:
    for columna in ("cuenta_id", "buzon_id", "tenant_id"):
        op.drop_index(op.f(f"ix_correo_oauth_intentos_{columna}"), table_name="correo_oauth_intentos")
    op.drop_table("correo_oauth_intentos")
