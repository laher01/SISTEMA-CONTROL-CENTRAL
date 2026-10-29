import { useState } from "react";
import type { FormEvent } from "react";

import { enviarFormulario, enviarJson, useDatos } from "../api";

type Operacion = {
  id: string;
  fecha_reporte: string;
  puerto: string;
  muelle: string;
  planta: string;
  armador_reportante: string | null;
  comprador: string | null;
  remitente: string | null;
  destinatario: string | null;
  facturador: string | null;
  toneladas_declaradas: number | null;
  precio_propuesto: number | null;
  precio_confirmado: number | null;
  precio_confirmado_por: string | null;
  precio_confirmado_at: string | null;
  descarga_prevista: string | null;
  llegada_planta_prevista: string | null;
  jefe_bahia: string | null;
  encargado_muelle: string | null;
  apuntador: string | null;
  factura_serie: string | null;
  factura_correlativo: string | null;
  factura_emitida_at: string | null;
  factura_emitida_por: string | null;
  estado_facturacion: string;
  estado: string;
};

type Descarga = { descarga_id: string; embarcacion_id: string; matricula: string; nombre: string; armador: string | null; patron: string | null; peso_declarado_kg: number | null; inicio_descarga: string | null; fin_descarga: string | null };
type Vehiculo = {
  id: string;
  placa: string;
  tipo: string;
  chofer: string;
  estado: string;
  salida_muelle: string | null;
  llegada_planta: string | null;
  turno: string | null;
  fecha_reporte_planta: string | null;
  inicio_planta: string | null;
  fin_planta: string | null;
};
type Archivo = { id: string; tipo: string; nombre: string; vehiculo_id: string | null };
type Movimiento = { id: string; operacion_id: string | null; clase: string; pagador: string; beneficiario: string; concepto: string; importe: number; moneda: string; registrado_por: string; comprobante_documento_id: string | null; abonado: number; saldo: number; estado: string };
type Paquete = { vehiculo_id: string; placa: string; documentacion_lista: boolean; faltantes: string[] };
type Resumen = {
  total_peso_muelle_kg: number;
  total_peso_aceptado_planta_kg: number;
  vehiculos: Array<{
    vehiculo_id: string;
    placa: string;
    resultado_planta: string;
    peso_aceptado: number | null;
    unidad: string | null;
    peso_muelle_kg: number | null;
  }>;
};

const DOCUMENTOS = [
  ["certificado_matricula", "Certificado de matrícula"],
  ["permiso_pesca", "Permiso de pesca"],
  ["certificado_sanipes", "Certificado SANIPES"],
  ["reporte_satelital", "Constancia / reporte satelital"],
  ["visto_bueno_produce", "Visto bueno PRODUCE"],
  ["guia_remitente", "Guía de remisión remitente"],
  ["guia_transportista", "Guía de remisión transportista"],
  ["acta_fiscalizacion", "Acta de fiscalización"],
  ["formato_descarga", "Formato de descarga"],
  ["certificado_procedencia", "Certificado de procedencia"],
  ["certificado_captura", "Certificado de captura"],
  ["factura", "Factura emitida"],
  ["peso_planta", "Peso registrado en planta"],
  ["otro", "Otro documento"],
] as const;

function fechaHoraLocalActual() {
  const fecha = new Date(Date.now() - new Date().getTimezoneOffset() * 60_000);
  return fecha.toISOString().slice(0, 16);
}

