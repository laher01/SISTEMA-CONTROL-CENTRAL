import { useState } from "react";

import { conParametros, enviarJson, useDatos } from "../api";
import { formatearMonto } from "../formato";
import type { FiltroOpcion, SesionActual } from "../tipos";

type Fila = {
  responsable_id: string;
  responsable_codigo: string;
  responsable_nombre: string;
  cliente_id: string;
  cliente_ruc: string;
  cliente_nombre: string;
  agente_retencion: boolean;
  produccion: string;
  porcentaje: string;
  porcentaje_personalizado: boolean;
  comision: string;
  pedido: string;
  exceso: string;
};
type Resumen = {
  desde: string;
  hasta: string;
  moneda: "PEN" | "USD";
  total_produccion: string;
  total_comisiones: string;
  filas: Fila[];
  detalle_historico_clientes?: Array<{ responsable_id: string; cliente_id: string; cliente_ruc: string; cliente_nombre: string; produccion: string; porcentaje: string; comision_referencial: string }>;
  total_pendiente_atribucion?: string;
  pendientes_atribucion?: Array<{ responsable_id: string; responsable: string; registros: number; produccion: string }>;
};
type Pago = {
  id: string;
  responsable_id: string;
  periodo_desde: string;
  periodo_hasta: string;
  moneda: string;
  produccion_total: string;
  comision_total: string;
  estado: string;
  fecha_pago: string | null;
  referencia_pago: string | null;
  abonado: string;
  saldo: string;
  fecha_reprogramada: string | null;
};
type Cambio = { fecha: string; datos: { actor?: string; anterior?: string; nuevo?: string; motivo?: string } };

function mesActual() {
  const ahora = new Date();
  const anio = ahora.getFullYear();
  const mes = String(ahora.getMonth() + 1).padStart(2, "0");
  const ultimo = new Date(anio, ahora.getMonth() + 1, 0).getDate();
  return { desde: `${anio}-${mes}-01`, hasta: `${anio}-${mes}-${ultimo}` };
}

function Historial({ fila }: { fila: Fila }) {
  const { datos, error } = useDatos<Cambio[]>(
    `/api/v1/pagos-responsables/comision/${fila.responsable_id}/${fila.cliente_id}/historial`,
  );
  return <div>
    <strong>Historial de modificaciones</strong>
    {error && <p role="alert">{error}</p>}
    {!datos?.length && <p>No hay modificaciones registradas.</p>}
    {(datos ?? []).map((c, i) => <p key={i}>
      {new Date(c.fecha).toLocaleString("es-PE")} · {c.datos.actor ?? "Sistema"}:
      {" "}{c.datos.anterior ?? "—"}% → {c.datos.nuevo ?? "—"}% · {c.datos.motivo ?? ""}
    </p>)}
  </div>;
}

