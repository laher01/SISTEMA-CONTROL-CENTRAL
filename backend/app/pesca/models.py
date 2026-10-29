import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, ahora


class OperacionPesca(Base):
    __tablename__ = "pesca_operaciones"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    fecha_reporte: Mapped[date] = mapped_column(Date, index=True)
    puerto: Mapped[str] = mapped_column(String(100))
    muelle: Mapped[str] = mapped_column(String(200))
    planta: Mapped[str] = mapped_column(String(200))
    armador_reportante: Mapped[str | None] = mapped_column(String(200))
    comprador: Mapped[str | None] = mapped_column(String(200))
    remitente: Mapped[str | None] = mapped_column(String(200))
    destinatario: Mapped[str | None] = mapped_column(String(200))
    facturador: Mapped[str | None] = mapped_column(String(200))
    toneladas_declaradas: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    precio_propuesto: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    precio_confirmado: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    precio_confirmado_por: Mapped[str | None] = mapped_column(String(200))
    precio_confirmado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    descarga_prevista: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    llegada_planta_prevista: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    jefe_bahia: Mapped[str | None] = mapped_column(String(200))
    encargado_muelle: Mapped[str | None] = mapped_column(String(200))
    apuntador: Mapped[str | None] = mapped_column(String(200))
    factura_serie: Mapped[str | None] = mapped_column(String(20))
    factura_correlativo: Mapped[str | None] = mapped_column(String(30))
    factura_emitida_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    factura_emitida_por: Mapped[str | None] = mapped_column(String(200))
    estado_facturacion: Mapped[str] = mapped_column(String(30), default="pendiente")
    responsable_id: Mapped[str] = mapped_column(String(200))
    estado: Mapped[str] = mapped_column(String(30), default="en_descarga", index=True)
    observacion: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora, onupdate=ahora)


class EmbarcacionPesca(Base):
    __tablename__ = "pesca_embarcaciones"
    __table_args__ = (UniqueConstraint("tenant_id", "matricula"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    matricula: Mapped[str] = mapped_column(String(40))
    nombre: Mapped[str] = mapped_column(String(200))
    patron_armador: Mapped[str] = mapped_column(String(200))
    armador: Mapped[str | None] = mapped_column(String(200))
    patron: Mapped[str | None] = mapped_column(String(200))
    intermediario: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class DescargaEmbarcacion(Base):
    __tablename__ = "pesca_descargas_embarcacion"
    __table_args__ = (UniqueConstraint("operacion_id", "embarcacion_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    operacion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pesca_operaciones.id", ondelete="CASCADE"), index=True)
    embarcacion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pesca_embarcaciones.id"), index=True)
    inicio_descarga: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fin_descarga: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    peso_declarado_kg: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class VehiculoPesca(Base):
    __tablename__ = "pesca_vehiculos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    operacion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pesca_operaciones.id", ondelete="CASCADE"), index=True)
    placa: Mapped[str] = mapped_column(String(20))
    tipo: Mapped[str] = mapped_column(String(60))
    chofer: Mapped[str] = mapped_column(String(200))
    estado: Mapped[str] = mapped_column(String(30), default="pendiente_planta", index=True)
    salida_muelle: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_reporte_planta: Mapped[date | None] = mapped_column(Date)
    inicio_planta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fin_planta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    turno: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class CargaEmbarcacionVehiculo(Base):
    __tablename__ = "pesca_cargas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    descarga_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pesca_descargas_embarcacion.id", ondelete="CASCADE"), index=True)
    vehiculo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pesca_vehiculos.id", ondelete="CASCADE"), index=True)
    peso_muelle_kg: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    cajas: Mapped[int | None]
    observacion: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class RegistroPlanta(Base):
    __tablename__ = "pesca_registros_planta"
    __table_args__ = (UniqueConstraint("vehiculo_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    vehiculo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pesca_vehiculos.id", ondelete="CASCADE"), index=True)
    resultado: Mapped[str] = mapped_column(String(20))
    peso_aceptado: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    unidad: Mapped[str] = mapped_column(String(10), default="ton")
    cajas_rechazadas: Mapped[int] = mapped_column(default=0)
    motivo_rechazo: Mapped[str | None] = mapped_column(String(200))
    fecha_finalizacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observacion: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora, onupdate=ahora)


class DocumentoPesca(Base):
    __tablename__ = "pesca_documentos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    operacion_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pesca_operaciones.id", ondelete="CASCADE"), index=True)
    vehiculo_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pesca_vehiculos.id", ondelete="CASCADE"), index=True)
    tipo: Mapped[str] = mapped_column(String(50), index=True)
    nombre: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(100))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    ruta_storage: Mapped[str] = mapped_column(String(500))
    subido_por: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class VinculoDocumentoVehiculo(Base):
    __tablename__ = "pesca_documento_vehiculos"

    documento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pesca_documentos.id", ondelete="CASCADE"), primary_key=True)
    vehiculo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pesca_vehiculos.id", ondelete="CASCADE"), primary_key=True)


class VinculoDocumentoEmbarcacion(Base):
    __tablename__ = "pesca_documento_embarcaciones"

    documento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pesca_documentos.id", ondelete="CASCADE"), primary_key=True)
    embarcacion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pesca_embarcaciones.id", ondelete="CASCADE"), primary_key=True)


class HistorialPesca(Base):
    __tablename__ = "pesca_historial"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    operacion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pesca_operaciones.id", ondelete="CASCADE"), index=True)
    vehiculo_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pesca_vehiculos.id", ondelete="CASCADE"), index=True)
    accion: Mapped[str] = mapped_column(String(60))
    actor: Mapped[str] = mapped_column(String(200))
    detalle: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class MovimientoPesca(Base):
    """Registro monetario trazable; los préstamos personales no tienen operación asociada."""

    __tablename__ = "pesca_movimientos"
    __table_args__ = (
        CheckConstraint(
            "(clase = 'prestamo_personal_bahia' AND operacion_id IS NULL) OR "
            "(clase <> 'prestamo_personal_bahia' AND operacion_id IS NOT NULL)",
            name="prestamo_personal_sin_operacion",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    operacion_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pesca_operaciones.id", ondelete="CASCADE"), index=True)
    clase: Mapped[str] = mapped_column(String(40), index=True)
    pagador: Mapped[str] = mapped_column(String(200))
    beneficiario: Mapped[str] = mapped_column(String(200))
    concepto: Mapped[str] = mapped_column(String(300))
    importe: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    moneda: Mapped[str] = mapped_column(String(3), default="PEN")
    cantidad: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    tarifa_unitaria: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    comprobante_documento_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pesca_documentos.id"))
    registrado_por: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class AbonoMovimientoPesca(Base):
    __tablename__ = "pesca_movimiento_abonos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    movimiento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pesca_movimientos.id", ondelete="CASCADE"), index=True)
    importe: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    tipo: Mapped[str] = mapped_column(String(30))
    registrado_por: Mapped[str] = mapped_column(String(200))
    observacion: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
