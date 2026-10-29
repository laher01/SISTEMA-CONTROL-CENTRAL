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
    precio_acuerdo_embarcacion_confirmado: Mapped[bool] = mapped_column(default=False)
    precio_acuerdo_embarcacion_confirmado_por: Mapped[str | None] = mapped_column(String(200))
    precio_acuerdo_embarcacion_confirmado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    precio_confirmado: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    precio_confirmado_por: Mapped[str | None] = mapped_column(String(200))
    precio_confirmado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    modalidad_pago_cuadrilla: Mapped[str | None] = mapped_column(String(20))
    monto_pago_cuadrilla: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    descarga_prevista: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    llegada_planta_prevista: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    jefe_bahia: Mapped[str | None] = mapped_column(String(200))
    encargado_muelle: Mapped[str | None] = mapped_column(String(200))
    apuntador: Mapped[str | None] = mapped_column(String(200))
    responsable_pesaje_muelle: Mapped[str | None] = mapped_column(String(40))
    responsable_pesaje_muelle_cuenta_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cuentas_acceso.id", ondelete="SET NULL"))
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

    @property
    def precio_acuerdo_aceptado(self) -> bool:
        return self.precio_confirmado is not None

    @property
    def precio_ajuste_pendiente(self) -> bool:
        return (
            self.precio_confirmado is not None
            and self.precio_propuesto is not None
            and self.precio_confirmado != self.precio_propuesto
        )


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
    matricula_snapshot: Mapped[str] = mapped_column(String(40))
    nombre_snapshot: Mapped[str] = mapped_column(String(200))
    armador_snapshot: Mapped[str] = mapped_column(String(200))
    patron_snapshot: Mapped[str] = mapped_column(String(200))
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
    llegada_planta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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


class AsignacionCuadrillaPesca(Base):
    __tablename__ = "pesca_asignaciones_cuadrilla"
    __table_args__ = (UniqueConstraint("tenant_id", "operacion_id", "actividad", "nombre_integrante"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    operacion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pesca_operaciones.id", ondelete="CASCADE"), index=True)
    actividad: Mapped[str] = mapped_column(String(20), index=True)
    nombre_integrante: Mapped[str] = mapped_column(String(200))
    activa: Mapped[bool] = mapped_column(default=True)
    monto_pago: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    asignado_por_cuenta_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cuentas_acceso.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora, onupdate=ahora)


class ActividadCuadrillaPesca(Base):
    __tablename__ = "pesca_actividades_cuadrilla"
    __table_args__ = (UniqueConstraint("tenant_id", "vehiculo_id", "actividad"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    operacion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pesca_operaciones.id", ondelete="CASCADE"), index=True)
    vehiculo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pesca_vehiculos.id", ondelete="CASCADE"), index=True)
    actividad: Mapped[str] = mapped_column(String(20), index=True)
    estado: Mapped[str] = mapped_column(String(20), default="en_proceso")
    cajas: Mapped[int | None]
    hielo_kg: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    verificacion_visual: Mapped[bool | None]
    contaminacion_detectada: Mapped[bool | None]
    revision_final: Mapped[bool | None]
    observacion: Mapped[str | None] = mapped_column(Text)
    actor_cuenta_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cuentas_acceso.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora, onupdate=ahora)


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
    __table_args__ = (
        CheckConstraint("estado_revision IN ('PENDIENTE', 'VERIFICADO', 'OBSERVADO')", name="ck_pesca_documentos_estado_revision_valido"),
        CheckConstraint("version >= 1", name="ck_pesca_documentos_version_positiva"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    operacion_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pesca_operaciones.id", ondelete="CASCADE"), index=True)
    vehiculo_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pesca_vehiculos.id", ondelete="CASCADE"), index=True)
    tipo: Mapped[str] = mapped_column(String(50), index=True)
    etapa: Mapped[str] = mapped_column(String(30), default="GENERAL", index=True)
    nombre: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(100))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    ruta_storage: Mapped[str] = mapped_column(String(500))
    subido_por: Mapped[str] = mapped_column(String(200))
    estado_revision: Mapped[str] = mapped_column(String(20), default="PENDIENTE", index=True)
    observacion_revision: Mapped[str | None] = mapped_column(Text)
    revisado_por: Mapped[str | None] = mapped_column(String(200))
    revisado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(default=1)
    vigente: Mapped[bool] = mapped_column(default=True, index=True)
    documento_anterior_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pesca_documentos.id", ondelete="SET NULL"))
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
    tipo_gasto: Mapped[str | None] = mapped_column(String(30))
    tipo_comprobante: Mapped[str | None] = mapped_column(String(30))
    motivo_boleta_muelle: Mapped[str | None] = mapped_column(Text)
    importe: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    moneda: Mapped[str] = mapped_column(String(3), default="PEN")
    cantidad: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    tarifa_unitaria: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    comprobante_documento_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pesca_documentos.id"))
    voucher_documento_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pesca_documentos.id"))
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
    voucher_documento_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pesca_documentos.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class AsignacionRolPesca(Base):
    __tablename__ = "pesca_asignaciones_rol"
    __table_args__ = (UniqueConstraint("tenant_id", "cuenta_id", "rol"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    cuenta_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cuentas_acceso.id", ondelete="CASCADE"), index=True)
    rol: Mapped[str] = mapped_column(String(40), index=True)
    activa: Mapped[bool] = mapped_column(default=True)
    asignado_por_cuenta_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cuentas_acceso.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora, onupdate=ahora)


class AuditoriaRolPesca(Base):
    __tablename__ = "pesca_auditoria_roles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    actor_cuenta_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cuentas_acceso.id"))
    cuenta_objetivo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cuentas_acceso.id"))
    rol: Mapped[str] = mapped_column(String(40))
    accion: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
