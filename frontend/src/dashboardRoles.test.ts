import { describe, expect, it } from "vitest";
import { agrupacionInicial, controlesDashboard } from "./dashboardRoles";

describe("Dashboard por rol", () => {
  it.each(["ADMINISTRADOR", "GERENTE", "SECRETARIA"] as const)(
    "%s conserva jerarquía completa", (rol) => {
      expect(controlesDashboard(rol)).toEqual({ responsable: true, usuario: true, gestor: true });
    },
  );
  it("Responsable solo filtra niveles inferiores", () => {
    expect(controlesDashboard("RESPONSABLE")).toEqual({ responsable: false, usuario: true, gestor: true });
  });
  it("Usuario solo filtra sus gestores", () => {
    expect(controlesDashboard("USUARIO")).toEqual({ responsable: false, usuario: false, gestor: true });
    expect(agrupacionInicial("USUARIO")).toBe("gestor");
  });
  it("Gestor no ve filtros jerárquicos superiores", () => {
    expect(controlesDashboard("GESTOR")).toEqual({ responsable: false, usuario: false, gestor: false });
    expect(agrupacionInicial("GESTOR")).toBe("receptor");
  });
});
