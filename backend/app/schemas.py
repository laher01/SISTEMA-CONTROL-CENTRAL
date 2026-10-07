import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.enums import (
    EstadoDocumento,
    EstadoExpediente,
    Moneda,
    RolMiembro,
    TipoAlerta,
    TipoComprobante,
    TipoDocumento,
)

Ruc = Annotated[str, Field(pattern=r"^\d{11}$")]


class Orm(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EmpresaIn(BaseModel):
    ruc: Ruc
    razon_social: str = Field(min_length=1, max_length=300)


class EmpresaOut(Orm):
    id: uuid.UUID
    ruc: str
    razon_social: str
    autorizada: bool
    agente_retencion: bool


class EmpresaActualizar(BaseModel):
    razon_social: str | None = Field(default=None, min_length=1, max_length=300)
    autorizada: bool | None = None
    agente_retencion: bool | None = None


class MiembroIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=1, max_length=200)
    rol: RolMiembro


class MiembroOut(Orm):
    id: uuid.UUID
    codigo: str
    nombre: str
    rol: RolMiembro
    activo: bool


class MiembroActualizar(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=50)
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    rol: RolMiembro | None = None
    activo: bool | None = None


class GestorIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=1, max_length=200)
    usuario_id: uuid.UUID


class GestorOut(Orm):
    id: uuid.UUID
    codigo: str
    nombre: str
    usuario_id: uuid.UUID | None


class GestorActualizar(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=50)
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    usuario_id: uuid.UUID | None = None


class DocumentoOut(Orm):
    id: uuid.UUID
    expediente_id: uuid.UUID | None
    emisor: EmpresaOut | None = None
    receptor: EmpresaOut | None = None
    tipo_documento: TipoDocumento | None
    estado: EstadoDocumento
    sha256: str
    nombre_original: str
    mime_type: str
    tamano_bytes: int
    datos_extraidos: dict[str, object] | None
    formato_origen: str | None
    fecha_emision: date | None = None
    serie: str | None = None
    correlativo: str | None = None
    moneda: Moneda | None = None
    importe_total: Decimal | None = None
    gestor_id: uuid.UUID | None
    usuario_id: uuid.UUID | None
    created_at: datetime


class DocumentoVincular(BaseModel):
    expediente_id: uuid.UUID
    tipo_documento: TipoDocumento


class ProcesamientoLoteOut(BaseModel):
    considerados: int
    relacionados: int
    revision_requerida: int
    fallidos: int


class ExtraccionConfirmar(BaseModel):
    serie: str | None = Field(default=None, pattern=r"^[A-Z0-9]{4}$")
    correlativo: str | None = Field(default=None, pattern=r"^\d{1,8}$")
    ruc_emisor: Ruc | None = None
    ruc_receptor: Ruc | None = None
    razon_social_emisor: str | None = Field(default=None, min_length=1, max_length=300)
    razon_social_receptor: str | None = Field(default=None, min_length=1, max_length=300)
    fecha_emision: date | None = None
    moneda: Moneda | None = None
    importe_total: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    numero_operacion: str | None = Field(default=None, min_length=4, max_length=30)

    @model_validator(mode="after")
    def contiene_algun_campo(self) -> "ExtraccionConfirmar":
        if not self.model_fields_set:
            raise ValueError("Debe confirmar al menos un campo")
        return self


class ExpedienteAsistidoIn(BaseModel):
    tipo_comprobante: TipoComprobante
    razon_social_emisor: str | None = Field(default=None, min_length=1, max_length=300)
    razon_social_receptor: str | None = Field(default=None, min_length=1, max_length=300)
    requiere_guia: bool = True
    gestor_id: uuid.UUID | None = None


class AlertaOut(Orm):
    id: uuid.UUID
    expediente_id: uuid.UUID
    tipo: TipoAlerta
    mensaje: str
    resuelta: bool
    created_at: datetime
    resuelta_at: datetime | None


class ExpedienteIn(BaseModel):
    receptor: EmpresaIn
    emisor: EmpresaIn
    tipo_comprobante: TipoComprobante
    serie: str = Field(pattern=r"^[A-Z0-9]{4}$")
    correlativo: str = Field(pattern=r"^\d{1,8}$")
    fecha_emision: date
    moneda: Moneda = Moneda.PEN
    importe_total: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    requiere_guia: bool = True
    gestor_id: uuid.UUID | None = None


