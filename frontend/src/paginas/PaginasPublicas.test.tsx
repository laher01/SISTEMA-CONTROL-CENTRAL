import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";

import PaginaLegal from "./PaginasPublicas";
import Presentacion from "./Presentacion";
import { contenidoLandingInicial } from "../contenidoLanding";

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

  it("presenta el catálogo comercial tipado sin mostrar precios no aprobados", () => {
    const html = renderToStaticMarkup(<MemoryRouter><Presentacion /></MemoryRouter>);
    expect(html).toContain(contenidoLandingInicial.titulo);
    for (const beneficio of contenidoLandingInicial.beneficios) {
      expect(html).toContain(beneficio.titulo);
    }
    expect(html).toContain("Los planes y sus tarifas se publicarán");
    expect(html).toContain('/ingresar');
    expect(html).not.toContain("S/ 90");
  });

  it("la presentación pública enlaza a la política y términos", () => {
    const html = renderToStaticMarkup(<MemoryRouter><Presentacion /></MemoryRouter>);
    expect(html).toContain("/privacidad");
    expect(html).toContain("/terminos");
  });
});
