import { describe, expect, it } from "vitest";

import { mensajeDeDetalle } from "./api";
import { formatearFecha, formatearMonto, formatearTamano } from "./formato";

describe("formato", () => {
  it("formatea montos con símbolo y dos decimales", () => {
    expect(formatearMonto("PEN", "2500")).toMatch(/^S\/ 2.500,00$|^S\/ 2,500\.00$/);
    expect(formatearMonto("USD", 0.5)).toMatch(/^US\$ 0[.,]50$/);
  });

  it("formatea fechas ISO como dd/mm/aaaa", () => {
    expect(formatearFecha("2026-09-10")).toBe("10/09/2026");
    expect(formatearFecha("2026-10-01T06:25:33Z")).toBe("01/10/2026");
  });

  it("formatea tamaños", () => {
    expect(formatearTamano(512)).toBe("512 B");
    expect(formatearTamano(2048)).toBe("2.0 KB");
  });
});

describe("mensajeDeDetalle", () => {
  it("extrae mensajes de los distintos formatos de error de la API", () => {
    expect(mensajeDeDetalle(404, "Expediente no encontrado")).toBe("Expediente no encontrado");
    expect(mensajeDeDetalle(409, { mensaje: "El archivo ya fue cargado" })).toBe(
      "El archivo ya fue cargado",
    );
    expect(mensajeDeDetalle(422, [{ msg: "Field required" }])).toBe("Field required");
    expect(mensajeDeDetalle(500, null)).toBe("Error 500");
  });
});
