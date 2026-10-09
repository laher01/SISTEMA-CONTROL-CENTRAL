"""Operaciones autorizadas, leases, versiones completas y backups cifrados.

Revision ID: 0018
Revises: 0017
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("infra_nodos", sa.Column("migracion_instalada", sa.String(100)))
    op.add_column("infra_reportes", sa.Column("migracion", sa.String(100)))
    op.add_column("infra_versiones", sa.Column("imagen_frontend", sa.String(300)))
    op.add_column("infra_versiones", sa.Column("digest_frontend", sa.String(71)))
    op.create_table(
        "infra_operaciones",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("nodo_id", sa.Uuid(), sa.ForeignKey("infra_nodos.id"), nullable=False),
        sa.Column("solicitud_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), sa.ForeignKey("infra_versiones.id")),
        sa.Column("actor_cuenta_id", sa.Uuid(), sa.ForeignKey("cuentas_acceso.id"), nullable=False),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("grupo_id", sa.Uuid()),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("contenido_hash", sa.String(64), nullable=False),
        sa.Column("parametros", sa.JSON().with_variant(JSONB(), "postgresql"), nullable=False),
        sa.Column("resultado", sa.JSON().with_variant(JSONB(), "postgresql")),
        sa.Column("lease_hash", sa.String(64)),
        sa.Column("lease_hasta", sa.DateTime(timezone=True)),
        sa.Column("iniciada_at", sa.DateTime(timezone=True)),
        sa.Column("finalizada_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("nodo_id", "solicitud_id"),
    )
    op.create_index("ix_infra_operaciones_nodo_id", "infra_operaciones", ["nodo_id"])
    op.create_index("ix_infra_operaciones_grupo_id", "infra_operaciones", ["grupo_id"])
    op.create_table(
        "infra_backups",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("nodo_id", sa.Uuid(), sa.ForeignKey("infra_nodos.id"), nullable=False),
        sa.Column(
            "operacion_id",
            sa.Uuid(),
            sa.ForeignKey("infra_operaciones.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("version", sa.String(100)),
        sa.Column("migracion", sa.String(100)),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("objeto", sa.String(200), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("bytes", sa.BigInteger(), nullable=False),
        sa.Column("retencion_dias", sa.Integer(), nullable=False),
        sa.Column("restauracion_verificada_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_infra_backups_nodo_id", "infra_backups", ["nodo_id"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
            CREATE FUNCTION infra_proteger_evento() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                RAISE EXCEPTION 'Los eventos de infraestructura son inmutables';
            END;
            $$;
        """)
        op.execute("""
            CREATE TRIGGER infra_eventos_inmutables
            BEFORE UPDATE OR DELETE ON infra_eventos
            FOR EACH ROW EXECUTE FUNCTION infra_proteger_evento();
        """)
    elif op.get_bind().dialect.name == "sqlite":
        for accion in ("UPDATE", "DELETE"):
            op.execute(f"""
                CREATE TRIGGER infra_eventos_inmutables_{accion.lower()}
                BEFORE {accion} ON infra_eventos BEGIN
                    SELECT RAISE(ABORT, 'Los eventos de infraestructura son inmutables');
                END;
            """)


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER infra_eventos_inmutables ON infra_eventos")
        op.execute("DROP FUNCTION infra_proteger_evento()")
    elif op.get_bind().dialect.name == "sqlite":
        op.execute("DROP TRIGGER infra_eventos_inmutables_update")
        op.execute("DROP TRIGGER infra_eventos_inmutables_delete")
    op.drop_table("infra_backups")
    op.drop_table("infra_operaciones")
    op.drop_column("infra_versiones", "digest_frontend")
    op.drop_column("infra_versiones", "imagen_frontend")
    op.drop_column("infra_reportes", "migracion")
    op.drop_column("infra_nodos", "migracion_instalada")
