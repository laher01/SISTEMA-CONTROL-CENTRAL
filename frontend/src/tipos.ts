export type Moneda = "PEN" | "USD";
export type EstadoExpediente = "VERDE" | "AMARILLO" | "NARANJA" | "ROJO";
export type EstadoDocumento = "PENDIENTE_CLASIFICACION" | "PENDIENTE_RELACION" | "RELACIONADO";
export const ESTADOS_DOCUMENTO: EstadoDocumento[] = [
  "PENDIENTE_CLASIFICACION",
  "PENDIENTE_RELACION",
  "RELACIONADO",
];
export type TipoAlerta =
  | "BANCARIZACION_SIN_VOUCHER"
  | "RETENCION_PENDIENTE"
  | "RECEPTOR_NO_AUTORIZADO"
  | "EXPEDIENTE_VENCIDO";
export type TipoComprobante = "FACT" | "RHE";
export type RolMiembro = "SUPERADMIN" | "ADMINISTRADOR" | "GERENTE" | "SECRETARIA" | "RESPONSABLE" | "USUARIO";

export const TIPOS_DOCUMENTO = [
  "FACT",
  "RHE",
  "GRR",
  "GRT",
  "VCHR",
  "RET",
  "EMAIL",
  "WSP",
  "COT",
  "OC",
  "REQ",
  "FOTO",
  "OTRO",
] as const;
export type TipoDocumento = (typeof TIPOS_DOCUMENTO)[number];

export const ESTADOS_EXPEDIENTE: EstadoExpediente[] = ["VERDE", "AMARILLO", "NARANJA", "ROJO"];
export const TIPOS_ALERTA: TipoAlerta[] = [
  "BANCARIZACION_SIN_VOUCHER",
  "RETENCION_PENDIENTE",
  "RECEPTOR_NO_AUTORIZADO",
  "EXPEDIENTE_VENCIDO",
];

export type TipoRelacionEmpresa = "PROVEEDOR" | "CLIENTE" | "AMBOS" | "SIN_CLASIFICAR";
export type ClasificacionProveedor = "A" | "B";

export interface EmpresaUsuario {
  id: string;
  codigo: string;
  nombre: string;
}

export interface Empresa {
  id: string;
  ruc: string;
  razon_social: string;
  tipo_relacion: TipoRelacionEmpresa;
  clasificacion_proveedor: ClasificacionProveedor | null;
  usuarios?: EmpresaUsuario[];
  autorizada: boolean;
  agente_retencion: boolean;
}

export interface Miembro {
  id: string;
  responsable_id: string | null;
  codigo: string;
  nombre: string;
  rol: RolMiembro;
  porcentaje_produccion: string | null;
  activo: boolean;
}

export interface Gestor {
  porcentaje_comision: string | null;
  id: string;
  codigo: string;
  nombre: string;
  usuario_id: string | null;
}

export interface Documento {
  id: string;
  expediente_id: string | null;
  emisor?: Empresa | null;
  receptor?: Empresa | null;
  tipo_documento: TipoDocumento | null;
  estado: EstadoDocumento;
  sha256: string;
  nombre_original: string;
  mime_type: string;
  tamano_bytes: number;
  datos_extraidos: Record<string, unknown> | null;
  formato_origen: string | null;
  fecha_emision: string | null;
  serie: string | null;
  correlativo: string | null;
  moneda: Moneda | null;
  importe_total: string | null;
  gestor_id: string | null;
  usuario_id: string | null;
  created_at: string;
}

export interface Alerta {
  id: string;
  expediente_id: string;
  tipo: TipoAlerta;
  mensaje: string;
  resuelta: boolean;
  created_at: string;
  resuelta_at: string | null;
}

export interface Expediente {
  id: string;
  receptor: Empresa;
  emisor: Empresa;
  tipo_comprobante: TipoComprobante;
  serie: string;
  correlativo: string;
  fecha_emision: string;
  moneda: Moneda;
  importe_total: string;
  requiere_guia: boolean;
  gestor_id: string | null;
  usuario_id: string | null;
  estado: EstadoExpediente;
  pendiente_aprobacion: boolean;
  created_at: string;
}

export interface ExpedienteDetalle extends Expediente {
  documentos: Documento[];
  alertas: Alerta[];
  faltantes: TipoDocumento[];
  fecha_limite: string;
}

export interface RelacionSugerida {
  expediente: Expediente;
  puntaje: number;
  evidencias: string[];
}

export interface DashboardResumen {
  expedientes_total: number;
  por_estado: Record<EstadoExpediente, number>;
  pendientes_aprobacion: number;
  montos: { moneda: Moneda; bancarizable: string; no_bancarizable: string }[];
  alertas_abiertas: Record<TipoAlerta, number>;
  documentos_pendientes: Partial<Record<EstadoDocumento, number>>;
}


