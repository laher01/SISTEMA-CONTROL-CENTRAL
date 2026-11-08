"""Entidades persistentes de Contabilidad de Ítems, aisladas de Expediente."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, ConCreacion, ConId, ConTenant


class ProductoItem(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "productos_items"
    __table_args__ = (UniqueConstraint("tenant_id", "clave_catalogo"),)

    clave_catalogo: Mapped[str] = mapped_column(String(300))
    descripcion: Mapped[str] = mapped_column(String(500))
    categoria: Mapped[str] = mapped_column(String(80), default="POR_CATEGORIZAR")
    unidad_base: Mapped[str | None] = mapped_column(String(40))
    clasificacion_confirmada: Mapped[bool] = mapped_column(default=False)
    activo: Mapped[bool] = mapped_column(default=True)


class CategoriaItem(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "categorias_items"
    __table_args__ = (
        UniqueConstraint("tenant_id", "nombre_normalizado", name="uq_categoria_item_tenant_nombre"),
    )

    nombre: Mapped[str] = mapped_column(String(80))
    nombre_normalizado: Mapped[str] = mapped_column(String(160))
    activa: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    creado_por_cuenta_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cuentas_acceso.id"))


class TrabajoReescaneoItems(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "trabajos_reescaneo_items"
    __table_args__ = (
        Index(
            "uq_reescaneo_items_activo_tenant",
            "tenant_id",
            unique=True,
            postgresql_where=text("estado = 'EN_PROCESO'"),
            sqlite_where=text("estado = 'EN_PROCESO'"),
        ),
    )

    solicitado_por_cuenta_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cuentas_acceso.id"))
    estado: Mapped[str] = mapped_column(
        String(32), default="EN_PROCESO", server_default="EN_PROCESO"
    )
    cursor_documento_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("documentos.id"))
    total_documentos: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    procesados: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    lineas_nuevas: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    requieren_revision: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    errores: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    finalizado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LineaComprobanteItem(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "lineas_comprobantes_items"
    __table_args__ = (UniqueConstraint("tenant_id", "documento_id", "numero_linea"),)

    documento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documentos.id"), index=True)
    producto_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("productos_items.id"), index=True)
    numero_linea: Mapped[int] = mapped_column(Integer)
    descripcion_original: Mapped[str] = mapped_column(String(1000))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    unidad: Mapped[str] = mapped_column(String(40))
    importe_linea: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))


class AuditoriaFacturaItem(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "auditorias_facturas_items"

    expediente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("expedientes.id"), index=True)
    producto_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("productos_items.id"))
    estado: Mapped[str] = mapped_column(String(40), default="OBSERVADA", index=True)
    motivo: Mapped[str] = mapped_column(String(1000))
    solicitado_por_cuenta_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cuentas_acceso.id"))
    aprobado_por_cuenta_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cuentas_acceso.id")
    )
