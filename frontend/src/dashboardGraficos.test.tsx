import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { anchoBarra, etiquetaFilaDashboard, MESES_DASHBOARD } from "./dashboardGraficos";
import { GraficoMontos, GraficoVistaOrdenada } from "./componentes/GraficosDashboard";
import Dashboard from "./paginas/Dashboard";
import type { DashboardDesgloseFila, DashboardResumen, SesionActual } from "./tipos";

const mocks = vi.hoisted(() => ({ useDatos: vi.fn() }));
vi.mock("./api", () => ({ useDatos: mocks.useDatos }));
const filas: [DashboardDesgloseFila, DashboardDesgloseFila] = [
  { clave: "2026-09", etiqueta: "09/2026", ruc: null, expedientes: 55, total_pen: "91406", total_usd: "0" },
  { clave: "2026-08", etiqueta: "08/2026", ruc: null, expedientes: 62, total_pen: "101160", total_usd: "0" },
];
const montos: DashboardResumen["montos"] = [
  { moneda: "PEN", bancarizable: "0", no_bancarizable: "200", con_agente_retencion: "50", sin_agente_retencion: "150", cantidad_bancarizable: 0, cantidad_no_bancarizable: 2, cantidad_con_agente_retencion: 1, cantidad_sin_agente_retencion: 1 },
  { moneda: "USD", bancarizable: "10", no_bancarizable: "0", con_agente_retencion: "0", sin_agente_retencion: "10", cantidad_bancarizable: 1, cantidad_no_bancarizable: 0, cantidad_con_agente_retencion: 0, cantidad_sin_agente_retencion: 1 },
];

describe("Gráficos y meses del dashboard", () => {
  it.each(MESES_DASHBOARD.map((nombre, i) => [nombre, String(i + 1).padStart(2, "0")]))("muestra %s/año sin depender del huso horario", (nombre, mes) => {
    expect(etiquetaFilaDashboard({ ...filas[0], clave: `2026-${mes}` }, "mes")).toBe(`${nombre}/2026`);
  });
  it("conserva nombres de empresas y etiquetas desconocidas", () => {
    expect(etiquetaFilaDashboard(filas[0], "emisor")).toBe("09/2026");
    expect(etiquetaFilaDashboard({ ...filas[0], clave: "2026-13" }, "mes")).toBe("09/2026");
  });
  it("mantiene el orden de la tabla y representa todos los grupos", () => {
    const html = renderToStaticMarkup(<GraficoVistaOrdenada filas={filas} agrupacion="mes" />);
    expect(html.indexOf("Septiembre/2026")).toBeLessThan(html.indexOf("Agosto/2026"));
    expect(html).toContain(">55</strong>");
    expect(html).toContain(">62</strong>");
    expect(html).not.toContain("09/2026");
  });
  it("separa escalas por moneda sin sumar clasificaciones solapadas", () => {
    const html = renderToStaticMarkup(<GraficoMontos montos={montos} />);
    expect(html).toContain('aria-label="Montos en PEN"');
    expect(html).toContain('aria-label="Montos en USD"');
    expect(html).toContain("S/ 200.00");
    expect(html).toContain("US$ 10.00");
    expect(html.match(/width:100%/g)).toHaveLength(3);
  });
  it("presenta estados vacíos y no genera barras inválidas", () => {
    expect(renderToStaticMarkup(<GraficoVistaOrdenada filas={[]} agrupacion="mes" />)).toContain("Sin datos para los filtros seleccionados.");
    expect(anchoBarra(0, 0)).toBe("0%");
    expect(anchoBarra(Infinity, 5)).toBe("0%");
    expect(anchoBarra(-5, 10)).toBe("50%");
  });
  it.each(["SUPERADMIN", "ADMINISTRADOR", "GERENTE", "SECRETARIA", "RESPONSABLE", "USUARIO", "GESTOR"] as const)("%s recibe los gráficos comunes y etiquetas de mes", (rol) => {
    mocks.useDatos.mockImplementation((ruta: string) => ({
      cargando: false,
      datos: ruta.includes("/resumen") ? {
        expedientes_total: 117, por_estado: { VERDE: 116, AMARILLO: 1, NARANJA: 0, ROJO: 0 },
        pendientes_aprobacion: 0, documentos_pendientes: {}, alertas_abiertas: {}, montos,
      } : ruta.includes("/desglose") ? { agrupar_por: "mes", filas } : {},
    }));
    const html = renderToStaticMarkup(<MemoryRouter><Dashboard sesion={{ rol } as SesionActual} /></MemoryRouter>);
    expect(html).toContain('aria-label="Gráfico de vista ordenada"');
    expect(html).toContain('aria-label="Gráfico de montos"');
    expect(html).toContain("Mes de emisión");
    expect(html).toContain("Enero/");
  });
});
