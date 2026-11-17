export function validarCamposManuales(valores: Record<string, string>, tipo: "FACT" | "RHE" | "GRR" = "FACT"): Record<string, string> {
  const errores: Record<string, string> = {};
  const valor = (nombre: string) => (valores[nombre] ?? "").trim();
  if (!/^[A-Z0-9]{4}$/.test(valor("serie"))) errores.serie = "Ingrese una serie de cuatro caracteres.";
  if (!/^\d{1,32}$/.test(valor("correlativo"))) errores.correlativo = "Ingrese un correlativo numérico.";
  for (const nombre of ["ruc_emisor", "ruc_receptor"]) {
    if (!/^\d{11}$/.test(valor(nombre))) errores[nombre] = "Ingrese 11 dígitos.";
  }
  if (tipo === "GRR") {
    delete errores.ruc_emisor;
    if (!/^[FE][0-9]{3}$/.test(valor("serie_factura"))) errores.serie_factura = "Ingrese la serie fiscal de la factura.";
    if (!/^\d{1,8}$/.test(valor("correlativo_factura")) || Number(valor("correlativo_factura")) === 0) errores.correlativo_factura = "Ingrese el número de factura.";
    if (!/^\d{11}$/.test(valor("emisor_factura_ruc"))) errores.emisor_factura_ruc = "Ingrese 11 dígitos del emisor de la factura.";
    if (valor("emisor_factura_ruc") === valor("ruc_receptor") && valor("ruc_receptor")) errores.emisor_factura_ruc = "Emisor y receptor deben ser distintos.";
    if (Number(valor("correlativo")) === 0) errores.correlativo = "Ingrese un correlativo válido.";
    return errores;
  }
  const fecha = valor("fecha_emision");
  const fechaParsed = new Date(fecha + "T00:00:00Z");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(fecha) || Number.isNaN(fechaParsed.getTime()) || fechaParsed.toISOString().slice(0, 10) !== fecha) errores.fecha_emision = "Ingrese una fecha válida.";
  if (!["PEN", "USD"].includes(valor("moneda"))) errores.moneda = "Seleccione soles o dólares.";
  for (const nombre of ["importe_total", "subtotal", "igv"]) {
    const monto = valor(nombre);
    if (!monto && nombre !== "importe_total") continue;
    if (!/^\d{1,12}(\.\d{1,2})?$/.test(monto)) errores[nombre] = "Ingrese un importe válido con hasta dos decimales.";
  }
  for (const nombre of ["razon_social_emisor", "razon_social_receptor"]) {
    if (valor(nombre).length > 300) errores[nombre] = "Máximo 300 caracteres.";
  }
  return errores;
}
