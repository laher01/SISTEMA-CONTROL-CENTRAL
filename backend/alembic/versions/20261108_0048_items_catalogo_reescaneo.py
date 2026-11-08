"""Catálogo de categorías y trabajos reanudables de reescaneo de ítems.

Revision ID: 0048
Revises: 0047
"""

import hashlib
import re
import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0048"
down_revision: str | None = "0047"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("productos_items", sa.Column("unidad_base", sa.String(40), nullable=True))
    op.create_table(
        "categorias_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("nombre", sa.String(80), nullable=False),
        sa.Column("nombre_normalizado", sa.String(160), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_por_cuenta_id", sa.Uuid(), sa.ForeignKey("cuentas_acceso.id")),
        sa.UniqueConstraint(
            "tenant_id", "nombre_normalizado", name="uq_categoria_item_tenant_nombre"
        ),
    )
    op.create_index("ix_categorias_items_tenant_id", "categorias_items", ["tenant_id"])

    bind = op.get_bind()
    productos = sa.table(
        "productos_items",
        sa.column("id", sa.Uuid()),
        sa.column("tenant_id", sa.Uuid()),
        sa.column("categoria", sa.String()),
        sa.column("unidad_base", sa.String()),
    )
    lineas = sa.table(
        "lineas_comprobantes_items",
        sa.column("producto_id", sa.Uuid()),
        sa.column("unidad", sa.String()),
    )
    categorias = sa.table(
        "categorias_items",
        sa.column("id", sa.Uuid()),
        sa.column("tenant_id", sa.Uuid()),
        sa.column("nombre", sa.String()),
        sa.column("nombre_normalizado", sa.String()),
        sa.column("activa", sa.Boolean()),
    )
    nombres_por_tenant: dict[uuid.UUID, list[tuple[str, str]]] = {}
    normalizados_por_tenant: dict[uuid.UUID, set[str]] = {}
    for tenant_id, nombre in bind.execute(
        sa.select(productos.c.tenant_id, productos.c.categoria).distinct()
    ):
        limpio = re.sub(r"\s+", " ", (nombre or "POR_CATEGORIZAR")).strip()[:80]
        if not limpio:
            limpio = "POR_CATEGORIZAR"
        normalizado = re.sub(r"\s+", " ", limpio.casefold()).strip()
        usados = normalizados_por_tenant.setdefault(tenant_id, set())
        if normalizado in usados:
            sufijo = hashlib.sha256(limpio.encode("utf-8")).hexdigest()[:16]
            normalizado = f"{normalizado[:140]}~{sufijo}"
        usados.add(normalizado)
        nombres_por_tenant.setdefault(tenant_id, []).append((nombre, normalizado))
    for tenant_id, nombres in nombres_por_tenant.items():
        for nombre_original, normalizado in nombres:
            bind.execute(
                sa.insert(categorias).values(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    nombre=re.sub(r"\s+", " ", (nombre_original or "POR_CATEGORIZAR")).strip()[:80]
                    or "POR_CATEGORIZAR",
                    nombre_normalizado=normalizado,
                    activa=True,
                )
            )

    unidades_unicas = bind.execute(
        sa.select(lineas.c.producto_id, sa.func.min(lineas.c.unidad))
        .group_by(lineas.c.producto_id)
        .having(sa.func.count(sa.distinct(lineas.c.unidad)) == 1)
    )
    for producto_id, unidad in unidades_unicas:
        bind.execute(
            productos.update()
            .where(productos.c.unidad_base.is_(None))
            .where(productos.c.id == producto_id)
            .values(unidad_base=unidad)
        )

    op.create_table(
        "trabajos_reescaneo_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "solicitado_por_cuenta_id",
            sa.Uuid(),
            sa.ForeignKey("cuentas_acceso.id"),
            nullable=False,
        ),
        sa.Column("estado", sa.String(32), nullable=False, server_default="EN_PROCESO"),
        sa.Column("cursor_documento_id", sa.Uuid(), sa.ForeignKey("documentos.id")),
        sa.Column("total_documentos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("procesados", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lineas_nuevas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("requieren_revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errores", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("finalizado_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_trabajos_reescaneo_items_tenant_id", "trabajos_reescaneo_items", ["tenant_id"]
    )
    op.create_index(
        "uq_reescaneo_items_activo_tenant",
        "trabajos_reescaneo_items",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'EN_PROCESO'"),
        sqlite_where=sa.text("estado = 'EN_PROCESO'"),
    )


def downgrade() -> None:
    op.drop_index("uq_reescaneo_items_activo_tenant", table_name="trabajos_reescaneo_items")
    op.drop_table("trabajos_reescaneo_items")
    op.drop_index("ix_categorias_items_tenant_id", table_name="categorias_items")
    op.drop_table("categorias_items")
    op.drop_column("productos_items", "unidad_base")
