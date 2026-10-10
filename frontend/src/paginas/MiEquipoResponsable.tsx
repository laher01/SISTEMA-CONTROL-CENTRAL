import { useState } from "react";

import { eliminar, enviarJson, useDatos } from "../api";
import { formatearMonto } from "../formato";

interface UsuarioResponsable {
  id: string;
  codigo: string;
  nombre: string;
  rol: string;
  activo: boolean;
}
interface Equipo {
  usuarios: { id: string; codigo: string; nombre: string }[];
  clientes: { usuario_id: string; receptor_id: string; ruc: string; razon_social: string; moneda: string; expedientes: number; produccion: string }[];
  pedidos: { id: string; cliente: string; ruc: string; periodo: string; moneda: string; monto_solicitado: string; monto_asignado: string; pendiente_distribuir: string; estado: string; asignaciones: { usuario_id: string; monto: string }[] }[];
  pagos: { id: string; porcentaje: string; usuario_id: string; periodo_desde: string; periodo_hasta: string; moneda: string; produccion: string; bruto: string; adelantos: string; saldo: string; estado: string }[];
}
interface SaldoPendiente { id: string; periodo_mes: string; moneda: string; monto: string; detalle: string }
interface AdelantoPendiente { id: string; fecha: string; moneda: string; monto: string; descripcion: string }
interface LiquidacionUsuario {
  id: string; periodo_desde: string; periodo_hasta: string; moneda: string;
  produccion_total: string; porcentaje: string; bruto: string; adelantos: string;
  saldo: string; estado: string; observacion_adelantos: string; referencia_pago: string;
}
interface CotizacionUsuario {
  produccion: string; saldos_agregados: string; base_global: string;
  porcentaje: string; bruto: string; adelantos: string; neto: string;
  adelantos_pendientes: number;
}
type Pestana = "USUARIOS" | "PEDIDOS" | "COBROS" | "PAGOS";

