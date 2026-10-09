import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

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


TipoRelacionEmpresa = Literal["PROVEEDOR", "CLIENTE", "AMBOS", "SIN_CLASIFICAR"]
ClasificacionProveedor = Literal["A", "B"]


class EmpresaOut(Orm):
    id: uuid.UUID
    ruc: str
    razon_social: str
    tipo_relacion: TipoRelacionEmpresa
    clasificacion_proveedor: ClasificacionProveedor | None
    autorizada: bool
    agente_retencion: bool


class EmpresaUsuarioOut(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str


class EmpresaListadoOut(EmpresaOut):
    usuarios: list[EmpresaUsuarioOut] = Field(default_factory=list)


class EmpresaActualizar(BaseModel):
    ruc: Ruc | None = None
    razon_social: str | None = Field(default=None, min_length=1, max_length=300)
    tipo_relacion: TipoRelacionEmpresa | None = None
    clasificacion_proveedor: ClasificacionProveedor | None = None
    autorizada: bool | None = None
    agente_retencion: bool | None = None


class EmpresasEliminarIn(BaseModel):
    empresa_ids: list[uuid.UUID] = Field(min_length=1)


class EmpresasEliminarOut(BaseModel):
    eliminadas: int


class ImpresionExpedientesIn(BaseModel):
    expediente_ids: list[uuid.UUID] = Field(min_length=1, max_length=1000)


class MiembroIn(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=50)
    nombre: str = Field(min_length=1, max_length=200)
    rol: RolMiembro
    porcentaje_produccion: Decimal | None = Field(
        default=None, ge=0, le=100, max_digits=7, decimal_places=4
    )


class MiembroOut(Orm):
    id: uuid.UUID
    responsable_id: uuid.UUID | None
    codigo: str
    nombre: str
    rol: RolMiembro
    porcentaje_produccion: Decimal | None
    activo: bool


class MiembroActualizar(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=50)
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    rol: RolMiembro | None = None
    porcentaje_produccion: Decimal | None = Field(
        default=None, ge=0, le=100, max_digits=7, decimal_places=4
    )
    activo: bool | None = None


class GestorIn(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=50)
    nombre: str = Field(min_length=1, max_length=200)
    usuario_id: uuid.UUID


class GestorOut(Orm):
    porcentaje_comision: Decimal | None = None
    id: uuid.UUID
    codigo: str
    nombre: str
    usuario_id: uuid.UUID | None


class GestorActualizar(BaseModel):
    porcentaje_comision: Decimal | None = Field(
        default=None, ge=0, le=100, max_digits=7, decimal_places=4
    )
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
    espacio: str | None = Field(default=None, min_length=1, max_length=200)
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
    tipo_empresa: str | None = None
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
    documentos_presentes: list[TipoDocumento]
    documentos_faltantes: list[TipoDocumento]
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


class CarteraClienteFila(BaseModel):
    cliente_id: uuid.UUID
    ruc: str
    razon_social: str
    agente_retencion: bool
    moneda: Moneda
    compras_mes: Decimal
    saldo_anterior: Decimal
    abonos_mes: Decimal
    saldo_total: Decimal


class CarteraClientesResumen(BaseModel):
    mes: str
    moneda: Moneda
    filas: list[CarteraClienteFila]
    total_compras_mes: Decimal
    total_saldo_anterior: Decimal
    total_abonos_mes: Decimal
    total_saldo: Decimal


class AbonoClienteERPIn(BaseModel):
    cliente_id: uuid.UUID
    fecha: date
    moneda: Moneda
    monto: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    descripcion: str | None = Field(default=None, max_length=500)
    referencia: str | None = Field(default=None, max_length=120)


class AbonoClienteERPOut(Orm):
    id: uuid.UUID
    cliente_id: uuid.UUID
    fecha: date
    moneda: Moneda
    monto: Decimal
    descripcion: str | None
    referencia: str | None
    created_at: datetime


class AgenteRetencionIn(BaseModel):
    agente_retencion: bool


class PedidoGerenciaIn(BaseModel):
    responsable_id: uuid.UUID | None = None
    cliente_id: uuid.UUID
    periodo_mes: date
    moneda: Moneda
    monto_solicitado: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    modalidad: Literal["SIN_RESTRICCION", "POR_PEDIDO"] = "POR_PEDIDO"
    modo_distribucion: Literal["MANUAL", "SEMIASISTIDA", "AUTOMATICA"] = "MANUAL"
    observacion: str | None = Field(default=None, max_length=500)


class PedidoGerenciaActualizarIn(BaseModel):
    responsable_id: uuid.UUID | None = None
    monto_solicitado: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    modalidad: Literal["SIN_RESTRICCION", "POR_PEDIDO"] | None = None
    modo_distribucion: Literal["MANUAL", "SEMIASISTIDA", "AUTOMATICA"] | None = None
    estado: Literal["ACTIVO", "CERRADO", "CANCELADO"] | None = None
    observacion: str | None = Field(default=None, max_length=500)


class AsignacionPedidoGerenciaIn(BaseModel):
    usuario_id: uuid.UUID
    gestor_id: uuid.UUID | None = None
    proveedor_id: uuid.UUID | None = None
    monto_asignado: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


class AsignacionPedidoGerenciaOut(BaseModel):
    id: uuid.UUID
    usuario_id: uuid.UUID
    usuario_codigo: str
    usuario_nombre: str
    gestor_id: uuid.UUID | None
    gestor_codigo: str | None
    gestor_nombre: str | None
    proveedor_id: uuid.UUID | None
    proveedor_ruc: str | None
    proveedor_razon_social: str | None
    monto_asignado: Decimal
    ejecutado: Decimal
    saldo: Decimal


class PedidoGerenciaOut(BaseModel):
    id: uuid.UUID
    responsable_id: uuid.UUID | None = None
    cliente_id: uuid.UUID
    cliente_ruc: str
    cliente_razon_social: str
    periodo_mes: date
    moneda: Moneda
    monto_solicitado: Decimal
    monto_asignado: Decimal
    monto_ejecutado: Decimal
    saldo_pendiente: Decimal
    exceso: Decimal
    avance_porcentaje: Decimal
    modalidad: str
    modo_distribucion: str
    estado: str
    observacion: str | None
    concentracion_maxima_proveedor: Decimal
    proveedor_mayor_concentracion: str | None
    asignaciones: list[AsignacionPedidoGerenciaOut] = Field(default_factory=list)


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


class FiltroOpcion(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    usuario_id: uuid.UUID | None = None
    porcentaje_produccion: Decimal | None = None


class RegistroOpciones(BaseModel):
    usuarios: list[FiltroOpcion]
    gestores: list[FiltroOpcion]


class NexusFuente(BaseModel):
    titulo: str
    url: str | None = None
    tipo: str


class NexusChatIn(BaseModel):
    mensaje: str = Field(min_length=1, max_length=2000)
    ruta: str = Field(default="/", max_length=500)
    expediente_id: uuid.UUID | None = None


class NexusChatOut(BaseModel):
    respuesta: str
    accion: str
    fuentes: list[NexusFuente] = []
    datos: dict[str, object] = {}
    internet_usado: bool = False
    requiere_configuracion_externa: bool = False


class NexusEstadoOut(BaseModel):
    asistente_activo: bool
    consulta_ruc_externa: bool
    busqueda_internet: bool
    fuente_oficial_preferida: str


class ConfiguracionAccesoOut(Orm):
    id: uuid.UUID
    registro_publico: bool
    requiere_aprobacion: bool
    solo_correos_autorizados: bool
    requiere_email_verificado: bool
    proveedor_email_configurado: bool
    acceso_cloudflare_activo: bool
    duracion_sesion_horas: int
    intentos_fallidos_max: int
    bloqueo_minutos: int
    clave_min_longitud: int
    clave_requiere_letra: bool
    clave_requiere_numero: bool


class ConfiguracionAccesoIn(BaseModel):
    registro_publico: bool
    requiere_aprobacion: bool
    solo_correos_autorizados: bool
    requiere_email_verificado: bool
    acceso_cloudflare_activo: bool
    duracion_sesion_horas: int = Field(ge=1, le=168)
    intentos_fallidos_max: int = Field(ge=1, le=20)
    bloqueo_minutos: int = Field(ge=1, le=1440)
    clave_min_longitud: int = Field(ge=8, le=128)
    clave_requiere_letra: bool
    clave_requiere_numero: bool


class CorreoAutorizadoIn(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    rol_sugerido: RolMiembro | None = None


class CorreoAutorizadoOut(Orm):
    id: uuid.UUID
    email: str
    rol_sugerido: str | None
    activo: bool
    created_at: datetime


class SolicitudAccesoIn(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    nombre: str = Field(min_length=2, max_length=200)
    codigo_solicitado: str = Field(min_length=2, max_length=50)


class SolicitudAccesoResolverIn(BaseModel):
    aprobar: bool
    rol: RolMiembro | None = None


class SolicitudAccesoOut(Orm):
    id: uuid.UUID
    email: str
    nombre: str
    codigo_solicitado: str
    estado: str
    rol_asignado: str | None
    created_at: datetime
    resuelta_at: datetime | None


class CuentaAccesoAdminOut(Orm):
    id: uuid.UUID
    login: str
    email: str | None
    email_verificado: bool
    activo: bool
    cambio_clave_obligatorio: bool
    intentos_fallidos: int
    bloqueado_hasta: datetime | None
    ultimo_acceso: datetime | None
    miembro_id: uuid.UUID | None
    gestor_id: uuid.UUID | None


class CuentaAccesoAdminActualizar(BaseModel):
    activo: bool | None = None
    email_verificado: bool | None = None


class SesionAccesoAdminOut(BaseModel):
    id: uuid.UUID
    cuenta_id: uuid.UUID
    login: str
    rol_activo: str
    expira_at: datetime
    ultima_actividad: datetime
    revocada_at: datetime | None


class MantenimientoAdministradorOut(BaseModel):
    cuenta_id: uuid.UUID | None
    login: str
    rol: str
    registros: dict[str, int]


class MantenimientoSeleccionIn(BaseModel):
    cuenta_ids: list[uuid.UUID] = []
    incluir_sin_trazabilidad: bool = False
    tipos: list[str] = Field(min_length=1)
    fecha_desde: date | None = None
    fecha_hasta: date | None = None


class MantenimientoVistaPreviaOut(BaseModel):
    administradores: list[MantenimientoAdministradorOut]
    totales: dict[str, int]


class MantenimientoEjecutarIn(MantenimientoSeleccionIn):
    confirmacion: str = Field(min_length=1, max_length=100)


class MantenimientoResultadoOut(BaseModel):
    eliminados: dict[str, int]
    archivos_eliminados: int
