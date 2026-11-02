import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { TablaDocumentos } from "./ExpedienteDetalle";
import type { Documento } from "../tipos";

const expedienteId = "expediente-28200";
const voucher = {
  id: "voucher-28200",
  expediente_id: expedienteId,
  tipo_documento: "VCHR",
  estado: "RELACIONADO",
  sha256: "hash-voucher",
  nombre_original: "28200 - VCH.jpeg",
  mime_type: "image/jpeg",
  tamano_bytes: 1024,
  datos_extraidos: null,
  formato_origen: null,
  fecha_emision: null,
  serie: null,
  correlativo: null,
  moneda: null,
  importe_total: null,
  gestor_id: null,
  usuario_id: null,
  created_at: "2026-10-31T12:00:00Z",
} satisfies Documento;

function htmlDocumentos(puedeVincularPagos: boolean): string {
  return renderToStaticMarkup(createElement(
    MemoryRouter,
    null,
    createElement(TablaDocumentos, {
      documentos: [voucher],
      expedienteId,
      puedeVincularPagos,
      puedeEliminar: false,
      ocupado: false,
      alEliminar: () => {},
    }),
  ));
}

describe("acciones de voucher en el expediente fiscal", () => {
  it("abre el pago agrupado con el archivo existente y el expediente resaltado", () => {
    const html = htmlDocumentos(true);

    expect(html).toContain("href=\"/pagos-documentales/voucher-28200?expediente=expediente-28200\"");
    expect(html).toContain("Vincular a pago agrupado");
  });

  it("no expone la acción de vínculo a roles sin permiso de pagos documentales", () => {
    expect(htmlDocumentos(false)).not.toContain("Vincular a pago agrupado");
  });
});