export default function MiEquipoResponsable({ inicial = "USUARIOS" }: { inicial?: Pestana }) {
  const pestana = inicial;
  const { datos, error, cargando, recargar } = useDatos<UsuarioResponsable[]>(
    "/api/v1/miembros/mis-usuarios",
  );
  const { datos: equipo, error: errorEquipo, cargando: cargandoEquipo, recargar: recargarEquipo } =
    useDatos<Equipo>("/api/v1/responsable/resumen");
  const [moneda, setMoneda] = useState<"PEN" | "USD">("PEN");
  const [usuarioDestino, setUsuarioDestino] = useState<Record<string, string>>({});
  const [montos, setMontos] = useState<Record<string, string>>({});
  const [mensaje, setMensaje] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [nombreNuevo, setNombreNuevo] = useState("");
  const [porcentajeNuevo, setPorcentajeNuevo] = useState("1.5");
  const [creandoUsuario, setCreandoUsuario] = useState(false);
  const [credencialNueva, setCredencialNueva] = useState<{ login: string; clave_temporal: string } | null>(null);
  const [errorAlta, setErrorAlta] = useState("");
  const crearUsuario = async (evento: React.FormEvent<HTMLFormElement>) => {
    evento.preventDefault();
    setCreandoUsuario(true);
    setErrorAlta("");
    setCredencialNueva(null);
    try {
      const alta = await enviarJson<{ credencial: { login: string; clave_temporal: string } }>(
        "/api/v1/miembros/mis-usuarios", "POST", {
          nombre: nombreNuevo,
          porcentaje_produccion: porcentajeNuevo,
        },
      );
      setCredencialNueva(alta.credencial);
      setNombreNuevo("");
      recargar();
      recargarEquipo();
    } catch (error) {
      setErrorAlta(error instanceof Error ? error.message : String(error));
    } finally {
      setCreandoUsuario(false);
    }
  };
  const [usuarioPago, setUsuarioPago] = useState("");
  const [desdePago, setDesdePago] = useState(new Date().toISOString().slice(0, 7) + "-01");
  const [hastaPago, setHastaPago] = useState(new Date().toISOString().slice(0, 10));
  const [cotizacion, setCotizacion] = useState<CotizacionUsuario | null>(null);
  const [porcentajesSaldos, setPorcentajesSaldos] = useState<Record<string, string>>({});
  const [saldosSeleccionados, setSaldosSeleccionados] = useState<string[]>([]);
  const [adelantosSeleccionados, setAdelantosSeleccionados] = useState<string[]>([]);
  const [observacionAdelantos, setObservacionAdelantos] = useState("");
  const [saldoMes, setSaldoMes] = useState(new Date().toISOString().slice(0, 7));
  const [saldoMonto, setSaldoMonto] = useState("");
  const [saldoDetalle, setSaldoDetalle] = useState("");
  const [fechaConfirmacion, setFechaConfirmacion] = useState(new Date().toISOString().slice(0, 10));
  const [referenciaConfirmacion, setReferenciaConfirmacion] = useState("");
  const saldosPendientes = useDatos<SaldoPendiente[]>(
    usuarioPago ? "/api/v1/responsable/pagos/saldos?usuario_id=" + usuarioPago : null,
  );
  const adelantosPendientes = useDatos<AdelantoPendiente[]>(
    usuarioPago ? "/api/v1/responsable/pagos/adelantos?usuario_id=" + usuarioPago : null,
  );
  const liquidaciones = useDatos<LiquidacionUsuario[]>(
    usuarioPago ? "/api/v1/responsable/pagos/liquidaciones?usuario_id=" + usuarioPago : null,
  );
  const [errorPago, setErrorPago] = useState("");
  const parametrosPago = {
    usuario_id: usuarioPago, desde: desdePago, hasta: hastaPago, moneda,
    saldo_ids: saldosSeleccionados, adelanto_ids: adelantosSeleccionados,
    porcentajes_saldos: Object.fromEntries(saldosSeleccionados.map((id) => [id, porcentajesSaldos[id] || null])),
    observacion_adelantos: observacionAdelantos.trim() || null,
  };
  const crearSaldo = async () => {
    try {
      await enviarJson("/api/v1/responsable/pagos/saldos", "POST", {
        usuario_id: usuarioPago, periodo_mes: saldoMes + "-01", moneda,
        monto: saldoMonto, detalle: saldoDetalle.trim(),
      });
      setSaldoMonto(""); setSaldoDetalle("");
      saldosPendientes.recargar();
      setCotizacion(null);
      setMensaje("Saldo mensual registrado con trazabilidad.");
    } catch (e) { setErrorPago(String(e)); }
  };
  const confirmarLiquidacion = async (id: string) => {
    try {
      await enviarJson("/api/v1/responsable/pagos/" + id + "/confirmar", "POST", {
        fecha_pago: fechaConfirmacion, referencia_pago: referenciaConfirmacion.trim(),
      });
      liquidaciones.recargar(); recargarEquipo();
      setReferenciaConfirmacion(""); setMensaje("Pago confirmado con referencia.");
    } catch (e) { setErrorPago(String(e)); }
  };
  const cotizarPago = async () => {
    setCotizacion(null); setErrorPago("");
    try {
      setCotizacion(await enviarJson<CotizacionUsuario>(
        "/api/v1/responsable/pagos/cotizar", "POST", parametrosPago,
      ));
    } catch (e) { setErrorPago(String(e)); }
  };
  const programarPago = async () => {
    setErrorPago("");
    try {
      await enviarJson("/api/v1/responsable/pagos/programar", "POST", parametrosPago);
      recargarEquipo(); liquidaciones.recargar(); saldosPendientes.recargar(); adelantosPendientes.recargar();
      setSaldosSeleccionados([]); setAdelantosSeleccionados([]); setCotizacion(null); setMensaje("Liquidación programada.");
    } catch (e) { setErrorPago(String(e)); }
  };
  const anularPago = async (id: string) => {
    if (!window.confirm("¿Anular programación pendiente? La auditoría conservará el movimiento.")) return;
    try {
      await eliminar("/api/v1/responsable/pagos/" + id);
      recargarEquipo(); liquidaciones.recargar(); saldosPendientes.recargar(); adelantosPendientes.recargar(); setMensaje("Programación anulada.");
    } catch (e) { setErrorPago(String(e)); }
  };
  const distribuir = async (pedidoId: string) => {
    setGuardando(true);
    setMensaje("");
    try {
      await enviarJson(`/api/v1/responsable/pedidos/${pedidoId}/distribuir`, "POST", {
        usuario_id: usuarioDestino[pedidoId], monto: montos[pedidoId],
      });
      recargarEquipo();
      setMensaje("Distribución guardada.");
    } catch (error) {
      setMensaje(error instanceof Error ? error.message : String(error));
    } finally {
      setGuardando(false);
    }
  };
  const nombreUsuario = (id: string) =>
    equipo?.usuarios.find((u) => u.id === id)?.codigo ?? "Usuario";
  const pedidos = (equipo?.pedidos ?? []).filter((p) => p.moneda === moneda);
  const clientes = (equipo?.clientes ?? []).filter((p) => p.moneda === moneda);
  const pagos = (equipo?.pagos ?? []).filter((p) => p.moneda === moneda);
  const sumar = (valores: string[]) => valores.reduce((a, n) => a + Number(n), 0);
  return (
    <>
      <h2>Mi equipo — Responsable</h2>
      <p className="tenue">
        Consulta de tus Usuarios y sus registros dentro de esta Administración.
        Los importes de pedidos y pagos solo reflejan asignaciones o liquidaciones registradas.
        No se realiza ningún pago desde esta pantalla.
      </p>
      <div className="filtros">
        <button type="button" onClick={() => { recargar(); recargarEquipo(); }}>Actualizar</button>
        {pestana !== "USUARIOS" && <label>Moneda{" "}
          <select value={moneda} onChange={(e) => { setMoneda(e.target.value as "PEN" | "USD"); setCotizacion(null); }}>
            <option value="PEN">Soles</option><option value="USD">Dólares</option>
          </select>
        </label>}
      </div>
      {(cargando || cargandoEquipo) && <p>Cargando…</p>}
      {(error || errorEquipo) && <p role="alert">{error || errorEquipo}</p>}
      {pestana === "USUARIOS" && <section className="panel-configuracion">
        <h3>Crear Usuario de mi equipo</h3>
        <p className="tenue">Se generará automáticamente un código y una clave inicial. El Usuario quedará asignado a tu responsabilidad.</p>
        <form onSubmit={(e) => void crearUsuario(e)} className="filtros">
          <label>Nombre completo
            <input value={nombreNuevo} required minLength={3} maxLength={200}
              onChange={(e) => setNombreNuevo(e.target.value)}
              placeholder="Nombres y apellidos" />
          </label>
          <label>Porcentaje de producción (%)
            <input type="number" min="0" max="100" step="0.0001" required
              value={porcentajeNuevo} onChange={(e) => setPorcentajeNuevo(e.target.value)} />
          </label>
          <button type="submit" disabled={creandoUsuario}>
            {creandoUsuario ? "Creando…" : "Crear Usuario"}
          </button>
        </form>
        {errorAlta && <p role="alert">{errorAlta}</p>}
        {credencialNueva && <div className="panel-configuracion" role="status">
          <h3>Credencial inicial — guárdala ahora</h3>
          <p>Usuario: <strong>{credencialNueva.login}</strong></p>
          <p>Clave temporal: <strong>{credencialNueva.clave_temporal}</strong></p>
          <p className="tenue">La clave se muestra una sola vez y deberá cambiarse al ingresar.</p>
          <button type="button" onClick={() => setCredencialNueva(null)}>Ocultar credencial</button>
        </div>}
      </section>}
      {pestana === "USUARIOS" && <table>
        <thead><tr><th>Código</th><th>Nombre</th><th>Estado</th><th>Clientes con expedientes</th></tr></thead>
        <tbody>{(datos ?? []).map((u) => (
          <tr key={u.id}><td>{u.codigo}</td><td>{u.nombre}</td>
            <td>{u.activo ? "Activo" : "Inactivo"}</td>
            <td>{new Set(equipo?.clientes.filter((c) => c.usuario_id === u.id).map((c) => c.receptor_id) ?? []).size}</td>
          </tr>
        ))}</tbody>
      </table>}
      {pestana === "PEDIDOS" && <>
        <h3>Presupuestos brutos recibidos de Gerencia</h3>
        <p>Total solicitado: <strong>{formatearMonto(moneda, sumar(pedidos.map((p) => p.monto_solicitado)))}</strong></p>
        <p className="tenue">Gerencia indica el cliente y el presupuesto. Tú decides qué Usuario atenderá el pedido y cuánto se le asigna, sin superar el total recibido.</p>
        {mensaje && <p role="status">{mensaje}</p>}
        <table>
          <thead><tr><th>Cliente</th><th>Mes</th><th>Presupuesto bruto</th><th>Distribuido</th><th>Disponible</th><th>Estado</th></tr></thead>
          <tbody>{pedidos.map((p) => (
            <tr key={p.id}><td>{p.ruc} · {p.cliente}</td><td>{p.periodo}</td>
              <td>{formatearMonto(moneda, p.monto_solicitado)}</td>
              <td>{formatearMonto(moneda, p.monto_asignado)}</td>
              <td>{formatearMonto(moneda, p.pendiente_distribuir)}</td><td>{p.estado}</td></tr>
          ))}</tbody>
        </table>
        {pedidos.map((p) => (
          <section key={p.id} className="panel-configuracion">
            <h3>Distribuir presupuesto: {p.cliente} ({p.periodo})</h3>
            <div className="filtros">
              <label>Usuario de mi equipo
                <select value={usuarioDestino[p.id] ?? ""} onChange={(e) => setUsuarioDestino((prev) => ({ ...prev, [p.id]: e.target.value }))}>
                  <option value="">Seleccionar Usuario</option>
                  {(equipo?.usuarios ?? []).map((u) => <option key={u.id} value={u.id}>{u.codigo} · {u.nombre}</option>)}
                </select>
              </label>
              <label>Monto
                <input type="number" min="0.01" step="0.01" value={montos[p.id] ?? ""} onChange={(e) => setMontos((prev) => ({ ...prev, [p.id]: e.target.value }))} />
              </label>
              <button type="button" disabled={guardando || p.estado !== "ACTIVO" || !usuarioDestino[p.id] || !montos[p.id]}
                onClick={() => void distribuir(p.id)}>Asignar / actualizar</button>
            </div>
            <table><thead><tr><th>Usuario asignado</th><th>Monto</th></tr></thead>
              <tbody>{p.asignaciones.map((a) => (
                <tr key={a.usuario_id}><td>{nombreUsuario(a.usuario_id)}</td><td>{formatearMonto(moneda, a.monto)}</td></tr>
              ))}</tbody>
            </table>
          </section>
        ))}
        {pedidos.length === 0 && <p>Gerencia aún no te ha asignado pedidos brutos en esta moneda.</p>}
      </>}
      {pestana === "COBROS" && <>
        <h3>Clientes y producción documentada del equipo</h3>
        <p>Producción registrada: <strong>{formatearMonto(moneda, sumar(clientes.map((c) => c.produccion)))}</strong></p>
        <p className="tenue">Esta producción no equivale a cobros recibidos. Los pagos del cliente necesitan conciliación independiente.</p>
        <table><thead><tr><th>Usuario</th><th>RUC</th><th>Cliente/Receptor</th><th>Expedientes</th><th>Producción</th></tr></thead>
          <tbody>{clientes.map((c) => <tr key={`${c.usuario_id}-${c.receptor_id}-${c.moneda}`}>
            <td>{nombreUsuario(c.usuario_id)}</td><td>{c.ruc}</td><td>{c.razon_social}</td>
            <td>{c.expedientes}</td><td>{formatearMonto(moneda, c.produccion)}</td></tr>)}</tbody>
        </table>
        {clientes.length === 0 && <p>No hay expedientes vinculados a tus Usuarios en esta moneda.</p>}
      </>}
      {pestana === "PAGOS" && <>
        <h3>Pago de Usuarios</h3>
        <p>Saldo programado: <strong>{formatearMonto(moneda, sumar(pagos.filter((p) => p.estado === "PROGRAMADO").map((p) => p.saldo)))}</strong></p>
        <p className="tenue">La base es la producción registrada por Usuario, multiplicada por el porcentaje de su plan vigente. Programar no equivale a pagar.</p>
        <div className="filtros">
          <label>Usuario <select value={usuarioPago} onChange={(e) => { setUsuarioPago(e.target.value); setCotizacion(null); }}>
            <option value="">Seleccionar Usuario</option>
            {(equipo?.usuarios ?? []).map((u) => <option key={u.id} value={u.id}>{u.codigo} · {u.nombre}</option>)}
          </select></label>
          <label>Desde <input type="date" value={desdePago} onChange={(e) => { setDesdePago(e.target.value); setCotizacion(null); }} /></label>
          <label>Hasta <input type="date" value={hastaPago} onChange={(e) => { setHastaPago(e.target.value); setCotizacion(null); }} /></label>
          <button type="button" disabled={!usuarioPago} onClick={() => void cotizarPago()}>Calcular pago</button>
        </div>
        {usuarioPago && <>
          <h4>Saldos de compras pendientes por mes</h4>
          <div className="filtros">
            <label>Mes <input type="month" value={saldoMes}
              onChange={(e) => setSaldoMes(e.target.value)} /></label>
            <label>Monto <input type="number" min="0.01" step="0.01" value={saldoMonto}
              onChange={(e) => setSaldoMonto(e.target.value)} /></label>
            <label>Detalle <input value={saldoDetalle} maxLength={500}
              onChange={(e) => setSaldoDetalle(e.target.value)} /></label>
            <button type="button" disabled={!saldoMonto || saldoDetalle.trim().length < 8}
              onClick={() => void crearSaldo()}>Agregar saldo</button>
          </div>
          {(saldosPendientes.datos ?? []).filter((s) => s.moneda === moneda).map((s) =>
            <label key={s.id} className="bloque">
              <input type="checkbox" checked={saldosSeleccionados.includes(s.id)}
                onChange={(e) => { setCotizacion(null); setSaldosSeleccionados((v) =>
                  e.target.checked ? [...v, s.id] : v.filter((x) => x !== s.id)); }} />
              {s.periodo_mes.slice(0, 7)} · {s.detalle} · {formatearMonto(moneda, s.monto)}
              {saldosSeleccionados.includes(s.id) && (
                <span> % histórico del saldo (obligatorio)
                  <input type="number" min="0" max="100" step="0.0001"
                    value={porcentajesSaldos[s.id] ?? ""}
                    onChange={(e) => { setCotizacion(null); setPorcentajesSaldos((v) => ({ ...v, [s.id]: e.target.value })); }}
                    placeholder="Tasa pactada para ese mes" required />
                </span>
              )}
            </label>
          )}
          <h4>Adelantos pendientes: seleccionar los que se descontarán</h4>
          {(adelantosPendientes.datos ?? []).filter((a) => a.moneda === moneda).map((a) =>
            <label key={a.id} className="bloque">
              <input type="checkbox" checked={adelantosSeleccionados.includes(a.id)}
                onChange={(e) => { setCotizacion(null); setAdelantosSeleccionados((v) =>
                  e.target.checked ? [...v, a.id] : v.filter((x) => x !== a.id)); }} />
              {a.fecha} · {a.descripcion} · {formatearMonto(moneda, a.monto)}
            </label>
          )}
          <label>Observación de adelantos no descontados
            <input value={observacionAdelantos} maxLength={500}
              onChange={(e) => setObservacionAdelantos(e.target.value)}
              placeholder="Motivo para dejar adelantos pendientes" />
          </label>
        </>}
        {cotizacion && <p>
          Periodo: {desdePago} al {hastaPago} · Producción: {formatearMonto(moneda, cotizacion.produccion)}
          {" · "}Saldos seleccionados: {formatearMonto(moneda, cotizacion.saldos_agregados)}
          {" · "}Base global: {formatearMonto(moneda, cotizacion.base_global)}
          {" · "}Porcentaje: {cotizacion.porcentaje}%
          {" · "}Bruto: {formatearMonto(moneda, cotizacion.bruto)}
          {" · "}Adelantos: {formatearMonto(moneda, cotizacion.adelantos)}
          {" · "}<strong>Neto: {formatearMonto(moneda, cotizacion.neto)}</strong>
          <button type="button" onClick={() => void programarPago()}>Programar</button>
        </p>}
        <h4>Confirmar pagos programados</h4>
        <div className="filtros">
          <label>Fecha <input type="date" value={fechaConfirmacion}
            onChange={(e) => setFechaConfirmacion(e.target.value)} /></label>
          <label>Referencia de pago
            <input value={referenciaConfirmacion} onChange={(e) => setReferenciaConfirmacion(e.target.value)}
              placeholder="Voucher o referencia bancaria" />
          </label>
        </div>
        {(liquidaciones.datos ?? []).filter((p) => p.moneda === moneda).map((p) => <p key={p.id}>
          {p.periodo_desde}–{p.periodo_hasta} · {p.estado} · Neto {formatearMonto(moneda, p.saldo)}
          {p.estado === "PROGRAMADO" && <button type="button"
            disabled={referenciaConfirmacion.trim().length < 4}
            onClick={() => void confirmarLiquidacion(p.id)}>Confirmar pago</button>}
        </p>)}
        {errorPago && <p role="alert">{errorPago}</p>}
        {mensaje && <p role="status">{mensaje}</p>}
        <table><thead><tr><th>Usuario</th><th>Desde</th><th>Hasta</th><th>Producción</th><th>%</th><th>Bruto</th><th>Adelantos</th><th>Saldo</th><th>Estado</th><th>Acción</th></tr></thead>
          <tbody>{pagos.map((p) => <tr key={p.id}><td>{nombreUsuario(p.usuario_id)}</td><td>{p.periodo_desde}</td><td>{p.periodo_hasta}</td><td>{formatearMonto(moneda, p.produccion)}</td><td>{p.porcentaje}%</td><td>{formatearMonto(moneda, p.bruto)}</td><td>{formatearMonto(moneda, p.adelantos)}</td><td>{formatearMonto(moneda, p.saldo)}</td><td>{p.estado}</td><td>{p.estado === "PROGRAMADO" && Number(p.adelantos) === 0 && <button type="button" onClick={() => void anularPago(p.id)}>Anular</button>}</td></tr>)}</tbody>
        </table>
        {pagos.length === 0 && <p>No hay pagos programados en esta moneda.</p>}
      </>}
    </>
  );
}
