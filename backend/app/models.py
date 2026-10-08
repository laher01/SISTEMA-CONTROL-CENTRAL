import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
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
    tipo_relacion: Mapped[str] = mapped_column(
        String(20), default="SIN_CLASIFICAR", server_default="SIN_CLASIFICAR", index=True
    )
    clasificacion_proveedor: Mapped[str | None] = mapped_column(String(1), index=True)
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
    porcentaje_produccion: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    creado_por_cuenta_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cuentas_acceso.id"), index=True
    )
    activo: Mapped[bool] = mapped_column(default=True, server_default="true")
    deleted_at: Mapped[datetime | None]

    gestores: Mapped[list["Gestor"]] = relationship(back_populates="usuario")


class CuentaAcceso(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "cuentas_acceso"
    __table_args__ = (
        UniqueConstraint("tenant_id", "login"),
        UniqueConstraint("tenant_id", "email"),
    )

    login: Mapped[str] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(320), index=True)
    email_verificado: Mapped[bool] = mapped_column(default=False, server_default="false")
    password_hash: Mapped[str] = mapped_column(String(500))
    miembro_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("miembros.id"), index=True)
    gestor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("gestores.id"), index=True)
    activo: Mapped[bool] = mapped_column(default=True, server_default="true")
    cambio_clave_obligatorio: Mapped[bool] = mapped_column(default=True, server_default="true")
    intentos_fallidos: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    bloqueado_hasta: Mapped[datetime | None]
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
    creado_por_cuenta_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cuentas_acceso.id"), index=True
    )
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
    creado_por_cuenta_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cuentas_acceso.id"), index=True
    )
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
    formato_origen: Mapped[str | None] = mapped_column(String(30), index=True)
    gestor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("gestores.id"), index=True)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("miembros.id"), index=True)
    creado_por_cuenta_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cuentas_acceso.id"), index=True
    )
    deleted_at: Mapped[datetime | None]

    expediente: Mapped[Expediente | None] = relationship(back_populates="documentos")

    @property
    def fecha_emision(self) -> date | None:
        return self.expediente.fecha_emision if self.expediente is not None else None

    @property
    def serie(self) -> str | None:
        return self.expediente.serie if self.expediente is not None else None

    @property
    def correlativo(self) -> str | None:
        return self.expediente.correlativo if self.expediente is not None else None

    @property
    def moneda(self) -> str | None:
        return self.expediente.moneda if self.expediente is not None else None

    @property
    def importe_total(self) -> Decimal | None:
        return self.expediente.importe_total if self.expediente is not None else None

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


class PerfilExtraccion(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "perfiles_extraccion"
    __table_args__ = (UniqueConstraint("tenant_id", "ruc", "tipo_parte", "formato"),)

    ruc: Mapped[str] = mapped_column(String(11), index=True)
    tipo_parte: Mapped[str] = mapped_column(String(10))
    formato: Mapped[str] = mapped_column(String(30), index=True)
    razon_social: Mapped[str] = mapped_column(String(300))
    confianza: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.95"))
    usos: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    activo: Mapped[bool] = mapped_column(default=True, server_default="true")
    updated_at: Mapped[datetime] = mapped_column(
        default=ahora, onupdate=ahora, server_default=func.now()
    )


class CorreccionIA(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "correcciones_ia"

    documento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documentos.id"), index=True)
    actor_codigo: Mapped[str] = mapped_column(String(100))
    actor_rol: Mapped[str] = mapped_column(String(20))
    formato: Mapped[str | None] = mapped_column(String(30), index=True)
    resultado_original: Mapped[JsonDict | None]
    resultado_corregido: Mapped[JsonDict]
    motivo: Mapped[str | None] = mapped_column(String(500))


class AlertaManual(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "alertas_manuales"

    expediente_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("expedientes.id"), index=True
    )
    creado_por_codigo: Mapped[str] = mapped_column(String(100))
    creado_por_rol: Mapped[str] = mapped_column(String(20))
    destinatario_usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("miembros.id"), index=True
    )
    destinatario_gestor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("gestores.id"), index=True
    )
    para_administracion: Mapped[bool] = mapped_column(default=True, server_default="true")
    asunto: Mapped[str] = mapped_column(String(200))
    mensaje: Mapped[str] = mapped_column(String(1000))
    resuelta: Mapped[bool] = mapped_column(default=False, server_default="false", index=True)
    resuelta_at: Mapped[datetime | None]


