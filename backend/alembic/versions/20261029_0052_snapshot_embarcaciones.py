"""conserva los datos de la embarcación asociados a cada operación

Revision ID: 0052
Revises: 0051
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0052"
down_revision: str | None = "0051"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("pesca_descargas_embarcacion", sa.Column("matricula_snapshot", sa.String(40), nullable=True))
    op.add_column("pesca_descargas_embarcacion", sa.Column("nombre_snapshot", sa.String(200), nullable=True))
    op.add_column("pesca_descargas_embarcacion", sa.Column("armador_snapshot", sa.String(200), nullable=True))
    op.add_column("pesca_descargas_embarcacion", sa.Column("patron_snapshot", sa.String(200), nullable=True))
    op.execute(
        """
        UPDATE pesca_descargas_embarcacion
        SET matricula_snapshot = (SELECT matricula FROM pesca_embarcaciones WHERE id = pesca_descargas_embarcacion.embarcacion_id),
            nombre_snapshot = (SELECT nombre FROM pesca_embarcaciones WHERE id = pesca_descargas_embarcacion.embarcacion_id),
            armador_snapshot = (SELECT COALESCE(armador, patron_armador, '') FROM pesca_embarcaciones WHERE id = pesca_descargas_embarcacion.embarcacion_id),
            patron_snapshot = (SELECT COALESCE(patron, '') FROM pesca_embarcaciones WHERE id = pesca_descargas_embarcacion.embarcacion_id)
        """
    )
    with op.batch_alter_table("pesca_descargas_embarcacion") as batch_op:
        for name, length in (
            ("matricula_snapshot", 40),
            ("nombre_snapshot", 200),
            ("armador_snapshot", 200),
            ("patron_snapshot", 200),
        ):
            batch_op.alter_column(name, existing_type=sa.String(length), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("pesca_descargas_embarcacion") as batch_op:
        batch_op.drop_column("patron_snapshot")
        batch_op.drop_column("armador_snapshot")
        batch_op.drop_column("nombre_snapshot")
        batch_op.drop_column("matricula_snapshot")