export default function ComisionesResponsables({ sesion }: { sesion: SesionActual }) {
  const inicial = mesActual();
  const [desde, setDesde] = useState(inicial.desde);
  const [hasta, setHasta] = useState(inicial.hasta);
  const [moneda, setMoneda] = useState<"PEN" | "USD">("PEN");
  const [responsableSeleccionado, setResponsableSeleccionado] = useState("");
  const [accionPago, setAccionPago] = useState<"TOTAL" | "ADELANTO" | "POSTERGAR" | "">("");
  const [pagoSeleccionado, setPagoSeleccionado] = useState("");
  const { datos: responsablesActivos } = useDatos<FiltroOpcion[]>("/api/v1/pagos/responsables");
  const [editando, setEditando] = useState("");
  const [porcentaje, setPorcentaje] = useState("");
  const [motivo, setMotivo] = useState("");
  const [historial, setHistorial] = useState("");
  const [mensaje, setMensaje] = useState("");
  const [procesando, setProcesando] = useState(false);
  const [referenciaPago, setReferenciaPago] = useState("");
  const [comprobante, setComprobante] = useState<File | null>(null);
  const [montoAdelanto, setMontoAdelanto] = useState("");
  const [nuevaFecha, setNuevaFecha] = useState("");
  const [motivoReprogramacion, setMotivoReprogramacion] = useState("");
  const [movimientos, setMovimientos] = useState<Record<string, Array<{ id: string; fecha: string; monto: string; referencia: string }>>>({});
  const [fechaPago, setFechaPago] = useState(() => new Date().toLocaleDateString("en-CA"));
  const { datos, error, cargando, recargar } = useDatos<Resumen>(
    conParametros("/api/v1/pagos-responsables/resumen", { desde, hasta, moneda }),
  );
  const pagos = useDatos<Pago[]>("/api/v1/pagos-responsables");
  const pagosFiltrados = (pagos.datos ?? []).filter(p =>
    (!responsableSeleccionado || p.responsable_id === responsableSeleccionado) &&
    p.moneda === moneda && p.periodo_desde >= desde && p.periodo_hasta <= hasta
  );
  const filas = (datos?.filas ?? []).filter(f => !responsableSeleccionado || f.responsable_id === responsableSeleccionado);
  const detalleHistorico = (datos?.detalle_historico_clientes ?? []).filter(f => !responsableSeleccionado || f.responsable_id === responsableSeleccionado);
  const produccionResponsable = filas.reduce((total, f) => total + Number(f.produccion), 0);
  const comisionResponsable = filas.reduce((total, f) => total + Number(f.comision), 0);
  const produccionHistorica = detalleHistorico.reduce((total, f) => total + Number(f.produccion), 0);
  const comisionReferencial = detalleHistorico.reduce((total, f) => total + Number(f.comision_referencial), 0);
  const responsables = Array.from(
    new Map(filas.map((f) => [f.responsable_id, f.responsable_nombre])).entries(),
  );
  const puedeProgramar = sesion.rol === "GERENTE";
  const puedePagar = sesion.rol === "GERENTE";

  const incorporarHistoricos = async () => {
    if (!responsableSeleccionado || !window.confirm(
      "¿Confirmas que esta producción histórica corresponde a tu Gerencia? " +
      "La incorporación quedará auditada y no modificará facturas de otros Gerentes."
    )) return;
    setProcesando(true);
    setMensaje("");
    try {
      const resultado = await enviarJson<{ cantidad: number; produccion: string }>(
        "/api/v1/pagos-responsables/incorporar-historicos", "POST",
        { responsable_id: responsableSeleccionado, desde, hasta, moneda }
      );
      recargar();
      pagos.recargar();
      setMensaje(`Incorporadas ${resultado.cantidad} facturas por ${formatearMonto(moneda, resultado.produccion)}. Ya puedes programar la liquidación y decidir su pago.`);
    } catch (e) {
      setMensaje(e instanceof Error ? e.message : String(e));
    } finally {
      setProcesando(false);
    }
  };

  const modificar = async (fila: Fila) => {
    setProcesando(true);
    setMensaje("");
    try {
      await enviarJson("/api/v1/pagos-responsables/comision", "PUT", {
        responsable_id: fila.responsable_id,
        cliente_id: fila.cliente_id,
        porcentaje: Number(porcentaje),
        motivo: motivo.trim(),
      });
      setEditando("");
      setMotivo("");
      recargar();
      setHistorial("");
      setMensaje("Porcentaje actualizado y registrado en auditoría.");
    } catch (e) {
      setMensaje(e instanceof Error ? e.message : String(e));
    } finally {
      setProcesando(false);
    }
  };

  const programar = async (responsableId: string) => {
    setProcesando(true);
    try {
      await enviarJson("/api/v1/pagos-responsables/programar", "POST", {
        responsable_id: responsableId, desde, hasta, moneda, observacion: null,
      });
      pagos.recargar();
      setMensaje("Liquidación de Responsable programada, pendiente de pago por Gerencia.");
    } catch (e) {
      setMensaje(e instanceof Error ? e.message : String(e));
    } finally {
      setProcesando(false);
    }
  };
  const pagar = async (pagoId: string, accion: "TOTAL" | "ADELANTO") => {
    if (!referenciaPago.trim() || !fechaPago || !comprobante) {
      setMensaje("Indique fecha, referencia y adjunte el comprobante.");
      return;
    }
    if (accion === "ADELANTO" && !(Number(montoAdelanto) > 0)) {
      setMensaje("Indique el importe positivo del adelanto.");
      return;
    }
    setProcesando(true);
    try {
      const cuerpo = new FormData();
      cuerpo.set("accion", accion);
      cuerpo.set("fecha", fechaPago);
      cuerpo.set("referencia", referenciaPago.trim());
      cuerpo.set("comprobante", comprobante);
      if (accion === "ADELANTO") cuerpo.set("monto", montoAdelanto);
      const response = await fetch(`/api/v1/pagos-responsables/${pagoId}/abonar`, {
        method: "POST", credentials: "same-origin", body: cuerpo,
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(typeof error.detail === "string" ? error.detail : "Error al registrar abono");
      }
      pagos.recargar();
      setReferenciaPago("");
      setMontoAdelanto("");
      setComprobante(null);
      setMensaje("Movimiento registrado con comprobante y saldo actualizado.");
    } catch (e) {
      setMensaje(e instanceof Error ? e.message : String(e));
    } finally {
      setProcesando(false);
    }
  };

  const reprogramar = async (pagoId: string) => {
    if (!nuevaFecha || motivoReprogramacion.trim().length < 5) {
      setMensaje("Indique nueva fecha y motivo de al menos cinco caracteres.");
      return;
    }
    setProcesando(true);
    try {
      await enviarJson(`/api/v1/pagos-responsables/${pagoId}/reprogramar`, "POST", {
        fecha: nuevaFecha, motivo: motivoReprogramacion.trim(),
      });
      pagos.recargar();
      setMensaje("Fecha de pago reprogramada y registrada en auditoría.");
    } catch (e) {
      setMensaje(e instanceof Error ? e.message : String(e));
    } finally {
      setProcesando(false);
    }
  };

  const verMovimientos = async (pagoId: string) => {
    const response = await fetch(`/api/v1/pagos-responsables/${pagoId}/movimientos`, {
      credentials: "same-origin",
    });
    if (!response.ok) {
      setMensaje("No se pudo consultar el historial de abonos.");
      return;
    }
    const datos = await response.json();
    setMovimientos(actual => ({ ...actual, [pagoId]: datos }));
  };

  return <>
    <h3>Producción y comisiones por Responsable</h3>
    <p className="tenue">
      Los importes se calculan a partir de los expedientes, según cliente receptor y
      periodo seleccionado. Los pedidos se comparan por meses comprendidos, incluso
      cuando el rango es parcial. Exceder un pedido genera aviso y no impide el pago.
    </p>
    <div className="filtros">
      <label>Desde <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} /></label>
      <label>Hasta <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} /></label>
      <label>Moneda <select value={moneda} onChange={(e) => setMoneda(e.target.value as "PEN" | "USD")}>
        <option value="PEN">PEN</option><option value="USD">USD</option>
      </select></label>
    </div>
    <div className="filtros">
      <label>Responsable activo
        <select aria-label="Seleccionar Responsable" value={responsableSeleccionado}
          onChange={e => setResponsableSeleccionado(e.target.value)}>
          <option value="">Todos los Responsables</option>
          {(responsablesActivos ?? []).map(r => <option key={r.id} value={r.id}>
            {r.codigo} · {r.nombre}
          </option>)}
        </select>
      </label>
    </div>
    {cargando && <p>Cargando producción…</p>}
    {error && <p role="alert">{error}</p>}
    <div className="resumen-carga">
      <strong>Producción total: {formatearMonto(moneda, datos?.total_produccion ?? "0")}</strong>
      {" · "}
      <strong>Total a pagar por comisiones: {formatearMonto(moneda, datos?.total_comisiones ?? "0")}</strong>
    </div>
    {responsableSeleccionado && <p className="resumen-carga">
      <strong>Responsable seleccionado · Producción atribuida: {formatearMonto(moneda, produccionResponsable)}</strong>
      {" · "}<strong>Comisión autorizada: {formatearMonto(moneda, comisionResponsable)}</strong>
    </p>}
    {sesion.rol === "GERENTE" && Number(datos?.total_pendiente_atribucion ?? 0) > 0 && <section className="panel-configuracion">
      <h4>Producción histórica pendiente de atribución</h4>
      <p className="tenue">Desglose referencial por cliente. Las comisiones mostradas aquí NO son saldos
        pagables hasta que el Gerente confirme que pertenecen a su Gerencia.</p>
      {responsableSeleccionado ? <>
        <div className="tabla-responsive"><table>
          <thead><tr><th>Cliente receptor</th><th>Producción acumulada</th><th>% comisión</th><th>Comisión referencial</th></tr></thead>
          <tbody>{detalleHistorico.map(f => <tr key={f.cliente_id}>
            <td>{f.cliente_nombre}<small className="bloque tenue">{f.cliente_ruc}</small></td>
            <td>{formatearMonto(moneda, f.produccion)}</td><td>{f.porcentaje}%</td>
            <td>{formatearMonto(moneda, f.comision_referencial)}</td>
          </tr>)}</tbody>
          <tfoot><tr><th>Total referencial</th><th>{formatearMonto(moneda, produccionHistorica)}</th><th>—</th>
            <th>{formatearMonto(moneda, comisionReferencial)}</th></tr></tfoot>
        </table></div>
        {produccionHistorica > 0 && <button disabled={procesando} onClick={() => void incorporarHistoricos()}>
          Incorporar a mi Gerencia para liquidar
        </button>}
      </> : <>
        <strong>{formatearMonto(moneda, datos?.total_pendiente_atribucion ?? "0")}</strong>
        <p className="tenue">Seleccione un Responsable para ver el detalle por cliente.</p>
      </>}
    </section>}
    {mensaje && <p role="status">{mensaje}</p>}
    <div className="tabla-responsive"><table>
      <thead><tr>
        <th>Responsable</th><th>Empresa receptora / Cliente</th><th>Producción</th>
        <th>% Comisión</th><th>Agente de retención</th><th>Total comisión</th>
        <th>Pedido</th><th>Exceso</th><th>Acciones</th>
      </tr></thead>
      <tbody>{filas.map((fila) => {
        const llave = `${fila.responsable_id}:${fila.cliente_id}`;
        const editar = editando === llave;
        return <tr key={llave}>
          <td>{fila.responsable_codigo} · {fila.responsable_nombre}</td>
          <td>{fila.cliente_nombre}<small className="bloque tenue">{fila.cliente_ruc}</small></td>
          <td>{formatearMonto(moneda, fila.produccion)}</td>
          <td>{editar ? <>
            <input aria-label="Nuevo porcentaje" type="number" min="0" max="100" step="0.0001"
              value={porcentaje} onChange={(e) => setPorcentaje(e.target.value)} />
            <input aria-label="Motivo del cambio" placeholder="Motivo obligatorio"
              value={motivo} onChange={(e) => setMotivo(e.target.value)} />
          </> : `${fila.porcentaje}%`}</td>
          <td>{fila.agente_retencion ? "Sí" : "No"}</td>
          <td>{formatearMonto(moneda, fila.comision)}</td>
          <td>{formatearMonto(moneda, fila.pedido)}</td>
          <td>{Number(fila.exceso) > 0 ? `Excedido: ${formatearMonto(moneda, fila.exceso)}` : "—"}</td>
          <td>
            {editar ? <>
              <button disabled={procesando || motivo.trim().length < 5 || porcentaje === ""}
                onClick={() => void modificar(fila)}>Guardar</button>
              <button onClick={() => setEditando("")}>Cancelar</button>
            </> : <button onClick={() => {
              setEditando(llave); setPorcentaje(fila.porcentaje); setMotivo("");
            }}>Editar %</button>}
            {" "}
            <button onClick={() => setHistorial(historial === llave ? "" : llave)}>Historial</button>
            {historial === llave && <Historial fila={fila}/>}
          </td>
        </tr>;
      })}</tbody>
    </table></div>
    {puedeProgramar && responsables.map(([id, nombre]) => {
      const f = filas.filter((fila) => fila.responsable_id === id);
      const produccion = f.reduce((total, fila) => total + Number(fila.produccion), 0);
      const comision = f.reduce((total, fila) => total + Number(fila.comision), 0);
      return <p key={id}>Responsable {nombre}: {formatearMonto(moneda, produccion)} de producción
        {" · "}{formatearMonto(moneda, comision)} de comisión
        {" "}<button disabled={procesando} onClick={() => void programar(id)}>
          Programar liquidación
        </button>
      </p>;
    })}
    <h4>Pagos a Responsables</h4>
    <p className="resumen-carga">Saldo global de las liquidaciones: {formatearMonto(moneda, pagosFiltrados.reduce((a, p) => a + Number(p.saldo ?? (p.estado === "PAGADO" ? 0 : p.comision_total)), 0))}</p>
    {puedePagar && pagoSeleccionado && <div className="panel-configuracion">
      <h4>{accionPago === "TOTAL" ? "Pagar saldo completo" :
        accionPago === "ADELANTO" ? "Registrar pago parcial" : "Postergar pago"}</h4>
      {accionPago === "POSTERGAR" ? <div className="filtros">
        <label>Nueva fecha <input type="date" value={nuevaFecha} onChange={e => setNuevaFecha(e.target.value)} /></label>
        <label>Motivo <input value={motivoReprogramacion} onChange={e => setMotivoReprogramacion(e.target.value)}
          placeholder="Motivo de postergación" /></label>
        <button disabled={procesando || !nuevaFecha || motivoReprogramacion.trim().length < 5}
          onClick={() => void reprogramar(pagoSeleccionado)}>Confirmar postergación</button>
      </div> : <div className="filtros">
        <label>Fecha de pago <input type="date" value={fechaPago} onChange={e => setFechaPago(e.target.value)} /></label>
        <label>Referencia bancaria <input value={referenciaPago} onChange={e => setReferenciaPago(e.target.value)} /></label>
        <label>Voucher PDF/JPG/PNG <input type="file" accept=".pdf,.jpg,.jpeg,.png"
          onChange={e => setComprobante(e.target.files?.[0] ?? null)} /></label>
        {accionPago === "ADELANTO" && <label>Importe parcial
          <input type="number" min="0.01" max={pagosFiltrados.find(p => p.id === pagoSeleccionado)?.saldo}
            step="0.01" value={montoAdelanto} onChange={e => setMontoAdelanto(e.target.value)} />
        </label>}
        <button disabled={procesando || !comprobante || referenciaPago.trim().length < 4 ||
          (accionPago === "ADELANTO" && !(Number(montoAdelanto) > 0))}
          onClick={() => void pagar(pagoSeleccionado, accionPago === "TOTAL" ? "TOTAL" : "ADELANTO")}>
          Confirmar {accionPago === "TOTAL" ? "pago completo" : "pago parcial"}
        </button>
      </div>}
    </div>}
    <div className="tabla-responsive"><table>
      <thead><tr><th>Responsable</th><th>Periodo</th><th>Comisión</th>
        <th>Abonado</th><th>Saldo</th><th>Estado</th><th>Referencia</th><th>Acción</th></tr></thead>
      <tbody>{pagosFiltrados.map((p) => <tr key={p.id}>
        <td>{responsables.find(([id]) => id === p.responsable_id)?.[1] ?? p.responsable_id}</td>
        <td>{p.periodo_desde} al {p.periodo_hasta}</td>
        <td>{formatearMonto(p.moneda as "PEN" | "USD", p.comision_total)}</td>
        <td>{formatearMonto(p.moneda as "PEN" | "USD", p.abonado ?? "0")}</td>
        <td>{formatearMonto(p.moneda as "PEN" | "USD", p.saldo ?? p.comision_total)}</td>
        <td>{p.estado}{p.fecha_reprogramada ? ` · ${p.fecha_reprogramada}` : ""}</td>
        <td>{p.referencia_pago ?? "—"}</td>
        <td>
          {puedePagar && !["PAGADO", "ANULADO"].includes(p.estado) && <>
            <select aria-label={`Decidir pago de ${p.responsable_id}`}
              value={pagoSeleccionado === p.id ? accionPago : ""}
              onChange={e => {
                setPagoSeleccionado(p.id);
                setAccionPago(e.target.value as "TOTAL" | "ADELANTO" | "POSTERGAR" | "");
                setMontoAdelanto("");
                setMensaje("");
              }}>
              <option value="">Decidir pago</option>
              <option value="TOTAL">Pagar completo</option>
              <option value="ADELANTO">Pagar parcial</option>
              <option value="POSTERGAR">Postergar</option>
            </select>{" "}
          </>}
          <button onClick={() => void verMovimientos(p.id)}>Movimientos</button>
          {(movimientos[p.id] ?? []).map(m => <div key={m.id}><a href={`/api/v1/pagos-responsables/${p.id}/movimientos/${m.id}/comprobante`} target="_blank" rel="noreferrer">{m.fecha} · {formatearMonto(p.moneda as "PEN" | "USD", m.monto)} · {m.referencia}</a></div>)}
        </td>
      </tr>)}</tbody>
    </table></div>
  </>;
}
