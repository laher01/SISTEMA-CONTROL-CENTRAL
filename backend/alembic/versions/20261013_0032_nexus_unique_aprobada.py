"""Enforce one approved NEXUS formula per tenant and user.

Revision ID: 0032
Revises: 0031
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0032"
down_revision: str | None = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_nexus_formula_aprobada_usuario",
        "formulas_pago_nexus",
        ["tenant_id", "usuario_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'APROBADA'"),
    )


def downgrade() -> None:
    op.drop_index("uq_nexus_formula_aprobada_usuario", table_name="formulas_pago_nexus")
