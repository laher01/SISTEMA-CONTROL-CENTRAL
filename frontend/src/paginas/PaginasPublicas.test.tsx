import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";

import PaginaLegal from "./PaginasPublicas";
import Presentacion from "./Presentacion";

describe("páginas públicas para Google OAuth", () => {
  it("publica política de privacidad sin iniciar sesión", () => {
    const html = renderToStaticMarkup(<MemoryRouter><PaginaLegal tipo="privacidad" /></MemoryRouter>);
    expect(html).toContain("Política de privacidad");
    expect(html).toContain("gmail.readonly");
    expect(html).toContain("NEXOMAR NEGOCIOS E.I.R.L.");
  });

  it("publica condiciones y enlaces internos", () => {
    const html = renderToStaticMarkup(<MemoryRouter><PaginaLegal tipo="terminos" /></MemoryRouter>);
    expect(html).toContain("Términos y condiciones");
    expect(html).toContain("/privacidad");
    expect(html).toContain("/ingresar");
  });

  it("la presentación pública enlaza a la política y términos", () => {
    const html = renderToStaticMarkup(<MemoryRouter><Presentacion /></MemoryRouter>);
    expect(html).toContain("/privacidad");
    expect(html).toContain("/terminos");
  });
});
