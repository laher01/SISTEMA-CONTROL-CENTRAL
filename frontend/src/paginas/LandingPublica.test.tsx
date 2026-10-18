import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import LandingPublica from "./LandingPublica";

const mockUseDatos = vi.hoisted(() => vi.fn());

vi.mock("../api", () => ({
  useDatos: mockUseDatos,
}));

function mostrar(): string {
  return renderToStaticMarkup(
    <MemoryRouter><LandingPublica /></MemoryRouter>,
  );
}

describe("visibilidad pública de landing", () => {
  beforeEach(() => {
    mockUseDatos.mockReset();
  });

  it("oculta contenido comercial sin bloquear login ni legales", () => {
    mockUseDatos.mockReturnValue({
      datos: { activa: false, version: 2 },
      error: undefined,
      cargando: false,
    });
    const html = mostrar();
    expect(html).toContain("La presentación comercial no está disponible");
    expect(html).toContain("/ingresar");
    expect(html).toContain("/privacidad");
    expect(html).toContain("/terminos");
    expect(html).not.toContain("Planes del servicio");
  });

  it("muestra landing actual cuando está habilitada", () => {
    mockUseDatos.mockReturnValue({
      datos: { activa: true, version: 3 },
      error: undefined,
      cargando: false,
    });
    const html = mostrar();
    expect(html).toContain("Planes del servicio");
    expect(html).toContain("/ingresar");
  });

  it("no publica sin confirmación explícita aunque no exista error de red", () => {
    mockUseDatos.mockReturnValue({
      datos: undefined,
      error: undefined,
      cargando: false,
    });
    const html = mostrar();
    expect(html).toContain("La presentación comercial no está disponible");
    expect(html).toContain("/ingresar");
    expect(html).toContain("/privacidad");
    expect(html).toContain("/terminos");
    expect(html).not.toContain("Planes del servicio");
  });

  it("oculta conservadoramente la landing cuando falla la consulta pública", () => {
    mockUseDatos.mockReturnValue({
      datos: undefined,
      error: "No disponible",
      cargando: false,
    });
    expect(mostrar()).toContain("La presentación comercial no está disponible");
    expect(mostrar()).toContain("/ingresar");
  });
});