class ExpedienteOut(Orm):
    id: uuid.UUID
    receptor: EmpresaOut
    emisor: EmpresaOut
    tipo_comprobante: TipoComprobante
    serie: str
    correlativo: str
    fecha_emision: date
    moneda: Moneda
    importe_total: Decimal
    requiere_guia: bool
    gestor_id: uuid.UUID | None
    usuario_id: uuid.UUID | None
    estado: EstadoExpediente
    pendiente_aprobacion: bool
    created_at: datetime


class ExpedienteAsistidoOut(BaseModel):
    expediente: ExpedienteOut
    documento: DocumentoOut
    creado: bool


class ExpedienteDetalle(ExpedienteOut):
    documentos: list[DocumentoOut]
    alertas: list[AlertaOut]
    faltantes: list[TipoDocumento]
    fecha_limite: date


class RelacionSugeridaOut(BaseModel):
    expediente: ExpedienteOut
    puntaje: float = Field(ge=0, le=1)
    evidencias: list[str]


class Recalculo(BaseModel):
    actualizados: int


class MontosMoneda(BaseModel):
    moneda: Moneda
    bancarizable: Decimal
    no_bancarizable: Decimal


class DashboardResumen(BaseModel):
    expedientes_total: int
    por_estado: dict[EstadoExpediente, int]
    pendientes_aprobacion: int
    montos: list[MontosMoneda]
    alertas_abiertas: dict[TipoAlerta, int]
    documentos_pendientes: dict[EstadoDocumento, int]


class DashboardDesgloseFila(BaseModel):
    clave: str
    etiqueta: str
    ruc: str | None = None
    expedientes: int
    total_pen: Decimal
    total_usd: Decimal


class DashboardDesglose(BaseModel):
    agrupar_por: str
    filas: list[DashboardDesgloseFila]


class ProduccionFila(BaseModel):
    usuario_id: uuid.UUID | None
    usuario_codigo: str
    usuario_nombre: str
    gestor_id: uuid.UUID | None
    gestor_codigo: str
    gestor_nombre: str
    moneda: Moneda
    expedientes: int
    importe_total: Decimal


class ProduccionResumen(BaseModel):
    filas: list[ProduccionFila]


class ComprasProveedorFila(BaseModel):
    usuario_codigo: str
    gestor_codigo: str
    emisor_ruc: str
    emisor_razon_social: str
    receptor_ruc: str
    receptor_razon_social: str
    moneda: Moneda
    expedientes: int
    importe_total: Decimal


class LoginIn(BaseModel):
    login: str = Field(min_length=1, max_length=100)
    clave: str = Field(min_length=8, max_length=200)


class SesionOut(BaseModel):
    rol: str
    codigo: str
    nombre: str
    miembro_id: uuid.UUID | None
    gestor_id: uuid.UUID | None
    usuario_id: uuid.UUID | None
    cambio_clave_obligatorio: bool


class CambioClaveIn(BaseModel):
    clave_actual: str = Field(min_length=8, max_length=200)
    clave_nueva: str = Field(min_length=10, max_length=200)


class CredencialTemporalOut(BaseModel):
    login: str
    clave_temporal: str


class AltaMiembroOut(BaseModel):
    miembro: MiembroOut
    credencial: CredencialTemporalOut


class AltaGestorOut(BaseModel):
    gestor: GestorOut
    credencial: CredencialTemporalOut


class RegistroFila(BaseModel):
    expediente_id: uuid.UUID
    estado: EstadoExpediente
    usuario_id: uuid.UUID | None
    usuario_codigo: str | None
    usuario_nombre: str | None
    gestor_id: uuid.UUID | None
    gestor_codigo: str | None
    gestor_nombre: str | None
    fecha_emision: date
    tipo_comprobante: TipoComprobante
    serie: str
    correlativo: str
    emisor_ruc: str
    emisor_razon_social: str
    receptor_ruc: str
    receptor_razon_social: str
    moneda: Moneda
    importe_total: Decimal
    documentos_requeridos: list[TipoDocumento]
    documentos_opcionales: list[TipoDocumento]
    puede_eliminar: bool


