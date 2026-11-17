import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import Pendientes from "./Pendientes";
import type { SesionActual } from "../tipos";

vi.mock("../api", async (importOriginal) => ({
  ...await importOriginal<typeof import("../api")>(),
  useDatos: (ruta: string) => ({
    datos: ruta.includes("/provisionales-gre") ? [{
      documento_id: "a", factura: "E001-175", emisor_ruc: "20123456789",
      receptor_ruc: "20987654321", cliente_autorizado: true,
      gestor_codigo: "GESTOR-A", usuario_codigo: "USUARIO-A", responsable_codigo: "RESP-A",
    }] : ruta.startsWith("/api/v1/documentos?") ? [{
      id: "b", nombre_original: "archivo.pdf", created_at: "2026-11-16T00:00:00Z",
      tipo_documento: "GRR", gestor_codigo: "GESTOR-B", usuario_codigo: "USUARIO-B",
      responsable_codigo: "RESP-B",
    }] : [],
    error: null, cargando: false, recargar: () => {},
  }),
}));

describe("Ruta en las dos tablas de Pendientes", () => {
  it.each(["ADMINISTRADOR", "GERENTE", "SECRETARIA", "RESPONSABLE", "USUARIO", "GESTOR"] as const)("muestra una columna Ruta por tabla para %s", (rol: SesionActual["rol"]) => {
    const html = renderToStaticMarkup(<MemoryRouter><Pendientes rol={rol} /></MemoryRouter>);
    expect(html.match(/<th>Ruta<\/th>/g)).toHaveLength(2);
    for (const sufijo of ["A", "B"]) {
      expect(html).toContain(`<div class="bloque"><strong>Gestor</strong> GESTOR-${sufijo}</div><div class="bloque"><strong>Usuario</strong> USUARIO-${sufijo}</div><div class="bloque"><strong>Responsable</strong> RESP-${sufijo}</div>`);
    }
  });
});
