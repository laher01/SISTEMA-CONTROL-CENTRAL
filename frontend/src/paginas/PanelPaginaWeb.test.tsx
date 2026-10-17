import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import PanelPaginaWeb from "./PanelPaginaWeb";

describe("Consola SaaS / Página web", () => {
  it("presenta las secciones editoriales sin fingir activación global", () => {
    const html = renderToStaticMarkup(<PanelPaginaWeb />);
    expect(html).toContain("Página web y Landing Page");
    expect(html).toContain("NEXUS comercial");
    expect(html).toContain("pendiente de conexión al servidor");
    expect(html).toMatch(/<input[^>]*disabled/);
    expect(html).toContain("/bienvenida");
  });
});
