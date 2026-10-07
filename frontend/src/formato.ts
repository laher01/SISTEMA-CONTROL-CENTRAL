import type {
  EstadoDocumento,
  EstadoExpediente,
  Moneda,
  TipoAlerta,
  TipoComprobante,
  TipoDocumento,
} from "./tipos";

const SIMBOLO: Record<Moneda, string> = { PEN: "S/", USD: "US$" };

export function formatearMonto(moneda: Moneda, importe: string | number): string {
  const numero = typeof importe === "number" ? importe : Number(importe);
  const texto = numero.toLocaleString("es-PE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${SIMBOLO[moneda]} ${texto}`;
}

export function formatearFecha(iso: string): string {
  const [anio, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${anio}`;
}

export function formatearTamano(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function numeroComprobante(serie: string, correlativo: string): string {
  return `${serie}-${correlativo}`;
}

export function numeroExpediente(
  tipo: TipoComprobante,
  serie: string,
  correlativo: string,
): string {
  const numero = numeroComprobante(serie, correlativo);
  return tipo === "RHE" ? `RHE-${numero}` : numero;
}

export const ETIQUETA_ESTADO: Record<EstadoExpediente, string> = {
  VERDE: "Completo",
  AMARILLO: "Falta retención",
  NARANJA: "Incompleto",
  ROJO: "Vencido",
};

export const ETIQUETA_ALERTA: Record<TipoAlerta, string> = {
  BANCARIZACION_SIN_VOUCHER: "Bancarización sin voucher",
  RETENCION_PENDIENTE: "Retención pendiente",
  RECEPTOR_NO_AUTORIZADO: "Receptor no autorizado",
  EXPEDIENTE_VENCIDO: "Expediente vencido",
};

export const ETIQUETA_ESTADO_DOCUMENTO: Record<EstadoDocumento, string> = {
  PENDIENTE_CLASIFICACION: "Sin clasificar",
  PENDIENTE_RELACION: "Sin expediente",
  RELACIONADO: "Relacionado",
};

export const ETIQUETA_TIPO_DOCUMENTO: Record<TipoDocumento, string> = {
  FACT: "Factura",
  RHE: "Recibo por honorarios",
  GRR: "Guía remitente",
  GRT: "Guía transportista",
  VCHR: "Voucher",
  RET: "Constancia de retención",
  EMAIL: "Correo",
  WSP: "WhatsApp",
  COT: "Cotización",
  OC: "Orden de compra",
  REQ: "Requerimiento",
  FOTO: "Foto",
  OTRO: "Otro",
};
