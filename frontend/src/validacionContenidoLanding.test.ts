import { describe, expect, it } from "vitest";
import { contenidoLandingInicial } from "./contenidoLanding";
import { validarContenidoLanding } from "./validacionContenidoLanding";

describe("validación editorial de landing", () => {
  it("acepta los contenidos públicos aprobados actuales", () => {
    expect(validarContenidoLanding(contenidoLandingInicial)).toEqual([]);
  });

  it("rechaza valores no estructurados o campos obligatorios vacíos", () => {
    expect(validarContenidoLanding(null)[0].campo).toBe("contenido");
    const errores = validarContenidoLanding({ ...contenidoLandingInicial, titulo: " " });
    expect(errores.some((error) => error.campo === "titulo")).toBe(true);
  });

  it("bloquea etiquetas HTML y caracteres de control", () => {
    const errores = validarContenidoLanding({
      ...contenidoLandingInicial,
      descripcion: "<script>contenido</script>",
    });
    expect(errores.some((error) => error.campo === "descripcion")).toBe(true);
  });

  it("detecta identificadores duplicados entre beneficios", () => {
    const [primero] = contenidoLandingInicial.beneficios;
    const errores = validarContenidoLanding({
      ...contenidoLandingInicial,
      beneficios: [primero, { ...primero }],
    });
    expect(errores.some((error) => error.mensaje === "Identificador repetido")).toBe(true);
  });

  it("limita cantidad de beneficios y longitud de títulos", () => {
    const errores = validarContenidoLanding({
      ...contenidoLandingInicial,
      titulo: "x".repeat(181),
      beneficios: [],
    });
    expect(errores.map((error) => error.campo).sort()).toEqual(["beneficios", "titulo"]);
  });
});
