import { describe, expect, it } from "vitest";

import { obtenerPaginasVisibles, paginaCorregida } from "./componentes";

describe("obtenerPaginasVisibles", () => {
  it("muestra todas las páginas cuando el resultado tiene siete páginas", () => {
    expect(obtenerPaginasVisibles(0, 7)).toEqual([1, 2, 3, 4, 5, 6, 7]);
  });

  it("mantiene accesibles la primera, la última y las páginas cercanas al punto actual", () => {
    expect(obtenerPaginasVisibles(9, 20)).toEqual([1, "…", 8, 9, 10, 11, 12, "…", 20]);
  });

  it("no crea páginas si el filtro no tiene resultados", () => {
    expect(obtenerPaginasVisibles(0, 0)).toEqual([]);
  });
});


describe("paginaCorregida", () => {
  it("estabiliza una lista vacía en la primera página", () => {
    const primera = paginaCorregida(4, -1);
    expect(primera).toBe(0);
    expect(paginaCorregida(primera, -1)).toBe(primera);
  });

  it("corrige una página fuera del rango y conserva las páginas válidas", () => {
    expect(paginaCorregida(8, 2)).toBe(2);
    expect(paginaCorregida(1, 2)).toBe(1);
    expect(paginaCorregida(8)).toBe(8);
  });
});
