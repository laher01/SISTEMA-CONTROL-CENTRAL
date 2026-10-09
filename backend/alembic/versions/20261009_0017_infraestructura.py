"""Plano global de infraestructura: ampliación aditiva de 0016.

Revision ID: 0017
Revises: 0016
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "infra_nodos",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("codigo", sa.String(60), nullable=False, unique=True),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("hostname", sa.String(253), nullable=False),
        sa.Column("endpoint_privado", sa.String(500), nullable=False),
        sa.Column("proveedor", sa.String(80), nullable=False),
        sa.Column("region", sa.String(80), nullable=False),
        sa.Column("sistema_operativo", sa.String(100), nullable=False),
        sa.Column("entorno", sa.String(20), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("cpu_nucleos", sa.Integer()),
        sa.Column("ram_bytes", sa.BigInteger()),
        sa.Column("disco_bytes", sa.BigInteger()),
        sa.Column("token_hash", sa.String(64)),
        sa.Column("ultima_conexion", sa.DateTime(timezone=True)),
        sa.Column("version_instalada", sa.String(100)),
        sa.Column("ultimo_despliegue", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "infra_reportes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("nodo_id", sa.Uuid(), sa.ForeignKey("infra_nodos.id"), nullable=False),
        sa.Column("reporte_id", sa.Uuid(), nullable=False),
        sa.Column("contenido_hash", sa.String(64), nullable=False),
        sa.Column("cpu_porcentaje", sa.Float()),
        sa.Column("ram_porcentaje", sa.Float()),
        sa.Column("disco_porcentaje", sa.Float()),
        sa.Column(
            "servicios",
            sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column("version", sa.String(100)),
        sa.UniqueConstraint("nodo_id", "reporte_id"),
    )
    op.create_index("ix_infra_reportes_nodo_id", "infra_reportes", ["nodo_id"])
    op.create_table(
        "infra_versiones",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column("entorno", sa.String(20), nullable=False),
        sa.Column("commit_git", sa.String(40), nullable=False),
        sa.Column("imagen_docker", sa.String(300), nullable=False),
        sa.Column("digest", sa.String(71), nullable=False),
        sa.Column("construida_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validacion", sa.String(20), nullable=False),
        sa.Column("aprobacion", sa.String(20), nullable=False),
        sa.Column("migracion_desde", sa.String(100), nullable=False),
        sa.Column("migracion_hasta", sa.String(100), nullable=False),
        sa.Column("migracion_reversible", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("version", "entorno"),
    )
    op.create_table(
        "infra_tenant_nodo",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False, unique=True),
        sa.Column("nodo_id", sa.Uuid(), sa.ForeignKey("infra_nodos.id"), nullable=False),
    )
    op.create_index("ix_infra_tenant_nodo_nodo_id", "infra_tenant_nodo", ["nodo_id"])
    op.create_table(
        "infra_eventos",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("actor_cuenta_id", sa.Uuid(), sa.ForeignKey("cuentas_acceso.id"), nullable=False),
        sa.Column("correlacion_id", sa.Uuid(), nullable=False),
        sa.Column("accion", sa.String(80), nullable=False),
        sa.Column("recurso_id", sa.Uuid(), nullable=False),
        sa.Column("resultado", sa.String(20), nullable=False),
        sa.Column(
            "datos",
            sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
    )
    op.create_index("ix_infra_eventos_recurso_id", "infra_eventos", ["recurso_id"])


def downgrade() -> None:
    # Solo para entornos aislados: elimina el plano nuevo y nunca datos de negocio.
    for tabla in (
        "infra_eventos",
        "infra_tenant_nodo",
        "infra_versiones",
        "infra_reportes",
        "infra_nodos",
    ):
        op.drop_table(tabla)
