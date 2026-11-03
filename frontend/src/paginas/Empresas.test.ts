import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import Empresas from "./Empresas";
import type { Empresa, SesionActual } from "../tipos";

const empresas: Empresa[] = [
  {
    id: "proveedor-1",
    ruc: "20123456789",
    razon_social: "Proveedor de prueba S.A.C.",
    tipo_relacion: "PROVEEDOR",
    clasificacion_proveedor: "A",
    autorizada: true,
    agente_retencion: false,
  },
];

vi.mock("../api", () => ({
  useDatos: () => ({ datos: empresas, error: null, cargando: false, recargar: () => {} }),
  enviarJson: vi.fn(),
}));

function htmlEmpresas(rol: SesionActual["rol"] = "ADMINISTRADOR"): string {
  const sesion = { rol, codigo: "PRUEBA", nombre: "Cuenta de prueba" } as SesionActual;
  return renderToStaticMarkup(createElement(
    MemoryRouter,
    null,
    createElement(Empresas, { sesion }),
  ));
}

describe("edición directa de empresas", () => {
  it("muestra la razón social como punto de edición y retira la columna Editar", () => {
    const html = htmlEmpresas();

    expect(html).toContain('aria-label="Editar razón social 20123456789"');
    expect(html).toContain("Proveedor de prueba S.A.C.");
    expect(html).not.toContain("<th>Editar</th>");
    expect(html).not.toContain(">Editar</button>");
  });

  it("presenta Tipo A y Tipo B como opciones exclusivas de selección", () => {
    const html = htmlEmpresas();

    expect(html).toContain('type="radio"');
    expect(html).toContain(">Tipo A</span>");
    expect(html).toContain(">Tipo B</span>");
    expect(html).toContain('checked="" value="A"');
    expect(html).not.toContain('<select aria-label="Tipo proveedor"');
  });

  it("mantiene la razón social de solo lectura para roles sin permiso administrativo", () => {
    const html = htmlEmpresas("USUARIO");

    expect(html).not.toContain('aria-label="Editar razón social 20123456789"');
    expect(html).toContain("Proveedor de prueba S.A.C.");
    expect(html).toContain("<fieldset class=\"empresas-tipo-proveedor\" disabled=\"\">");
  });
});
