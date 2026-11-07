import type { AgrupacionDashboard, DashboardDesgloseFila } from "./tipos";

export const MESES_DASHBOARD = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

export function etiquetaFilaDashboard(fila: DashboardDesgloseFila, agrupacion: AgrupacionDashboard): string {
  if (agrupacion !== "mes") return fila.etiqueta;
  const coincidencia = /^(\d{4})-(0[1-9]|1[0-2])$/.exec(fila.clave);
  if (!coincidencia) return fila.etiqueta;
  return `${MESES_DASHBOARD[Number(coincidencia[2]) - 1]}/${coincidencia[1]}`;
}

export function anchoBarra(valor: number, maximo: number): string {
  if (!Number.isFinite(valor) || !Number.isFinite(maximo) || maximo <= 0) return "0%";
  return `${Math.min(100, Math.max(0, Math.abs(valor) / maximo * 100))}%`;
}