function aFechaHoraLocal(valor: string | null) {
  if (!valor) return "";
  const fecha = new Date(valor);
  return new Date(fecha.getTime() - fecha.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}

async function manejar<T>(accion: () => Promise<T>, alExito: () => void, alError: (mensaje: string) => void) {
  try {
    await accion();
    alExito();
  } catch (error) {
    alError(error instanceof Error ? error.message : String(error));
  }
}

export default function Pesca() {
  const { datos: operaciones, error, cargando, recargar } = useDatos<Operacion[]>("/api/v1/pesca/operaciones");
  const [seleccionada, setSeleccionada] = useState("");
  const [aviso, setAviso] = useState("");
  const op = operaciones?.find((item) => item.id === seleccionada);
  const base = seleccionada ? `/api/v1/pesca/operaciones/${seleccionada}` : "/api/v1/pesca/operaciones";
  const { datos: descargas, recargar: recargarDescargas } = useDatos<Descarga[]>(seleccionada ? `${base}/embarcaciones` : "");
  const { datos: vehiculos, recargar: recargarVehiculos } = useDatos<Vehiculo[]>(seleccionada ? `${base}/vehiculos` : "");
  const { datos: archivos, recargar: recargarArchivos } = useDatos<Archivo[]>(seleccionada ? `${base}/documentos` : "");
  const { datos: paquetes, recargar: recargarPaquetes } = useDatos<Paquete[]>(seleccionada ? `${base}/documentacion` : "");
  const { datos: resumen, recargar: recargarResumen } = useDatos<Resumen>(seleccionada ? `${base}/resumen` : "");
  const { datos: movimientos, recargar: recargarMovimientos } = useDatos<Movimiento[]>(seleccionada ? `${base}/movimientos` : "");
  const { datos: prestamos, recargar: recargarPrestamos } = useDatos<Movimiento[]>("/api/v1/pesca/movimientos-personales");

  const refrescarDetalle = () => {
    recargarDescargas();
    recargarVehiculos();
    recargarArchivos();
    recargarPaquetes();
    recargarResumen();
    recargarMovimientos();
  };

  const registrarMovimiento = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formulario = event.currentTarget;
    const form = new FormData(formulario);
    const clase = String(form.get("clase"));
    void manejar(
      () => enviarJson<Movimiento>("/api/v1/pesca/movimientos", "POST", {
        operacion_id: clase === "prestamo_personal_bahia" ? null : seleccionada,
        clase, pagador: form.get("pagador"), beneficiario: form.get("beneficiario"),
        concepto: form.get("concepto"), importe: Number(form.get("importe")), moneda: form.get("moneda"),
        cantidad: form.get("cantidad") ? Number(form.get("cantidad")) : null,
        tarifa_unitaria: form.get("tarifa_unitaria") ? Number(form.get("tarifa_unitaria")) : null,
      }),
      () => { setAviso("Movimiento guardado con trazabilidad."); formulario.reset(); refrescarDetalle(); recargarPrestamos(); }, setAviso,
    );
  };

  const registrarAbono = (event: FormEvent<HTMLFormElement>, movimientoId: string, trasGuardar: () => void) => {
    event.preventDefault();
    const formulario = event.currentTarget;
    const form = new FormData(formulario);
    void manejar(
      () => enviarJson(`/api/v1/pesca/movimientos/${movimientoId}/abonos`, "POST", {
        importe: Number(form.get("importe")), observacion: form.get("observacion") || null,
      }),
      () => { setAviso("Devolución o reembolso registrado."); formulario.reset(); trasGuardar(); }, setAviso,
    );
  };

  const adjuntarComprobante = (event: FormEvent<HTMLFormElement>, movimientoId: string, trasGuardar: () => void) => {
    event.preventDefault();
    const formulario = event.currentTarget;
    const file = new FormData(formulario).get("archivo");
    if (!(file instanceof File) || !file.size) { setAviso("Selecciona el comprobante del movimiento."); return; }
    const data = new FormData(); data.append("archivo", file);
    void manejar(
      () => enviarFormulario(`/api/v1/pesca/movimientos/${movimientoId}/comprobante`, data),
      () => { setAviso("Comprobante adjuntado al movimiento."); formulario.reset(); trasGuardar(); }, setAviso,
    );
  };
  const listar = () => {
    recargar();
    refrescarDetalle();
  };

  const crearOperacion = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formulario = event.currentTarget;
    const form = new FormData(formulario);
    void manejar(
      () => enviarJson<Operacion>("/api/v1/pesca/operaciones", "POST", {
        puerto: form.get("puerto"), muelle: form.get("muelle"), planta: form.get("planta"),
        armador_reportante: form.get("armador_reportante") || null,
        comprador: form.get("comprador") || null, remitente: form.get("remitente") || null,
        destinatario: form.get("destinatario") || null, facturador: form.get("facturador") || null,
        toneladas_declaradas: form.get("toneladas_declaradas") ? Number(form.get("toneladas_declaradas")) : null,
        precio_propuesto: form.get("precio_propuesto") ? Number(form.get("precio_propuesto")) : null,
        descarga_prevista: form.get("descarga_prevista") ? new Date(String(form.get("descarga_prevista"))).toISOString() : null,
        llegada_planta_prevista: form.get("llegada_planta_prevista") ? new Date(String(form.get("llegada_planta_prevista"))).toISOString() : null,
        jefe_bahia: form.get("jefe_bahia") || null, encargado_muelle: form.get("encargado_muelle") || null,
        apuntador: form.get("apuntador") || null,
      }),
      () => { setAviso("Operación creada."); formulario.reset(); recargar(); },
      setAviso,
    );
  };

  const confirmarPrecio = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!seleccionada) return;
    const form = new FormData(event.currentTarget);
    void manejar(
      () => enviarJson<Operacion>(`${base}/confirmar-precio`, "POST", {
        comprador: form.get("comprador"), precio_confirmado: Number(form.get("precio_confirmado")),
      }),
      () => { setAviso("Precio confirmado y bloqueado para esta operación."); recargar(); }, setAviso,
    );
  };

  const iniciarDescarga = () => {
    if (!seleccionada) return;
    void manejar(
      () => enviarJson<Operacion>(`${base}/iniciar-descarga`, "POST"),
      () => { setAviso("Documentos verificados; descarga autorizada."); listar(); }, setAviso,
    );
  };

  const registrarFactura = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!seleccionada) return;
    const form = new FormData(event.currentTarget);
    void manejar(
      () => enviarJson<Operacion>(`${base}/factura`, "POST", {
        serie: form.get("factura_serie"), correlativo: form.get("factura_correlativo"),
      }),
      () => { setAviso("Factura registrada. Adjunta el comprobante para completar el paquete de pago."); listar(); }, setAviso,
    );
  };

  const agregarEmbarcacion = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!seleccionada) return;
    const formulario = event.currentTarget;
    const form = new FormData(formulario);
    void manejar(
      () => enviarJson<Descarga>(`${base}/embarcaciones`, "POST", {
        matricula: form.get("matricula"), nombre: form.get("nombre"), armador: form.get("armador"), patron: form.get("patron"),
        peso_declarado_kg: form.get("peso_declarado_t") ? Number(form.get("peso_declarado_t")) * 1000 : null,
        inicio_descarga: form.get("inicio_descarga") ? new Date(String(form.get("inicio_descarga"))).toISOString() : null,
        fin_descarga: form.get("fin_descarga") ? new Date(String(form.get("fin_descarga"))).toISOString() : null,
        intermediario: form.get("intermediario") || null,
      }),
      () => { setAviso("Embarcación vinculada."); formulario.reset(); refrescarDetalle(); }, setAviso,
    );
  };

  const agregarVehiculo = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!seleccionada) return;
    const formulario = event.currentTarget;
    const form = new FormData(formulario);
    void manejar(
      () => enviarJson<Vehiculo>(`${base}/vehiculos`, "POST", {
        placa: form.get("placa"), tipo: form.get("tipo"), chofer: form.get("chofer"), turno: form.get("turno") || null,
      }),
      () => { setAviso("Vehículo agregado."); formulario.reset(); refrescarDetalle(); }, setAviso,
    );
  };

  const guardarHorasDescarga = (event: FormEvent<HTMLFormElement>, descargaId: string) => {
    event.preventDefault();
    const formulario = event.currentTarget;
    const form = new FormData(formulario);
    const payload: Record<string, unknown> = { observacion: form.get("observacion") };
    const inicio = form.get("inicio_descarga");
    const fin = form.get("fin_descarga");
    if (inicio) payload.inicio_descarga = new Date(String(inicio)).toISOString();
    if (fin) payload.fin_descarga = new Date(String(fin)).toISOString();
    void manejar(
      () => enviarJson(`/api/v1/pesca/descargas/${descargaId}/fechas`, "PATCH", payload),
      () => { setAviso("Horas reales de descarga actualizadas."); refrescarDetalle(); }, setAviso,
    );
  };

  const subirArchivo = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!seleccionada) return;
    const formulario = event.currentTarget;
    const form = new FormData(formulario);
    const file = form.get("archivo");
    if (!(file instanceof File) || !file.size) { setAviso("Selecciona el archivo o foto que vas a subir."); return; }
    const data = new FormData();
    data.append("archivo", file);
    data.append("tipo", String(form.get("tipo")));
    const idVehiculo = String(form.get("vehiculo"));
    if (idVehiculo) data.append("vehiculo_ids", idVehiculo);
    const idEmbarcacion = String(form.get("embarcacion"));
    if (idEmbarcacion) data.append("embarcacion_ids", idEmbarcacion);
    void manejar(
      () => enviarFormulario(`${base}/documentos`, data),
      () => { setAviso("Documento guardado."); formulario.reset(); refrescarDetalle(); recargar(); }, setAviso,
    );
  };

  const cerrarOperacion = () => {
    if (!seleccionada) return;
    void manejar(
      () => enviarJson(`${base}/cerrar`, "POST"),
      () => { setAviso("Operación cerrada."); listar(); }, setAviso,
    );
  };

  return (
    <section className="pesca">
      <header className="pesca-cabecera">
        <div><p className="sobrelinea">MUELLE · PLANTA</p><h2>Operaciones de pesca</h2><p>Seguimiento de descargas, vehículos, pesos aceptados y documentos.</p></div>
        <button type="button" onClick={listar}>Actualizar</button>
      </header>
      {aviso && <p className="pesca-aviso" role="status">{aviso}<button type="button" onClick={() => setAviso("")}>Cerrar</button></p>}
      <details className="pesca-prestamos-personales">
        <summary>Préstamos personales del jefe de bahía <span>Separados de las operaciones y liquidaciones</span></summary>
        <form className="pesca-form pesca-prestamo-form" onSubmit={registrarMovimiento}>
          <input type="hidden" name="clase" value="prestamo_personal_bahia" />
          <label>Prestamista (jefe de bahía)<input name="pagador" required /></label>
          <label>Armador o patrón que recibió<input name="beneficiario" required /></label>
          <label>Motivo<input name="concepto" required /></label>
          <label>Importe<input name="importe" type="number" min="0.01" step="0.01" required /></label>
          <input type="hidden" name="moneda" value="PEN" />
          <button type="submit">Registrar préstamo personal</button>
        </form>
        <div className="pesca-movimientos">
          {!prestamos?.length ? <p className="muted">No hay préstamos personales registrados.</p> : prestamos.map((item) => <article className="pesca-movimiento" key={item.id}>
            <div><strong>{item.beneficiario}</strong><small>{item.concepto} · prestamista: {item.pagador}</small></div>
            <span>{item.moneda} {Number(item.importe).toFixed(2)} · abonado {Number(item.abonado).toFixed(2)} · saldo {Number(item.saldo).toFixed(2)}</span>
            {item.comprobante_documento_id ? <a href={`/api/v1/pesca/documentos/${item.comprobante_documento_id}/archivo`} target="_blank" rel="noreferrer">Ver constancia del préstamo</a> : <form className="pesca-abono-form" onSubmit={(event) => adjuntarComprobante(event, item.id, recargarPrestamos)}><label>Constancia (opcional)<input name="archivo" type="file" accept="application/pdf,image/jpeg,image/png,image/webp" required /></label><button type="submit">Adjuntar constancia</button></form>}
            {item.saldo > 0 && <form className="pesca-abono-form" onSubmit={(event) => registrarAbono(event, item.id, recargarPrestamos)}>
              <label>Registrar abono<input name="importe" type="number" min="0.01" max={item.saldo} step="0.01" required /></label>
              <label>Nota<input name="observacion" /></label><button type="submit">Guardar devolución</button>
            </form>}
          </article>)}
        </div>
      </details>
      <div className="pesca-columnas">
        <div className="pesca-panel">
          <h3>Nueva operación</h3>
          <form className="pesca-form" onSubmit={crearOperacion}>
            <label>Puerto<input name="puerto" required placeholder="Paita" /></label>
            <label>Muelle<input name="muelle" required placeholder="Nombre del muelle" /></label>
            <label>Planta de destino<input name="planta" required placeholder="Planta procesadora" /></label>
            <details className="pesca-datos-iniciales"><summary>Datos comerciales y preparación</summary>
              <label>Armador que reporta<input name="armador_reportante" /></label>
              <label>Comprador<input name="comprador" /></label>
              <label>Remitente<input name="remitente" placeholder="Quién emite la guía remitente" /></label>
              <label>Destinatario<input name="destinatario" /></label>
              <label>Facturador (si es distinto)<input name="facturador" /></label>
              <label>Toneladas declaradas<input name="toneladas_declaradas" type="number" min="0" step="0.001" /></label>
              <label>Precio propuesto por tonelada (S/)<input name="precio_propuesto" type="number" min="0" step="0.01" /></label>
              <label>Descarga prevista<input name="descarga_prevista" type="datetime-local" /></label>
              <label>Llegada prevista a planta<input name="llegada_planta_prevista" type="datetime-local" /></label>
              <label>Jefe de bahía<input name="jefe_bahia" /></label>
              <label>Encargado de muelle<input name="encargado_muelle" /></label>
              <label>Apuntador<input name="apuntador" /></label>
            </details>
            <button type="submit">Crear operación de hoy</button>
          </form>
          <h3>Operaciones recientes</h3>
          {cargando && <p>Cargando operaciones…</p>}
          {error && <p className="pesca-error">{error}</p>}
          {!cargando && !error && !operaciones?.length && <p>Aún no hay operaciones registradas.</p>}
          <div className="pesca-lista">
            {operaciones?.map((item) => (
              <button className={`pesca-op ${seleccionada === item.id ? "seleccionada" : ""}`} type="button" key={item.id} onClick={() => { setSeleccionada(item.id); setAviso(""); }}>
                <span><strong>{item.muelle}</strong><small>{item.puerto} · {new Date(`${item.fecha_reporte}T12:00:00`).toLocaleDateString("es-PE")}</small></span>
                <span className="pesca-estado">{item.estado === "cerrada" ? "Cerrada" : item.estado === "preparacion" ? "Preparación" : "En descarga"}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="pesca-detalle">
          {!op ? <div className="pesca-vacio"><h3>Selecciona una operación</h3><p>Verás aquí sus embarcaciones, vehículos y registro de planta.</p></div> : <>
            <div className="pesca-titulo-detalle"><div><p className="sobrelinea">{op.puerto} · {op.muelle}</p><h3>{op.planta}</h3></div><span className="pesca-estado grande">{op.estado === "cerrada" ? "Cerrada" : op.estado === "preparacion" ? "Preparación" : "En descarga"}</span></div>
            <section className="pesca-resumen-comercial" aria-label="Datos comerciales y responsables">
              <p><strong>Armador reportante:</strong> {op.armador_reportante || "Pendiente"} · <strong>Comprador:</strong> {op.comprador || "Pendiente"}</p>
              <p><strong>Remitente:</strong> {op.remitente || "Pendiente"} · <strong>Destinatario:</strong> {op.destinatario || "Pendiente"} · <strong>Facturador:</strong> {op.facturador || "Mismo remitente"}</p>
              <p><strong>Toneladas declaradas:</strong> {op.toneladas_declaradas ?? "Pendiente"} · <strong>Precio propuesto:</strong> {op.precio_propuesto == null ? "Pendiente" : `S/ ${Number(op.precio_propuesto).toFixed(2)}/t`}</p>
              <p><strong>Descarga prevista:</strong> {op.descarga_prevista ? new Date(op.descarga_prevista).toLocaleString("es-PE") : "Pendiente"} · <strong>Llegada prevista a planta:</strong> {op.llegada_planta_prevista ? new Date(op.llegada_planta_prevista).toLocaleString("es-PE") : "Pendiente"}</p>
              <p><strong>Jefe de bahía:</strong> {op.jefe_bahia || "—"} · <strong>Encargado:</strong> {op.encargado_muelle || "—"} · <strong>Apuntador:</strong> {op.apuntador || "—"}</p>
            </section>
            {op.precio_confirmado == null && op.estado === "preparacion" ? <form className="pesca-form pesca-confirmar-precio" onSubmit={confirmarPrecio}>
              <h4>Confirmación del comprador</h4>
              <label>Comprador que confirma<input name="comprador" defaultValue={op.comprador ?? ""} required /></label>
              <label>Precio acordado por tonelada (S/)<input name="precio_confirmado" type="number" min="0.01" step="0.01" defaultValue={op.precio_propuesto ?? ""} required /></label>
              <button type="submit">Confirmar y bloquear precio</button>
            </form> : op.precio_confirmado != null && <p className="pesca-precio-bloqueado"><strong>Precio confirmado:</strong> S/ {Number(op.precio_confirmado).toFixed(2)}/t · actor: {op.precio_confirmado_por} · {op.precio_confirmado_at ? new Date(op.precio_confirmado_at).toLocaleString("es-PE") : ""}</p>}
            {op.estado === "preparacion" && <div className="pesca-autorizacion-descarga">
              <strong>Antes de iniciar la descarga, sube:</strong>
              <span>matrícula · permiso de pesca · SANIPES · satelital · visto bueno PRODUCE · guía remitente</span>
              <button type="button" onClick={iniciarDescarga} disabled={op.precio_confirmado == null}>Verificar documentos e iniciar descarga</button>
            </div>}
            <div className="pesca-metricas"><div><small>Peso declarado</small><strong>{op.toneladas_declaradas == null ? "—" : `${Number(op.toneladas_declaradas).toFixed(3)} t`}</strong></div><div><small>Peso muelle</small><strong>{((resumen?.total_peso_muelle_kg ?? 0) / 1000).toFixed(3)} t</strong></div><div><small>Peso aceptado planta</small><strong>{((resumen?.total_peso_aceptado_planta_kg ?? 0) / 1000).toFixed(3)} t</strong></div><div><small>Vehículos</small><strong>{vehiculos?.length ?? 0}</strong></div></div>
            <section className="pesca-control-gastos">
              <h4>Gastos y adelantos de esta operación</h4>
              <p>Los gastos pagados por la empresa, los montos que el jefe de bahía puso de su bolsillo y los adelantos al armador se concilian aquí. Los préstamos personales se controlan en su registro independiente.</p>
              <form className="pesca-form pesca-movimiento-form" onSubmit={registrarMovimiento}>
                <label>Tipo<select name="clase"><option value="gasto_empresa">Gasto pagado por la empresa</option><option value="gasto_bahia_reembolsable">Gasto de operación pagado por jefe de bahía</option><option value="adelanto_armador_empresa">Adelanto de la empresa al armador</option></select></label>
                <label>Pagador<input name="pagador" required placeholder="Empresa o jefe de bahía" /></label>
                <label>Beneficiario / proveedor<input name="beneficiario" required /></label>
                <label>Concepto<input name="concepto" required placeholder="Hielo, cuadrilla, flete…" /></label>
                <label>Importe<input name="importe" type="number" min="0.01" step="0.01" required /></label>
                <label>Moneda<select name="moneda"><option value="PEN">Soles</option><option value="USD">Dólares</option></select></label>
                <label>Cantidad (opcional)<input name="cantidad" type="number" min="0.001" step="0.001" /></label>
                <label>Tarifa unitaria (opcional)<input name="tarifa_unitaria" type="number" min="0" step="0.01" /></label>
                <button type="submit">Guardar movimiento de la operación</button>
              </form>
              <div className="pesca-movimientos">
                {!movimientos?.length ? <p className="muted">Aún no hay gastos ni adelantos registrados.</p> : movimientos.map((item) => <article className="pesca-movimiento" key={item.id}>
                  <div><strong>{item.concepto}</strong><small>{item.clase.replaceAll("_", " ")} · {item.beneficiario} · pagó: {item.pagador}</small></div>
                  <span>{item.moneda} {Number(item.importe).toFixed(2)} · saldo {Number(item.saldo).toFixed(2)} · {item.estado.replaceAll("_", " ")}</span>
                  {item.comprobante_documento_id ? <a href={`/api/v1/pesca/documentos/${item.comprobante_documento_id}/archivo`} target="_blank" rel="noreferrer">Ver comprobante</a> : <form className="pesca-abono-form" onSubmit={(event) => adjuntarComprobante(event, item.id, recargarMovimientos)}><label>Comprobante (opcional)<input name="archivo" type="file" accept="application/pdf,image/jpeg,image/png,image/webp" required /></label><button type="submit">Adjuntar comprobante</button></form>}
                  {item.saldo > 0 && item.clase !== "gasto_empresa" && <form className="pesca-abono-form" onSubmit={(event) => registrarAbono(event, item.id, recargarMovimientos)}>
                    <label>Devolución / reembolso<input name="importe" type="number" min="0.01" max={item.saldo} step="0.01" required /></label>
                    <label>Nota de conciliación<input name="observacion" /></label><button type="submit">Registrar abono</button>
                  </form>}
                </article>)}
              </div>
            </section>
            <div className="pesca-subpaneles">
              {op.estado === "preparacion" && <form className="pesca-form pesca-form-horizontal" onSubmit={agregarEmbarcacion}>
                <h4>Vincular embarcación</h4>
                <label>Matrícula<input name="matricula" required /></label><label>Nombre<input name="nombre" required /></label>
                <label>Armador<input name="armador" required /></label><label>Patrón<input name="patron" required /></label>
                <label>Peso declarado (ton)<input name="peso_declarado_t" type="number" min="0" step="0.001" /></label>
                <label>Inicio real de descarga<input name="inicio_descarga" type="datetime-local" /></label>
                <label>Fin real de descarga<input name="fin_descarga" type="datetime-local" /></label>
                <label>Intermediario (opcional)<input name="intermediario" /></label>
                <button type="submit">Agregar embarcación</button>
              </form>}
              {["preparacion", "en_descarga"].includes(op.estado) && <form className="pesca-form pesca-form-horizontal" onSubmit={agregarVehiculo}>
                <h4>Agregar vehículo</h4><label>Placa<input name="placa" required /></label>
                <label>Tipo<input name="tipo" required placeholder="3 ejes, carreta…" /></label><label>Chofer<input name="chofer" required /></label>
                <label>Turno de planta (si existe)<input name="turno" /></label><button type="submit">Agregar vehículo</button>
              </form>}
            </div>

            <h4>Embarcaciones vinculadas</h4>
            {descargas?.length ? <ul className="pesca-chips">{descargas.map((d) => <li key={d.descarga_id}><strong>{d.nombre}</strong><small>{d.matricula} · Armador: {d.armador || "—"} · Patrón: {d.patron || "—"} · Declarado: {d.peso_declarado_kg == null ? "—" : `${(Number(d.peso_declarado_kg) / 1000).toFixed(3)} t`}</small><small>Descarga real: {d.inicio_descarga ? new Date(d.inicio_descarga).toLocaleString("es-PE") : "—"} a {d.fin_descarga ? new Date(d.fin_descarga).toLocaleString("es-PE") : "—"}</small><details><summary>Editar horas reales (requiere motivo)</summary><form className="pesca-form" onSubmit={(event) => guardarHorasDescarga(event, d.descarga_id)}><label>Inicio real<input name="inicio_descarga" type="datetime-local" defaultValue={aFechaHoraLocal(d.inicio_descarga)} /></label><label>Fin real<input name="fin_descarga" type="datetime-local" defaultValue={aFechaHoraLocal(d.fin_descarga)} /></label><label>Motivo / nota<input name="observacion" required /></label><button type="submit">Guardar horas</button></form></details></li>)}</ul> : <p className="muted">Agrega la primera embarcación.</p>}

            <h4>Vehículos y recepción en planta</h4>
            {!vehiculos?.length ? <p className="muted">Agrega un vehículo para iniciar el seguimiento.</p> : <div className="pesca-vehiculos">{vehiculos.map((v) => {
              const linea = resumen?.vehiculos.find((x) => x.vehiculo_id === v.id);
              const paquete = paquetes?.find((x) => x.vehiculo_id === v.id);
              return <VehiculoCard key={v.id} operationId={seleccionada} vehicle={v} descargas={descargas ?? []} linea={linea} paquete={paquete} alGuardar={() => { setAviso("Datos de vehículo actualizados."); refrescarDetalle(); }} alError={setAviso} />;
            })}</div>}

            <form className="pesca-form pesca-doc-upload" onSubmit={subirArchivo}>
              <h4>Documentación de la operación</h4>
              <label>Tipo de documento<select name="tipo">{DOCUMENTOS.map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>
              <label>Vincular a<select name="vehiculo"><option value="">Toda la operación</option>{vehiculos?.map((v) => <option key={v.id} value={v.id}>{v.placa} · {v.chofer}</option>)}</select></label>
              <label>Vincular certificado a embarcación<select name="embarcacion"><option value="">Documento general / del vehículo</option>{descargas?.map((d) => <option key={d.descarga_id} value={d.embarcacion_id}>{d.nombre} · {d.matricula}</option>)}</select></label>
              <small>El certificado de procedencia debe subirse para toda la operación, sin vincularlo a un vehículo ni a una embarcación.</small>
              <label>Foto o archivo (PDF/JPG/PNG/WEBP)<input name="archivo" type="file" accept="application/pdf,image/jpeg,image/png,image/webp" required /></label>
              <button type="submit">Subir documento</button>
            </form>
            <div className="pesca-documentacion"><strong>Documentación por vehículo</strong>{paquetes?.map((p) => <p key={p.vehiculo_id}><span>{p.placa}</span>{p.documentacion_lista ? <b className="texto-verde">Lista para presentar</b> : <small>Falta: {p.faltantes.join(", ")}</small>}</p>)}</div>
            {op.estado === "cerrada" && <section className="pesca-facturacion">
              <h4>Factura y expediente para pago</h4>
              {op.estado_facturacion === "pendiente" ? <form className="pesca-form pesca-factura-form" onSubmit={registrarFactura}>
                <label>Serie<input name="factura_serie" required placeholder="F001" /></label>
                <label>Correlativo<input name="factura_correlativo" required /></label>
                <button type="submit">Registrar factura emitida</button>
              </form> : <p>Factura {op.factura_serie}-{op.factura_correlativo} · {op.estado_facturacion.replaceAll("_", " ")}</p>}
              {op.estado_facturacion === "pendiente_documento" && <p className="pesca-pendiente-doc">Sube ahora el archivo de la factura en “Documentación de la operación”, con tipo “Factura emitida”.</p>}
              {op.estado_facturacion === "lista_para_pago" && <p className="texto-verde"><strong>Paquete listo para presentar a pago.</strong></p>}
            </section>}
            <details className="pesca-archivos"><summary>Archivos cargados ({archivos?.length ?? 0})</summary><ul>{archivos?.map((a) => <li key={a.id}>{a.tipo.replaceAll("_", " ")} · <a href={`/api/v1/pesca/documentos/${a.id}/archivo`} target="_blank" rel="noreferrer">{a.nombre}</a></li>)}</ul></details>
            {op.estado !== "cerrada" && <button className="pesca-cerrar-op" type="button" disabled={!vehiculos?.length || vehiculos.some((v) => v.estado !== "cerrado")} onClick={cerrarOperacion}>Cerrar operación del día</button>}
          </>}
        </div>
      </div>
    </section>
  );
}

type VehiculoLinea = Resumen["vehiculos"][number];
function VehiculoCard({ operationId, vehicle, descargas, linea, paquete, alGuardar, alError }: {
  operationId: string; vehicle: Vehiculo; descargas: Descarga[]; linea?: VehiculoLinea; paquete?: Paquete;
  alGuardar: () => void; alError: (mensaje: string) => void;
}) {
  const [peso, setPeso] = useState(linea?.peso_aceptado?.toString() ?? "");
  const [unidad, setUnidad] = useState(linea?.unidad ?? "ton");
  const [resultado, setResultado] = useState(linea?.resultado_planta === "pendiente" ? "completo" : linea?.resultado_planta ?? "completo");
  const [cajas, setCajas] = useState("0");
  const [motivo, setMotivo] = useState("");
  const [observacionPeso, setObservacionPeso] = useState("");
  const [foto, setFoto] = useState<File | null>(null);
  const [esperando, setEsperando] = useState(false);
  const [sinFechaFinal, setSinFechaFinal] = useState(false);
  const [descargaId, setDescargaId] = useState(descargas[0]?.descarga_id ?? "");
  const [pesoMuelle, setPesoMuelle] = useState("");
  const [cajasMuelle, setCajasMuelle] = useState("");
  const [inicio, setInicio] = useState(false);
  const [fechaReporte, setFechaReporte] = useState(vehicle.fecha_reporte_planta ?? "");
  const [llegadaManual, setLlegadaManual] = useState(aFechaHoraLocal(vehicle.llegada_planta));
  const [inicioManual, setInicioManual] = useState(aFechaHoraLocal(vehicle.inicio_planta));
  const [finManual, setFinManual] = useState(aFechaHoraLocal(vehicle.fin_planta));
  const [observacionFechas, setObservacionFechas] = useState("");
  const [fechaFinalPeso, setFechaFinalPeso] = useState(fechaHoraLocalActual);
  const asignarCarga = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!descargaId) { alError("Vincula una embarcación primero."); return; }
    setEsperando(true);
    try {
      await enviarJson(`/api/v1/pesca/vehiculos/${vehicle.id}/cargas`, "POST", {
        descarga_id: descargaId, peso_muelle_kg: pesoMuelle ? Number(pesoMuelle) : null,
        cajas: cajasMuelle ? Number(cajasMuelle) : null,
      });
      setPesoMuelle(""); setCajasMuelle(""); alGuardar();
    } catch (error) { alError(error instanceof Error ? error.message : String(error)); }
    finally { setEsperando(false); }
  };
  const iniciarTraslado = async () => {
    setInicio(true);
    try { await enviarJson(`/api/v1/pesca/vehiculos/${vehicle.id}/traslado/iniciar`, "POST"); alGuardar(); }
    catch (error) { alError(error instanceof Error ? error.message : String(error)); }
    finally { setInicio(false); }
  };
  const iniciarPlanta = async () => {
    setInicio(true);
    try { await enviarJson(`/api/v1/pesca/vehiculos/${vehicle.id}/planta/iniciar`, "POST"); alGuardar(); }
    catch (error) { alError(error instanceof Error ? error.message : String(error)); }
    finally { setInicio(false); }
  };
  const iniciarDescargaPlanta = async () => {
    setInicio(true);
    try { await enviarJson(`/api/v1/pesca/vehiculos/${vehicle.id}/planta/descarga/iniciar`, "POST"); alGuardar(); }
    catch (error) { alError(error instanceof Error ? error.message : String(error)); }
    finally { setInicio(false); }
  };
  const guardarFechas = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!observacionFechas.trim()) { alError("Indica el motivo del ajuste de fecha u hora."); return; }
    setEsperando(true);
    try {
      await enviarJson(`/api/v1/pesca/vehiculos/${vehicle.id}/planta/fechas`, "PATCH", {
        fecha_reporte_planta: fechaReporte || null,
        llegada_planta: llegadaManual ? new Date(llegadaManual).toISOString() : null,
        inicio_planta: inicioManual ? new Date(inicioManual).toISOString() : null,
        fin_planta: finManual ? new Date(finManual).toISOString() : null,
        observacion: observacionFechas,
      });
      setObservacionFechas(""); alGuardar();
    } catch (error) { alError(error instanceof Error ? error.message : String(error)); }
    finally { setEsperando(false); }
  };
  const cerrar = async () => {
    if (!foto) { alError("Selecciona la foto de huincha o ticket de planta antes de cerrar."); return; }
    setEsperando(true);
    try {
      await enviarJson(`/api/v1/pesca/vehiculos/${vehicle.id}/planta`, "POST", {
        resultado, peso_aceptado: Number(peso || 0), unidad, cajas_rechazadas: Number(cajas || 0),
        motivo_rechazo: motivo || null, no_registrar_fecha_finalizacion: sinFechaFinal,
        fecha_finalizacion: !sinFechaFinal && fechaFinalPeso ? new Date(fechaFinalPeso).toISOString() : null,
        observacion: observacionPeso || null,
      });
      const data = new FormData(); data.append("archivo", foto); data.append("tipo", "peso_planta"); data.append("vehiculo_ids", vehicle.id);
      await enviarFormulario(`/api/v1/pesca/operaciones/${operationId}/documentos`, data);
      await enviarJson(`/api/v1/pesca/vehiculos/${vehicle.id}/planta/cerrar`, "POST");
      alGuardar();
    } catch (error) { alError(error instanceof Error ? error.message : String(error)); }
    finally { setEsperando(false); }
  };
  const acceptedKg = Number(linea?.peso_aceptado ?? 0) * ({ ton: 1000, kg: 1, lb: 0.45359237, oz: 0.02834952 }[linea?.unidad ?? "ton"] ?? 1000);
  const colorPeso = linea?.peso_muelle_kg == null ? "" : acceptedKg > linea.peso_muelle_kg ? "verde" : acceptedKg === linea.peso_muelle_kg ? "naranja" : "rojo";
  return <article className="pesca-vehiculo">
    <header><div><strong>{vehicle.placa}</strong><small>{vehicle.tipo} · {vehicle.chofer}</small></div><span className={`pesca-estado ${vehicle.estado === "cerrado" ? "cerrado" : ""}`}>{vehicle.estado.replaceAll("_", " ")}</span></header>
    <div className="pesca-vehiculo-meta">
      <span>Turno: {vehicle.turno || "Sin turno"}</span><span>{descargas.length} embarcaciones vinculadas</span>
      {vehicle.salida_muelle && <span>Salió del muelle: {new Date(vehicle.salida_muelle).toLocaleString("es-PE")}</span>}
      {vehicle.llegada_planta && <span>Llegó a planta: {new Date(vehicle.llegada_planta).toLocaleString("es-PE")}</span>}
      {vehicle.inicio_planta && <span>Inició descarga: {new Date(vehicle.inicio_planta).toLocaleString("es-PE")}</span>}
      {vehicle.fin_planta && <span>Terminó descarga: {new Date(vehicle.fin_planta).toLocaleString("es-PE")}</span>}
    </div>
    {vehicle.estado === "pendiente_muelle" && <button type="button" className="pesca-secundario" disabled={inicio} onClick={() => void iniciarTraslado()}>{inicio ? "Registrando…" : "Despachar a planta (verificar carga y documentos)"}</button>}
    {vehicle.estado === "en_traslado" && <button type="button" className="pesca-secundario" disabled={inicio} onClick={() => void iniciarPlanta()}>{inicio ? "Registrando…" : "Registrar llegada real a planta"}</button>}
    {vehicle.estado === "en_planta" && !vehicle.inicio_planta && <button type="button" className="pesca-secundario" disabled={inicio} onClick={() => void iniciarDescargaPlanta()}>{inicio ? "Registrando…" : "Iniciar descarga real en planta"}</button>}
    {["en_planta", "pendiente_evidencia"].includes(vehicle.estado) && <details className="pesca-fechas"><summary>Fechas y horas de planta</summary><form className="pesca-form pesca-fechas-form" onSubmit={(event) => void guardarFechas(event)}>
      <label>Fecha de reporte<input type="date" value={fechaReporte} onChange={(e) => setFechaReporte(e.target.value)} /></label>
      <label>Llegada real a planta<input type="datetime-local" value={llegadaManual} onChange={(e) => setLlegadaManual(e.target.value)} /></label>
      <label>Inicio real de descarga<input type="datetime-local" value={inicioManual} onChange={(e) => setInicioManual(e.target.value)} /></label>
      <label>Fin de descarga<input type="datetime-local" value={finManual} onChange={(e) => setFinManual(e.target.value)} /></label>
      <label>Motivo del ajuste<input value={observacionFechas} onChange={(e) => setObservacionFechas(e.target.value)} required /></label>
      <button type="submit" disabled={esperando}>Guardar fechas</button>
    </form></details>}
    {vehicle.estado === "pendiente_muelle" && <form className="pesca-form pesca-carga-form" onSubmit={(event) => void asignarCarga(event)}>
      <strong>Asignar carga desde muelle</strong>
      <label>Embarcación<select value={descargaId} onChange={(e) => setDescargaId(e.target.value)} required><option value="">Seleccionar…</option>{descargas.map((d) => <option key={d.descarga_id} value={d.descarga_id}>{d.nombre} · {d.matricula}</option>)}</select></label>
      <label>Peso de muelle (kg)<input type="number" min="0" step="0.001" value={pesoMuelle} onChange={(e) => setPesoMuelle(e.target.value)} /></label>
      <label>Cajas (si se registran)<input type="number" min="0" step="1" value={cajasMuelle} onChange={(e) => setCajasMuelle(e.target.value)} /></label>
      <button type="submit" disabled={esperando || !descargaId}>Guardar carga</button>
    </form>}
    {linea?.peso_aceptado != null && <p className={`pesca-diferencia ${colorPeso}`}>Aceptado en planta: {linea.peso_aceptado} {linea.unidad} · comparación muelle: {colorPeso || "pendiente"}</p>}
    {paquete && !paquete.documentacion_lista && <p className="pesca-pendiente-doc">Pendiente: {paquete.faltantes.join(", ")}</p>}
    {["en_planta", "pendiente_evidencia"].includes(vehicle.estado) && Boolean(vehicle.inicio_planta) && <div className="pesca-form pesca-peso-form">
      <label>Resultado<select value={resultado} onChange={(e) => setResultado(e.target.value)}><option value="completo">Completo</option><option value="parcial">Parcial</option><option value="rechazado">Rechazado</option></select></label>
      <label>Peso aceptado<input type="number" min="0" step="0.001" value={peso} onChange={(e) => setPeso(e.target.value)} /></label>
      <label>Unidad<select value={unidad} onChange={(e) => setUnidad(e.target.value)}><option value="ton">Toneladas</option><option value="kg">Kilogramos</option><option value="lb">Libras</option><option value="oz">Onzas</option></select></label>
      {resultado !== "completo" && <label>Cajas rechazadas<input type="number" min="0" step="1" value={cajas} onChange={(e) => setCajas(e.target.value)} /></label>}
      {resultado === "rechazado" && <label>Motivo<select value={motivo} onChange={(e) => setMotivo(e.target.value)}><option value="">Seleccionar…</option><option value="calidad">Calidad</option><option value="contaminacion_quimica">Contaminación química</option><option value="excedente">Excedente</option><option value="otro">Otro</option></select></label>}
      {vehicle.estado === "pendiente_evidencia" && <label>Motivo para corregir o completar el registro<input value={observacionPeso} onChange={(e) => setObservacionPeso(e.target.value)} required /></label>}
      {!sinFechaFinal && <label>Fecha/hora final<input type="datetime-local" value={fechaFinalPeso} onChange={(e) => setFechaFinalPeso(e.target.value)} /></label>}
      <label>Evidencia de peso<input type="file" accept="application/pdf,image/jpeg,image/png,image/webp" onChange={(e) => setFoto(e.target.files?.[0] ?? null)} /></label>
      <label className="pesca-checkbox"><input type="checkbox" checked={sinFechaFinal} onChange={(e) => setSinFechaFinal(e.target.checked)} /> No registrar fecha final</label>
      <button type="button" disabled={esperando || (!peso && resultado !== "rechazado") || (resultado === "rechazado" && !motivo)} onClick={() => void cerrar()}>{esperando ? "Guardando…" : vehicle.estado === "pendiente_evidencia" ? "Completar peso, evidencia y cierre" : "Guardar peso y evidencia"}</button>
    </div>}
  </article>;
}
