import { describe, expect, it } from "vitest";
import { validarCamposManuales } from "./validacionExpedienteManual";

const factura = { serie: "E001", correlativo: "495", ruc_emisor: "20614885085", ruc_receptor: "20523209176", fecha_emision: "2026-09-24", moneda: "PEN", importe_total: "492.06", subtotal: "417.00", igv: "75.06" };

describe("validación de creación manual", () => {
  it("acepta una factura con identidad completa", () => {
    expect(validarCamposManuales(factura)).toEqual({});
  });
  it("acepta honorarios sin subtotal ni IGV", () => {
    expect(validarCamposManuales({ ...factura, subtotal: "", igv: "" })).toEqual({});
  });
  it("detecta fecha imposible, RUC incompleto y total inválido", () => {
    const errores = validarCamposManuales({ ...factura, fecha_emision: "2026-02-31", ruc_receptor: "123", importe_total: "-5" });
    expect(Object.keys(errores).sort()).toEqual(["fecha_emision", "importe_total", "ruc_receptor"]);
  });
  it("impide confirmar datos fiscales incompletos", () => {
    expect(Object.keys(validarCamposManuales({}))).toHaveLength(7);
  });
  it("rechaza importes con más de dos decimales", () => {
    expect(validarCamposManuales({ ...factura, importe_total: "1.234" }).importe_total).toBeTruthy();
  });
});

describe("GRE provisional", () => {
  const guia = { serie: "EG07", correlativo: "526", serie_factura: "F001", correlativo_factura: "175", emisor_factura_ruc: "20614885085", ruc_receptor: "20523209176" };
  it("no exige monto, moneda ni fecha de factura", () => {
    expect(validarCamposManuales(guia, "GRR")).toEqual({});
  });
  it("no permite usar la serie propia de GRE como factura", () => {
    expect(validarCamposManuales({ ...guia, serie_factura: "EG07" }, "GRR").serie_factura).toBeTruthy();
  });
});
