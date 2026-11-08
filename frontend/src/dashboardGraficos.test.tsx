import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { alturaBarra, etiquetaFilaDashboard, MESES_DASHBOARD, sectoresCirculares } from "./dashboardGraficos";
import { GraficoMontos, GraficoVistaOrdenada, VistasGraficosDashboard } from "./componentes/GraficosDashboard";
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
    expect(html).toContain("height:100%");
    expect(html).not.toContain("width:");
  });
  it("separa escalas por moneda sin sumar clasificaciones solapadas", () => {
    const html = renderToStaticMarkup(<GraficoMontos montos={montos} />);
    expect(html).toContain('aria-label="Montos en PEN"');
    expect(html).toContain('aria-label="Montos en USD"');
    expect(html).toContain("S/ 200.00");
    expect(html).toContain("US$ 10.00");
    expect(html.match(/height:100%/g)).toHaveLength(3);
  });
  it("presenta estados vacíos y no genera barras inválidas", () => {
    expect(renderToStaticMarkup(<GraficoVistaOrdenada filas={[]} agrupacion="mes" />)).toContain("Sin datos para los filtros seleccionados.");
    expect(alturaBarra(0, 0)).toBe("0%");
    expect(alturaBarra(Infinity, 5)).toBe("0%");
    expect(alturaBarra(-5, 10)).toBe("50%");
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
    expect(html.indexOf("dashboard-graficos")).toBeGreaterThan(html.indexOf("Alertas abiertas"));
    expect(html.indexOf("dashboard-graficos")).toBeGreaterThan(html.lastIndexOf("</table>"));
    expect(html).toContain("Enero/");
  });
});


describe("Tres vistas de los mismos datos", () => {
  it("ofrece exactamente tres pestañas y enlaza el panel activo", () => {
    const html = renderToStaticMarkup(<VistasGraficosDashboard vista="circular" alCambiar={() => {}}><p>Datos filtrados</p></VistasGraficosDashboard>);
    expect(html.match(/role="tab"/g)).toHaveLength(3);
    expect(html.match(/aria-selected="true"/g)).toHaveLength(1);
    expect(html).toContain("Circular 3D");
    expect(html).toContain("Barras verticales");
    expect(html).toContain("Líneas");
    expect(html).toContain('role="tabpanel"');
    expect(html).toContain("Datos filtrados");
  });
  it("calcula proporciones sin perder los valores cero", () => {
    const resultado = sectoresCirculares([0, 25, 75]);
    expect(resultado.total).toBe(100);
    expect(resultado.sectores.map((x) => x.porcentaje)).toEqual([0, 25, 75]);
    expect(resultado.sectores[2]?.fin).toBe(100);
  });
  it.each([[0, 0], [-10, 20], [Infinity, 1]])("no inventa proporciones ante ceros, negativos o valores inválidos (%j)", (...valores) => {
    const resultado = sectoresCirculares(valores);
    expect(resultado.total).toBe(0);
    expect(resultado.fondo).not.toMatch(/NaN|Infinity/);
  });
  it.each(["circular", "lineas"] as const)("%s conserva etiquetas, orden y valores del conjunto original", (vista) => {
    const html = renderToStaticMarkup(<GraficoVistaOrdenada filas={filas} agrupacion="mes" vista={vista} />);
    expect(html).toContain("Septiembre/2026");
    expect(html).toContain("Agosto/2026");
    expect(html).toContain(">55</strong>");
    expect(html).toContain(">62</strong>");
    const leyenda = html.slice(html.indexOf('<ul class="dashboard-leyenda">'));
    expect(leyenda.indexOf("Septiembre/2026")).toBeLessThan(leyenda.indexOf("Agosto/2026"));
    expect(html).not.toMatch(/NaN|Infinity/);
  });
  it("divide los círculos monetarios por clasificación y moneda", () => {
    const html = renderToStaticMarkup(<GraficoMontos montos={montos} vista="circular" />);
    for (const moneda of ["PEN", "USD"]) {
      expect(html).toContain(`aria-label="Bancarización en ${moneda}"`);
      expect(html).toContain(`aria-label="Retención en ${moneda}"`);
    }
    expect(html).toContain("25%");
    expect(html).toContain("75%");
    expect(html).toContain("S/ 200.00");
    expect(html).toContain("US$ 10.00");
  });
  it("conserva negativos en líneas y explica la limitación circular", () => {
    const negativo = [{ ...filas[0], expedientes: -10 }];
    const circular = renderToStaticMarkup(<GraficoVistaOrdenada filas={negativo} agrupacion="mes" vista="circular" />);
    expect(circular).toContain("valores con signo");
    expect(circular).toContain(">-10</strong>");
    const lineas = renderToStaticMarkup(<GraficoVistaOrdenada filas={negativo} agrupacion="mes" vista="lineas" />);
    expect(lineas).toContain("polyline");
    expect(lineas).toContain(">-10</strong>");
    expect(lineas).not.toMatch(/NaN|Infinity/);
  });
});
