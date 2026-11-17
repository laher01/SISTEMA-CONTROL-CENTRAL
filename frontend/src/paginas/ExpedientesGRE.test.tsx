import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import Expedientes from "./Expedientes";
import type { SesionActual } from "../tipos";

vi.mock("../api", async (importOriginal) => ({
  ...await importOriginal<typeof import("../api")>(),
  useDatos: (ruta: string) => ({
    datos: ruta.includes("/provisionales-gre") ? [
      { documento_id: "gre-a", factura: "E001-175", emisor_ruc: "20123456789", receptor_ruc: "20987654321", monto_contabilizable: "0.00", gestor_codigo: "GESTOR-A", gestor_nombre: "Javier", usuario_codigo: "USUARIO-A", usuario_nombre: "Jonathan", responsable_codigo: "RESP-A", responsable_nombre: "Luis" },
      { documento_id: "gre-b", factura: "E001-176", emisor_ruc: "20123456789", receptor_ruc: "20987654321", monto_contabilizable: "0.00", gestor_codigo: "GESTOR-B", usuario_codigo: "USUARIO-B" },
    ] : ruta.includes("/resumen") ? undefined : [],
    error: null, cargando: false, recargar: () => {},
  }),
}));

function tablaGRE(rol: SesionActual["rol"]) {
  const html = renderToStaticMarkup(<MemoryRouter><Expedientes sesion={{ rol } as SesionActual} /></MemoryRouter>);
  const inicio = html.indexOf('aria-label="GRE en espera de factura"');
  return html.slice(inicio, html.indexOf("</section>", inicio));
}

describe("Origen individual de GRE en Expedientes", () => {
  it.each(["ADMINISTRADOR", "GERENTE", "SECRETARIA", "RESPONSABLE"] as const)("muestra la jerarquía por fila para %s", (rol) => {
    const tabla = tablaGRE(rol);
    for (const columna of ["Gestor", "Usuario", "Responsable"]) expect(tabla).toContain(`<th>${columna}</th>`);
    expect(tabla).toMatch(/E001-175[\s\S]*GESTOR-A · Javier[\s\S]*USUARIO-A · Jonathan[\s\S]*RESP-A · Luis/);
    expect(tabla).toMatch(/E001-176[\s\S]*GESTOR-B[\s\S]*USUARIO-B[\s\S]*Sin asignar/);
  });

  it.each(["GESTOR", "USUARIO", "SUPERADMIN"] as const)("no añade columnas de origen a %s", (rol) => {
    const tabla = tablaGRE(rol);
    expect(tabla).not.toContain("<th>Gestor</th>");
    expect(tabla).not.toContain("GESTOR-A");
    expect(tabla).toContain("E001-175");
  });
});
