import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import Configuracion from "./Configuracion";
import type { SesionActual } from "../tipos";

vi.mock("../api", () => ({
  useDatos: () => ({ datos: [], error: null, cargando: false, recargar: () => {} }),
  enviarJson: vi.fn(),
  eliminar: vi.fn(),
}));

function htmlPara(rol: SesionActual["rol"]): string {
  const sesion = { rol, codigo: "PRUEBA", nombre: "Cuenta de prueba" } as SesionActual;
  return renderToStaticMarkup(createElement(Configuracion, { sesion }));
}

describe("configuración separada por rol", () => {
  it("muestra a SUPERADMIN solo el menú de administraciones SaaS", () => {
    const html = htmlPara("SUPERADMIN");
    expect(html).toContain("Consola SaaS");
    expect(html).toContain("Administraciones SaaS");
    expect(html).not.toContain(">Configuración de acceso</button>");
    expect(html).not.toContain(">Empresas registradas</button>");
    expect(html).not.toContain(">Mantenimiento</button>");
    expect(html).not.toContain(">Permisos operativos</button>");
  });

  it("conserva las herramientas del ADMINISTRADOR de cada tenant", () => {
    const html = htmlPara("ADMINISTRADOR");
    expect(html).toContain(">Permisos operativos</button>");
    expect(html).toContain(">Configuración de acceso</button>");
    expect(html).toContain(">Empresas registradas</button>");
    expect(html).toContain(">Mantenimiento</button>");
    expect(html).not.toContain(">Administraciones SaaS</button>");
  });
});
