import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import PanelPaginaWeb from "./PanelPaginaWeb";

describe("Consola SaaS / Página web", () => {
  it("presenta las secciones editoriales y espera lectura autorizada del estado", () => {
    const html = renderToStaticMarkup(<PanelPaginaWeb />);
    expect(html).toContain("Página web y Landing Page");
    expect(html).toContain("NEXUS comercial");
    expect(html).toContain("Consultando");
    expect(html).toMatch(/<input[^>]*disabled/);
    expect(html).toContain("/bienvenida");
  });
});