class ConfiguracionAcceso(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "configuracion_acceso"
    __table_args__ = (UniqueConstraint("tenant_id"),)

    registro_publico: Mapped[bool] = mapped_column(default=False, server_default="false")
    requiere_aprobacion: Mapped[bool] = mapped_column(default=True, server_default="true")
    solo_correos_autorizados: Mapped[bool] = mapped_column(default=True, server_default="true")
    requiere_email_verificado: Mapped[bool] = mapped_column(default=False, server_default="false")
    proveedor_email_configurado: Mapped[bool] = mapped_column(default=False, server_default="false")
    acceso_cloudflare_activo: Mapped[bool] = mapped_column(default=True, server_default="true")
    duracion_sesion_horas: Mapped[int] = mapped_column(Integer, default=12, server_default="12")
    intentos_fallidos_max: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    bloqueo_minutos: Mapped[int] = mapped_column(Integer, default=15, server_default="15")
    clave_min_longitud: Mapped[int] = mapped_column(Integer, default=10, server_default="10")
    clave_requiere_letra: Mapped[bool] = mapped_column(default=True, server_default="true")
    clave_requiere_numero: Mapped[bool] = mapped_column(default=True, server_default="true")
    updated_at: Mapped[datetime] = mapped_column(
        default=ahora, onupdate=ahora, server_default=func.now()
    )


class CorreoAutorizado(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "correos_autorizados"
    __table_args__ = (UniqueConstraint("tenant_id", "email"),)

    email: Mapped[str] = mapped_column(String(320), index=True)
    rol_sugerido: Mapped[str | None] = mapped_column(String(20))
    activo: Mapped[bool] = mapped_column(default=True, server_default="true")


class SolicitudAcceso(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "solicitudes_acceso"
    __table_args__ = (UniqueConstraint("tenant_id", "email"),)

    email: Mapped[str] = mapped_column(String(320), index=True)
    nombre: Mapped[str] = mapped_column(String(200))
    codigo_solicitado: Mapped[str] = mapped_column(String(50))
    estado: Mapped[str] = mapped_column(String(30), default="PENDIENTE", index=True)
    rol_asignado: Mapped[str | None] = mapped_column(String(20))
    resuelta_at: Mapped[datetime | None]


class PermisoConfigurado(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "permisos_configurados"
    __table_args__ = (UniqueConstraint("tenant_id", "rol", "permiso"),)

    rol: Mapped[str] = mapped_column(String(20), index=True)
    permiso: Mapped[str] = mapped_column(String(80), index=True)
    habilitado: Mapped[bool] = mapped_column(default=False, server_default="false")


class PlanLiquidacion(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "planes_liquidacion"

    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("miembros.id"), index=True)
    creado_por_cuenta_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cuentas_acceso.id"), index=True
    )
    nombre: Mapped[str] = mapped_column(String(120))
    porcentaje: Mapped[Decimal] = mapped_column(Numeric(7, 4))
    vigencia_desde: Mapped[date] = mapped_column(Date)
    vigencia_hasta: Mapped[date | None] = mapped_column(Date)
    activo: Mapped[bool] = mapped_column(default=True, server_default="true")


class CuentaPagoERP(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "cuentas_pago_erp"

    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("miembros.id"), index=True)
    creado_por_cuenta_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cuentas_acceso.id"), index=True
    )
    titular: Mapped[str] = mapped_column(String(200))
    banco: Mapped[str] = mapped_column(String(120))
    tipo_cuenta: Mapped[str] = mapped_column(String(50))
    moneda: Mapped[str] = mapped_column(String(3))
    numero_cuenta: Mapped[str | None] = mapped_column(String(80))
    cci: Mapped[str | None] = mapped_column(String(40))
    porcentaje_distribucion: Mapped[Decimal] = mapped_column(Numeric(7, 4), default=Decimal("100"))
    activa: Mapped[bool] = mapped_column(default=True, server_default="true")


class AdelantoERP(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "adelantos_erp"

    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("miembros.id"), index=True)
    creado_por_cuenta_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cuentas_acceso.id"), index=True
    )
    fecha: Mapped[date] = mapped_column(Date)
    moneda: Mapped[str] = mapped_column(String(3))
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    descripcion: Mapped[str | None] = mapped_column(String(500))
    aplicado: Mapped[bool] = mapped_column(default=False, server_default="false")


class AbonoClienteERP(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "abonos_cliente_erp"

    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("empresas.id"), index=True)
    creado_por_cuenta_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cuentas_acceso.id"), index=True
    )
    fecha: Mapped[date] = mapped_column(Date, index=True)
    moneda: Mapped[str] = mapped_column(String(3), index=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    descripcion: Mapped[str | None] = mapped_column(String(500))
    referencia: Mapped[str | None] = mapped_column(String(120))


class PagoERP(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "pagos_erp"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "usuario_id",
            "periodo_desde",
            "periodo_hasta",
            "moneda",
        ),
    )

    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("miembros.id"), index=True)
    creado_por_cuenta_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cuentas_acceso.id"), index=True
    )
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("planes_liquidacion.id"), index=True
    )
    periodo_desde: Mapped[date] = mapped_column(Date)
    periodo_hasta: Mapped[date] = mapped_column(Date)
    moneda: Mapped[str] = mapped_column(String(3))
    produccion_total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    porcentaje: Mapped[Decimal] = mapped_column(Numeric(7, 4))
    bruto: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    adelantos: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    ajustes: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    saldo: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    estado: Mapped[str] = mapped_column(String(20), default="PROGRAMADO", index=True)
    fecha_programada: Mapped[date | None] = mapped_column(Date)
    fecha_pago: Mapped[date | None] = mapped_column(Date)
    voucher_documento_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documentos.id"), index=True
    )
    conciliado: Mapped[bool] = mapped_column(default=False, server_default="false")


class Auditoria(ConId, ConTenant, ConCreacion, Base):
    __tablename__ = "auditoria"

    accion: Mapped[str] = mapped_column(String(60))
    entidad: Mapped[str] = mapped_column(String(40))
    entidad_id: Mapped[uuid.UUID] = mapped_column(index=True)
    datos: Mapped[JsonDict | None]
