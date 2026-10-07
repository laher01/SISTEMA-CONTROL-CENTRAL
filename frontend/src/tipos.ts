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
export type RolMiembro = "ADMINISTRADOR" | "GERENTE" | "SECRETARIA" | "USUARIO";

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

export interface Empresa {
  id: string;
  ruc: string;
  razon_social: string;
  autorizada: boolean;
  agente_retencion: boolean;
}

export interface Miembro {
  id: string;
  codigo: string;
  nombre: string;
  rol: RolMiembro;
  activo: boolean;
}

export interface Gestor {
  id: string;
  codigo: string;
  nombre: string;
  usuario_id: string | null;
}

export interface Documento {
  id: string;
  expediente_id: string | null;
  tipo_documento: TipoDocumento | null;
  estado: EstadoDocumento;
  sha256: string;
  nombre_original: string;
  mime_type: string;
  tamano_bytes: number;
  datos_extraidos: Record<string, unknown> | null;
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