export type AgrupacionDashboard = "usuario" | "emisor" | "receptor" | "dia" | "mes" | "anio";

export interface DashboardDesgloseFila {
  clave: string;
  etiqueta: string;
  ruc: string | null;
  expedientes: number;
  total_pen: string;
  total_usd: string;
}

export interface DashboardDesglose {
  agrupar_por: AgrupacionDashboard;
  filas: DashboardDesgloseFila[];
}


export interface ProduccionFila {
  usuario_id: string | null;
  usuario_codigo: string;
  usuario_nombre: string;
  gestor_id: string | null;
  gestor_codigo: string;
  gestor_nombre: string;
  moneda: Moneda;
  expedientes: number;
  importe_total: string;
}

export interface ProduccionResumen {
  filas: ProduccionFila[];
}


export interface ComprasProveedorFila {
  usuario_codigo: string;
  gestor_codigo: string;
  emisor_ruc: string;
  emisor_razon_social: string;
  receptor_ruc: string;
  receptor_razon_social: string;
  moneda: Moneda;
  expedientes: number;
  importe_total: string;
}


export interface SesionActual {
  rol: RolMiembro | "GESTOR";
  codigo: string;
  nombre: string;
  miembro_id: string | null;
  gestor_id: string | null;
  usuario_id: string | null;
  cambio_clave_obligatorio: boolean;
  jerarquia: Array<{ rol: string; codigo: string; nombre: string }>;
}

export interface CredencialTemporal {
  login: string;
  clave_temporal: string;
}

export interface AltaMiembro {
  miembro: Miembro;
  credencial: CredencialTemporal;
}

export interface AltaGestor {
  gestor: Gestor;
  credencial: CredencialTemporal;
}


export interface RegistroFila {
  tipo_empresa: ClasificacionProveedor | null;
  expediente_id: string;
  estado: EstadoExpediente;
  usuario_id: string | null;
  usuario_codigo: string | null;
  usuario_nombre: string | null;
  gestor_id: string | null;
  gestor_codigo: string | null;
  gestor_nombre: string | null;
  fecha_emision: string;
  tipo_comprobante: TipoComprobante;
  serie: string;
  correlativo: string;
  emisor_ruc: string;
  emisor_razon_social: string;
  receptor_ruc: string;
  receptor_razon_social: string;
  moneda: Moneda;
  importe_total: string;
  documentos_requeridos: TipoDocumento[];
  documentos_presentes: TipoDocumento[];
  documentos_faltantes: TipoDocumento[];
  documentos_opcionales: TipoDocumento[];
  puede_eliminar: boolean;
}

export interface RegistroResumen {
  filas: RegistroFila[];
  total_registros: number;
  total_pen: string;
  total_usd: string;
}

export interface AlertaManual {
  id: string;
  expediente_id: string | null;
  creado_por_codigo: string;
  creado_por_rol: string;
  destinatario_usuario_id: string | null;
  destinatario_gestor_id: string | null;
  para_administracion: boolean;
  asunto: string;
  mensaje: string;
  resuelta: boolean;
  created_at: string;
  resuelta_at: string | null;
}

export interface PermisoConfigurado {
  id: string;
  rol: string;
  permiso: string;
  habilitado: boolean;
}

export interface PlanLiquidacion {
  id: string;
  usuario_id: string;
  nombre: string;
  porcentaje: string;
  vigencia_desde: string;
  vigencia_hasta: string | null;
  activo: boolean;
}

export interface CuentaPagoERP {
  id: string;
  usuario_id: string;
  titular: string;
  banco: string;
  tipo_cuenta: string;
  moneda: Moneda;
  numero_cuenta: string | null;
  cci: string | null;
  porcentaje_distribucion: string;
  activa: boolean;
}

export interface AdelantoERP {
  id: string;
  usuario_id: string;
  fecha: string;
  moneda: Moneda;
  monto: string;
  descripcion: string | null;
  aplicado: boolean;
}

export interface CarteraClienteFila {
  cliente_id: string;
  ruc: string;
  razon_social: string;
  agente_retencion: boolean;
  moneda: Moneda;
  compras_mes: string;
  saldo_anterior: string;
  abonos_mes: string;
  saldo_total: string;
}

export interface CarteraClientesResumen {
  mes: string;
  moneda: Moneda;
  filas: CarteraClienteFila[];
  total_compras_mes: string;
  total_saldo_anterior: string;
  total_abonos_mes: string;
  total_saldo: string;
}