class RegistroResumen(BaseModel):
    filas: list[RegistroFila]
    total_registros: int
    total_pen: Decimal
    total_usd: Decimal


class AlertaManualIn(BaseModel):
    expediente_id: uuid.UUID | None = None
    destinatario_usuario_id: uuid.UUID | None = None
    destinatario_gestor_id: uuid.UUID | None = None
    para_administracion: bool = True
    asunto: str = Field(min_length=1, max_length=200)
    mensaje: str = Field(min_length=1, max_length=1000)


class AlertaManualOut(Orm):
    id: uuid.UUID
    expediente_id: uuid.UUID | None
    creado_por_codigo: str
    creado_por_rol: str
    destinatario_usuario_id: uuid.UUID | None
    destinatario_gestor_id: uuid.UUID | None
    para_administracion: bool
    asunto: str
    mensaje: str
    resuelta: bool
    created_at: datetime
    resuelta_at: datetime | None


class PermisoConfiguradoIn(BaseModel):
    rol: str = Field(min_length=1, max_length=20)
    permiso: str = Field(min_length=1, max_length=80)
    habilitado: bool


class PermisoConfiguradoOut(Orm):
    id: uuid.UUID
    rol: str
    permiso: str
    habilitado: bool


class PlanLiquidacionIn(BaseModel):
    usuario_id: uuid.UUID
    nombre: str = Field(min_length=1, max_length=120)
    porcentaje: Decimal = Field(ge=0, le=100, max_digits=7, decimal_places=4)
    vigencia_desde: date
    vigencia_hasta: date | None = None


class PlanLiquidacionOut(Orm):
    id: uuid.UUID
    usuario_id: uuid.UUID
    nombre: str
    porcentaje: Decimal
    vigencia_desde: date
    vigencia_hasta: date | None
    activo: bool


class CuentaPagoERPIn(BaseModel):
    usuario_id: uuid.UUID
    titular: str = Field(min_length=1, max_length=200)
    banco: str = Field(min_length=1, max_length=120)
    tipo_cuenta: str = Field(min_length=1, max_length=50)
    moneda: Moneda
    numero_cuenta: str | None = Field(default=None, max_length=80)
    cci: str | None = Field(default=None, max_length=40)
    porcentaje_distribucion: Decimal = Field(
        default=Decimal("100"), ge=0, le=100, max_digits=7, decimal_places=4
    )


class CuentaPagoERPOut(Orm):
    id: uuid.UUID
    usuario_id: uuid.UUID
    titular: str
    banco: str
    tipo_cuenta: str
    moneda: Moneda
    numero_cuenta: str | None
    cci: str | None
    porcentaje_distribucion: Decimal
    activa: bool


class AdelantoERPIn(BaseModel):
    usuario_id: uuid.UUID
    fecha: date
    moneda: Moneda
    monto: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    descripcion: str | None = Field(default=None, max_length=500)


class AdelantoERPOut(Orm):
    id: uuid.UUID
    usuario_id: uuid.UUID
    fecha: date
    moneda: Moneda
    monto: Decimal
    descripcion: str | None
    aplicado: bool


class PagoERPProgramarIn(BaseModel):
    usuario_id: uuid.UUID
    periodo_desde: date
    periodo_hasta: date
    moneda: Moneda
    ajustes: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)
    fecha_programada: date | None = None


class PagoERPActualizarIn(BaseModel):
    estado: str | None = Field(default=None, max_length=20)
    fecha_pago: date | None = None
    voucher_documento_id: uuid.UUID | None = None
    conciliado: bool | None = None


class PagoERPOut(Orm):
    id: uuid.UUID
    usuario_id: uuid.UUID
    plan_id: uuid.UUID | None
    periodo_desde: date
    periodo_hasta: date
    moneda: Moneda
    produccion_total: Decimal
    porcentaje: Decimal
    bruto: Decimal
    adelantos: Decimal
    ajustes: Decimal
    saldo: Decimal
    estado: str
    fecha_programada: date | None
    fecha_pago: date | None
    voucher_documento_id: uuid.UUID | None
    conciliado: bool
    created_at: datetime
