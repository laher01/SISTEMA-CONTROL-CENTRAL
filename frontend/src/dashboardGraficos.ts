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

export function alturaBarra(valor: number, maximo: number): string {
  if (!Number.isFinite(valor) || !Number.isFinite(maximo) || maximo <= 0) return "0%";
  return `${Math.min(100, Math.max(0, Math.abs(valor) / maximo * 100))}%`;
}

export type VistaGrafico = "barras" | "circular" | "lineas";

export function sectoresCirculares(valores: number[]) {
  const suma = valores.reduce((acumulado, valor) => acumulado + valor, 0);
  const valido = Number.isFinite(suma) && valores.every((valor) => Number.isFinite(valor) && valor >= 0);
  const total = valido ? suma : 0;
  let acumulado = 0;
  const sectores = valores.map((valor, indice) => {
    const porcentaje = total > 0 ? valor / total * 100 : 0;
    const inicio = acumulado;
    acumulado += porcentaje;
    return { porcentaje, inicio, fin: acumulado, color: `hsl(${(210 + indice * 137.5) % 360} 62% 44%)` };
  });
  return {
    valido,
    total,
    sectores,
    fondo: total > 0 ? `conic-gradient(${sectores.map((sector) => `${sector.color} ${sector.inicio}% ${sector.fin}%`).join(", ")})` : "#dce5ef",
  };
}