export interface AbonoClienteERP {
  id: string;
  cliente_id: string;
  fecha: string;
  moneda: Moneda;
  monto: string;
  descripcion: string | null;
  referencia: string | null;
  created_at: string;
}


export interface AsignacionPedidoGerencia {
  id: string;
  usuario_id: string;
  usuario_codigo: string;
  usuario_nombre: string;
  gestor_id: string | null;
  gestor_codigo: string | null;
  gestor_nombre: string | null;
  proveedor_id: string | null;
  proveedor_ruc: string | null;
  proveedor_razon_social: string | null;
  monto_asignado: string;
  ejecutado: string;
  saldo: string;
}

export interface PedidoGerencia {
  id: string;
  responsable_id: string | null;
  cliente_id: string;
  cliente_ruc: string;
  cliente_razon_social: string;
  periodo_mes: string;
  moneda: Moneda;
  monto_solicitado: string;
  monto_asignado: string;
  monto_ejecutado: string;
  saldo_pendiente: string;
  exceso: string;
  avance_porcentaje: string;
  modalidad: "SIN_RESTRICCION" | "POR_PEDIDO";
  modo_distribucion: "MANUAL" | "SEMIASISTIDA" | "AUTOMATICA";
  estado: "ACTIVO" | "CERRADO" | "CANCELADO";
  observacion: string | null;
  concentracion_maxima_proveedor: string;
  proveedor_mayor_concentracion: string | null;
  asignaciones: AsignacionPedidoGerencia[];
}


export interface PagoERP {
  id: string;
  usuario_id: string;
  plan_id: string | null;
  periodo_desde: string;
  periodo_hasta: string;
  moneda: Moneda;
  produccion_total: string;
  porcentaje: string;
  bruto: string;
  adelantos: string;
  ajustes: string;
  saldo: string;
  estado: string;
  fecha_programada: string | null;
  fecha_pago: string | null;
  voucher_documento_id: string | null;
  conciliado: boolean;
  created_at: string;
}


export interface FiltroOpcion {
  id: string;
  codigo: string;
  nombre: string;
  usuario_id: string | null;
  porcentaje_produccion: string | null;
}

export interface RegistroOpciones {
  usuarios: FiltroOpcion[];
  gestores: FiltroOpcion[];
}


export interface NexusFuente {
  titulo: string;
  url: string | null;
  tipo: string;
}

export interface NexusRespuesta {
  respuesta: string;
  accion: string;
  fuentes: NexusFuente[];
  datos: Record<string, unknown>;
  internet_usado: boolean;
  requiere_configuracion_externa: boolean;
}

export interface NexusEstado {
  asistente_activo: boolean;
  consulta_ruc_externa: boolean;
  busqueda_internet: boolean;
  fuente_oficial_preferida: string;
}


export interface ConfiguracionAcceso {
  id: string;
  registro_publico: boolean;
  requiere_aprobacion: boolean;
  solo_correos_autorizados: boolean;
  requiere_email_verificado: boolean;
  proveedor_email_configurado: boolean;
  acceso_cloudflare_activo: boolean;
  duracion_sesion_horas: number;
  intentos_fallidos_max: number;
  bloqueo_minutos: number;
  clave_min_longitud: number;
  clave_requiere_letra: boolean;
  clave_requiere_numero: boolean;
}

export interface CorreoAutorizado {
  id: string;
  email: string;
  rol_sugerido: RolMiembro | null;
  activo: boolean;
  created_at: string;
}

export interface SolicitudAcceso {
  id: string;
  email: string;
  nombre: string;
  codigo_solicitado: string;
  estado: string;
  rol_asignado: string | null;
  created_at: string;
  resuelta_at: string | null;
}


export interface CuentaAccesoAdmin {
  id: string;
  login: string;
  email: string | null;
  email_verificado: boolean;
  activo: boolean;
  cambio_clave_obligatorio: boolean;
  intentos_fallidos: number;
  bloqueado_hasta: string | null;
  ultimo_acceso: string | null;
  miembro_id: string | null;
  gestor_id: string | null;
}

export interface SesionAccesoAdmin {
  id: string;
  cuenta_id: string;
  login: string;
  rol_activo: string;
  expira_at: string;
  ultima_actividad: string;
  revocada_at: string | null;
}


export interface MantenimientoAdministrador {
  cuenta_id: string | null;
  login: string;
  rol: string;
  registros: Record<string, number>;
}

export interface MantenimientoVistaPrevia {
  administradores: MantenimientoAdministrador[];
  totales: Record<string, number>;
}

export interface MantenimientoResultado {
  eliminados: Record<string, number>;
  archivos_eliminados: number;
}
