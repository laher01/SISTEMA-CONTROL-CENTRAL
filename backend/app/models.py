import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    MetaData,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.enums import EstadoExpediente

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

JsonDict = dict[str, object]


def ahora() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {
        JsonDict: JSON().with_variant(JSONB(), "postgresql"),
        datetime: DateTime(timezone=True),
    }


class ConId:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class ConTenant:
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)


class ConCreacion:
    created_at: Mapped[datetime] = mapped_column(default=ahora, server_default=func.now())


class Tenant(ConId, ConCreacion, Base):
    __tablename__ = "tenants"

    nombre: Mapped[str] = mapped_column(String(200), unique=True)


class Empresa(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "empresas"
    __table_args__ = (UniqueConstraint("tenant_id", "ruc"),)

    ruc: Mapped[str] = mapped_column(String(11))
    razon_social: Mapped[str] = mapped_column(String(300))
    autorizada: Mapped[bool] = mapped_column(default=False, server_default="false")
    agente_retencion: Mapped[bool] = mapped_column(default=False, server_default="false")
    updated_at: Mapped[datetime] = mapped_column(
        default=ahora, onupdate=ahora, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None]


class Miembro(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "miembros"
    __table_args__ = (UniqueConstraint("tenant_id", "codigo"),)

    codigo: Mapped[str] = mapped_column(String(50))
    nombre: Mapped[str] = mapped_column(String(200))
    rol: Mapped[str] = mapped_column(String(20), index=True)
    activo: Mapped[bool] = mapped_column(default=True, server_default="true")
    deleted_at: Mapped[datetime | None]

    gestores: Mapped[list["Gestor"]] = relationship(back_populates="usuario")


class CuentaAcceso(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "cuentas_acceso"
    __table_args__ = (UniqueConstraint("tenant_id", "login"),)

    login: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(500))
    miembro_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("miembros.id"), index=True)
    gestor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("gestores.id"), index=True)
    activo: Mapped[bool] = mapped_column(default=True, server_default="true")
    cambio_clave_obligatorio: Mapped[bool] = mapped_column(default=True, server_default="true")
    ultimo_acceso: Mapped[datetime | None]
    deleted_at: Mapped[datetime | None]


class SesionAcceso(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "sesiones_acceso"

    cuenta_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cuentas_acceso.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    rol_activo: Mapped[str] = mapped_column(String(20), index=True)
    expira_at: Mapped[datetime]
    ultima_actividad: Mapped[datetime] = mapped_column(default=ahora, server_default=func.now())
    revocada_at: Mapped[datetime | None]


class Gestor(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "gestores"
    __table_args__ = (UniqueConstraint("tenant_id", "codigo"),)

    codigo: Mapped[str] = mapped_column(String(50))
    nombre: Mapped[str] = mapped_column(String(200))
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("miembros.id"), index=True)
    deleted_at: Mapped[datetime | None]

    usuario: Mapped[Miembro | None] = relationship(back_populates="gestores")


class Expediente(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "expedientes"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "receptor_id", "tipo_comprobante", "serie", "correlativo", "emisor_id"
        ),
    )

    receptor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("empresas.id"), index=True)
    emisor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("empresas.id"), index=True)
    tipo_comprobante: Mapped[str] = mapped_column(String(4))
    serie: Mapped[str] = mapped_column(String(4))
    correlativo: Mapped[str] = mapped_column(String(8))
    fecha_emision: Mapped[date] = mapped_column(Date)
    moneda: Mapped[str] = mapped_column(String(3))
    importe_total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    requiere_guia: Mapped[bool] = mapped_column(default=True, server_default="true")
    gestor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("gestores.id"), index=True)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("miembros.id"), index=True)
    estado: Mapped[str] = mapped_column(String(10), default=EstadoExpediente.NARANJA, index=True)
    pendiente_aprobacion: Mapped[bool] = mapped_column(default=False, server_default="false")
    updated_at: Mapped[datetime] = mapped_column(
        default=ahora, onupdate=ahora, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None]

    receptor: Mapped[Empresa] = relationship(foreign_keys=[receptor_id])
    emisor: Mapped[Empresa] = relationship(foreign_keys=[emisor_id])
    documentos: Mapped[list["Documento"]] = relationship(back_populates="expediente")
    alertas: Mapped[list["Alerta"]] = relationship(back_populates="expediente")


class Documento(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "documentos"
    __table_args__ = (UniqueConstraint("tenant_id", "sha256"),)

    expediente_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("expedientes.id"), index=True
    )
    tipo_documento: Mapped[str | None] = mapped_column(String(6))
    estado: Mapped[str] = mapped_column(String(30), index=True)
    sha256: Mapped[str] = mapped_column(String(64))
    nombre_original: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(100))
    tamano_bytes: Mapped[int] = mapped_column(BigInteger)
    ruta_storage: Mapped[str] = mapped_column(String(500))
    datos_extraidos: Mapped[JsonDict | None]
    gestor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("gestores.id"), index=True)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("miembros.id"), index=True)
    deleted_at: Mapped[datetime | None]

    expediente: Mapped[Expediente | None] = relationship(back_populates="documentos")

    @property
    def emisor(self) -> Empresa | None:
        return self.expediente.emisor if self.expediente is not None else None

    @property
    def receptor(self) -> Empresa | None:
        return self.expediente.receptor if self.expediente is not None else None


class Alerta(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "alertas"
    __table_args__ = (UniqueConstraint("expediente_id", "tipo"),)

    expediente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("expedientes.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(40))
    mensaje: Mapped[str] = mapped_column(String(500))
    resuelta: Mapped[bool] = mapped_column(default=False, server_default="false", index=True)
    resuelta_at: Mapped[datetime | None]

    expediente: Mapped[Expediente] = relationship(back_populates="alertas")


class Auditoria(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "auditoria"

    accion: Mapped[str] = mapped_column(String(60))
    entidad: Mapped[str] = mapped_column(String(40))
    entidad_id: Mapped[uuid.UUID] = mapped_column(index=True)
    datos: Mapped[JsonDict | None]
