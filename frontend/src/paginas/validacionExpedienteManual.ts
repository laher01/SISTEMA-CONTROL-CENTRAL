export function validarCamposManuales(valores: Record<string, string>): Record<string, string> {
  const errores: Record<string, string> = {};
  const valor = (nombre: string) => (valores[nombre] ?? "").trim();
  if (!/^[A-Z0-9]{4}$/.test(valor("serie"))) errores.serie = "Ingrese una serie de cuatro caracteres.";
  if (!/^\d{1,32}$/.test(valor("correlativo"))) errores.correlativo = "Ingrese un correlativo numérico.";
  for (const nombre of ["ruc_emisor", "ruc_receptor"]) {
    if (!/^\d{11}$/.test(valor(nombre))) errores[nombre] = "Ingrese 11 dígitos.";
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
