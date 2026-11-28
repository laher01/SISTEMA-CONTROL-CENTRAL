import { expect, it, vi } from "vitest";
import { obtener } from "./api";
import { consultarAvisoEmpresas } from "./avisoEmpresas";

vi.mock("./api", () => ({ obtener: vi.fn() }));

it("consulta una vez cada RUC visible y conserva los hallazgos si falla una fuente", async () => {
  const empresa = { ruc: "20000000001", razon_social: "Proveedor de prueba" };
  vi.mocked(obtener).mockReset()
    .mockResolvedValueOnce([empresa, empresa])
    .mockResolvedValueOnce({ estado: "Con deuda", monto: "12.30" })
    .mockRejectedValueOnce(new Error("SUNAT no disponible"));
  const signal = new AbortController().signal;
  expect(await consultarAvisoEmpresas(signal)).toEqual({
    incompleta: true,
    hallazgos: [{ ruc: empresa.ruc, razon: empresa.razon_social, deuda: "12.30" }],
  });
  expect(obtener).toHaveBeenCalledTimes(3);
  expect(obtener).toHaveBeenNthCalledWith(1, "/api/v1/empresas", signal);
});

it("devuelve una consulta completa sin hallazgos cuando ambas fuentes responden", async () => {
  vi.mocked(obtener).mockReset()
    .mockResolvedValueOnce([{ ruc: "20000000001", razon_social: "Proveedor de prueba" }])
    .mockResolvedValueOnce({ estado: "Sin deuda", monto: "0" })
    .mockResolvedValueOnce({ estado: "No figura en el padrón consultado" });
  expect(await consultarAvisoEmpresas(new AbortController().signal)).toEqual({
    incompleta: false,
    hallazgos: [],
  });
});
