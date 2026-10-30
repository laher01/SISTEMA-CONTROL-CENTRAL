import { useState } from "react";

import { eliminar, enviarJson, useDatos } from "../api";
import { formatearMonto } from "../formato";

interface UsuarioResponsable {
  id: string;
  codigo: string;
  nombre: string;
  rol: string;
  activo: boolean;
  porcentaje_con_agente: string | null;
  porcentaje_sin_agente: string | null;
}
interface Equipo {
  usuarios: { id: string; codigo: string; nombre: string }[];
  clientes: { usuario_id: string; receptor_id: string; ruc: string; razon_social: string; moneda: string; expedientes: number; produccion: string; agente_retencion: boolean; porcentaje_usuario: string | null; comision_usuario_referencial: string | null }[];
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
interface CotizacionJonatan {
  modo_base: string; base: string; gente_lima: string; javier: string;
  jonatan: string; total_distribuido: string; excluido_alex: string;
}
interface GerenteVinculado { gerente_id: string; gerente_codigo?: string | null; gerente_nombre?: string | null; activo: boolean }
interface CobrosEquipo {
  gerentes: { gerente_id: string; gerente_codigo: string; gerente_nombre: string; produccion: string; comision: string }[];
  clientes: { gerente_id: string; gerente_codigo: string; gerente_nombre: string; cliente_ruc: string; cliente_nombre: string; produccion: string; porcentaje: string; comision: string }[];
  proveedores: { gerente_id: string; gerente_codigo: string; gerente_nombre: string; ruc: string; razon_social: string; documentos: number; produccion: string }[];
  usuarios: { gerente_id: string; gerente_codigo: string; gerente_nombre: string; usuario_id: string; usuario_codigo: string; usuario_nombre: string; documentos: number; produccion: string; porcentaje_usuario: string | null; comision_referencial_usuario: string | null }[];
  pendientes_revision: { cantidad: number; produccion: string; expedientes: { expediente_id: string; comprobante: string; fecha: string; usuario_codigo: string; usuario_nombre: string; cliente_ruc: string; cliente_nombre: string; produccion: string; motivo: "RECEPTOR_NO_AUTORIZADO" | "GERENCIA_SIN_VINCULO" }[] };
}
type Pestana = "USUARIOS" | "PEDIDOS" | "COBROS" | "PAGOS";
type SubpestanaCobro = "PROVEEDORES" | "CLIENTES" | "USUARIOS";

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
  const [desdeCobro, setDesdeCobro] = useState(new Date().toISOString().slice(0, 8) + "01");
  const [hastaCobro, setHastaCobro] = useState(new Date().toISOString().slice(0, 10));
  const [sincronizandoCobros, setSincronizandoCobros] = useState(false);
  const [subpestanaCobro, setSubpestanaCobro] = useState<SubpestanaCobro>("CLIENTES");
  const [gerentesSeleccionados, setGerentesSeleccionados] = useState<string[] | null>(null);
  const { datos: vinculosGerencia } = useDatos<GerenteVinculado[]>("/api/v1/gerencias/vinculos");
  const { datos: solicitudesCobro, recargar: recargarSolicitudesCobro } = useDatos<Array<{
    id: string; gerente_id: string; desde: string; hasta: string; moneda: string;
    produccion: string; comision: string; estado: string;
  }>>("/api/v1/pagos-responsables/solicitudes-cobro");
  const vinculosActivos = vinculosGerencia?.filter((v) => v.activo) ?? [];
  const gerentesIncluidos = gerentesSeleccionados ?? vinculosActivos.map((v) => v.gerente_id);
  const parametrosCobro = new URLSearchParams({ desde: desdeCobro, hasta: hastaCobro, moneda });
  gerentesIncluidos.forEach((id) => parametrosCobro.append("gerente_ids", id));
  const urlCobro = gerentesIncluidos.length
    ? `/api/v1/pagos-responsables/equipo-resumen?${parametrosCobro.toString()}`
    : null;
  const cobrosEquipo = useDatos<CobrosEquipo>(urlCobro);
  const [guardando, setGuardando] = useState(false);
  const [nombreNuevo, setNombreNuevo] = useState("");
  const [porcentajeConNuevo, setPorcentajeConNuevo] = useState("1.5");
  const [porcentajeSinNuevo, setPorcentajeSinNuevo] = useState("1.5");
  const [tasasEditando, setTasasEditando] = useState<string | null>(null);
  const [tasasCon, setTasasCon] = useState("1.5");
  const [tasasSin, setTasasSin] = useState("1.5");
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
          porcentaje_con_agente: porcentajeConNuevo,
          porcentaje_sin_agente: porcentajeSinNuevo,
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
  const [cotizacionJonatan, setCotizacionJonatan] = useState<CotizacionJonatan | null>(null);
  const [baseJonatan, setBaseJonatan] = useState("");
  const [usarTotalJonatan, setUsarTotalJonatan] = useState(false);
  const esJonatan = (equipo?.usuarios.find((u) => u.id === usuarioPago)?.codigo ?? "")
    .trim().toUpperCase() === "JONA01";
  const [saldosSeleccionados, setSaldosSeleccionados] = useState<string[]>([]);
  const [adelantosSeleccionados, setAdelantosSeleccionados] = useState<string[]>([]);
  const [observacionAdelantos, setObservacionAdelantos] = useState("");
  const [adelantoFecha, setAdelantoFecha] = useState(new Date().toISOString().slice(0, 10));
  const [adelantoMonto, setAdelantoMonto] = useState("");
  const [adelantoDescripcion, setAdelantoDescripcion] = useState("");
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
  const crearAdelanto = async () => {
    try {
      await enviarJson("/api/v1/responsable/pagos/adelantos", "POST", {
        usuario_id: usuarioPago, fecha: adelantoFecha, moneda,
        monto: adelantoMonto, descripcion: adelantoDescripcion.trim(),
      });
      setAdelantoMonto(""); setAdelantoDescripcion("");
      adelantosPendientes.recargar(); setCotizacion(null);
      setMensaje("Adelanto registrado para descontar al programar el pago.");
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
    setCotizacion(null); setCotizacionJonatan(null); setErrorPago("");
    try {
      const resultado = await enviarJson<CotizacionUsuario>(
        "/api/v1/responsable/pagos/cotizar", "POST", parametrosPago,
      );
      setCotizacion(resultado);
      if (esJonatan) {
        const especial = await enviarJson<CotizacionJonatan>(
          "/api/v1/responsable/pagos/formulas/simular-jonatan", "POST", {
            usuario_id: usuarioPago, total_emitido: resultado.produccion,
            base_autorizada: usarTotalJonatan ? null : baseJonatan,
            usar_total_emitido: usarTotalJonatan,
          },
        );
        setCotizacionJonatan(especial);
      }
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
  const generarSolicitudCobro = async (gerenteId: string) => {
    try {
      await enviarJson("/api/v1/pagos-responsables/solicitudes-cobro", "POST", {
        gerente_id: gerenteId, desde: desdeCobro, hasta: hastaCobro, moneda,
      });
      recargarSolicitudesCobro();
      setMensaje("Solicitud de cobro enviada a Gerencia.");
    } catch (e) {
      setErrorPago(e instanceof Error ? e.message : String(e));
    }
  };
  const sincronizarCobros = async () => {
    setSincronizandoCobros(true);
    setMensaje("");
    try {
      const resultado = await enviarJson<{ vinculados: number; produccion: string }>(
        "/api/v1/pagos-responsables/equipo-sincronizar",
        "POST",
        { desde: desdeCobro, hasta: hastaCobro, moneda },
      );
      cobrosEquipo.recargar();
      setMensaje(
        resultado.vinculados > 0
          ? `Se vincularon ${resultado.vinculados} expedientes con pedidos inequívocos por ${formatearMonto(moneda, resultado.produccion)}.`
          : "No hay expedientes pendientes con un único pedido coincidente. Revisa los documentos excluidos abajo.",
      );
    } catch (error) {
      setMensaje(error instanceof Error ? error.message : String(error));
    } finally {
      setSincronizandoCobros(false);
    }
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
          <label>% con agente
            <input type="number" min="0" max="100" step="0.0001" required
              value={porcentajeConNuevo} onChange={(e) => setPorcentajeConNuevo(e.target.value)} />
          </label>
          <label>% sin agente
            <input type="number" min="0" max="100" step="0.0001" required
              value={porcentajeSinNuevo} onChange={(e) => setPorcentajeSinNuevo(e.target.value)} />
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
        <thead><tr><th>Código</th><th>Nombre</th><th>Estado</th><th>% con agente</th><th>% sin agente</th><th>Editar tasas</th><th>Clientes con expedientes</th></tr></thead>
        <tbody>{(datos ?? []).map((u) => (
          <tr key={u.id}><td>{u.codigo}</td><td>{u.nombre}</td>
            <td>{u.activo ? "Activo" : "Inactivo"}</td>
            <td>{u.porcentaje_con_agente ?? "—"}%</td>
            <td>{u.porcentaje_sin_agente ?? "—"}%</td>
            <td>{tasasEditando === u.id ? <>
              <input aria-label="% con agente" type="number" min="0" max="100" step="0.0001"
                value={tasasCon} onChange={(e) => setTasasCon(e.target.value)} />
              <input aria-label="% sin agente" type="number" min="0" max="100" step="0.0001"
                value={tasasSin} onChange={(e) => setTasasSin(e.target.value)} />
              <button type="button" onClick={async () => {
                try {
                  await enviarJson(`/api/v1/miembros/mis-usuarios/${u.id}/porcentajes`, "PATCH", {
                    porcentaje_con_agente: tasasCon, porcentaje_sin_agente: tasasSin,
                  });
                  setTasasEditando(null);
                  recargar();
                  setMensaje("Porcentajes actualizados.");
                } catch (error) { setMensaje(String(error)); }
              }}>Guardar</button>
              <button type="button" onClick={() => setTasasEditando(null)}>Cancelar</button>
            </> : <button type="button" onClick={() => {
              setTasasEditando(u.id);
              setTasasCon(u.porcentaje_con_agente ?? "1.5");
              setTasasSin(u.porcentaje_sin_agente ?? "1.5");
            }}>Editar</button>}</td>
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
        <h3>Cobros y clientes</h3>
        <p className="tenue">Consulta la producción del periodo. El cálculo de clientes aplica el porcentaje de comisión acordado por receptor; proveedores y Usuarios son vistas separadas.</p>
        <div className="filtros">
          <label>Desde <input type="date" value={desdeCobro} onChange={(e) => setDesdeCobro(e.target.value)} /></label>
          <label>Hasta <input type="date" value={hastaCobro} onChange={(e) => setHastaCobro(e.target.value)} /></label>
          <button type="button" disabled={sincronizandoCobros} onClick={() => void sincronizarCobros()}>
            {sincronizandoCobros ? "Vinculando pedidos…" : "Vincular pedidos coincidentes y actualizar"}
          </button>
        </div>
        {mensaje && <p role="status">{mensaje}</p>}
        <fieldset>
          <legend>Gerentes incluidos</legend>
          {vinculosActivos.map((v) => <label key={v.gerente_id} className="bloque">
            <input type="checkbox" checked={gerentesIncluidos.includes(v.gerente_id)}
              onChange={(e) => setGerentesSeleccionados((actual) => {
                const incluidos = actual ?? vinculosActivos.map((vinculo) => vinculo.gerente_id);
                return e.target.checked
                  ? [...new Set([...incluidos, v.gerente_id])]
                  : incluidos.filter((id) => id !== v.gerente_id);
              })} />
            {v.gerente_codigo ?? v.gerente_id} · {v.gerente_nombre ?? "Gerente"}
          </label>)}
          {vinculosActivos.length === 0 && <p>No tienes Gerentes vinculados activos.</p>}
        </fieldset>
        {cobrosEquipo.cargando && <p>Cargando resumen…</p>}
        {cobrosEquipo.error && <p role="alert">{cobrosEquipo.error}</p>}
        {cobrosEquipo.datos && <>
          <section className="panel-configuracion">
            <strong>Totales del periodo: {desdeCobro} al {hastaCobro}</strong>
            <p>Producción bruta: <strong>{formatearMonto(moneda, sumar(cobrosEquipo.datos.gerentes.map((g) => g.produccion)))}</strong></p>
            <p>Comisión que corresponde cobrar: <strong>{formatearMonto(moneda, sumar(cobrosEquipo.datos.gerentes.map((g) => g.comision)))}</strong></p>
          </section>
          <h4>Resumen por Gerente</h4>
          <table><thead><tr><th>Gerente</th><th>Producción bruta</th><th>Comisión a cobrar</th><th>Solicitud</th></tr></thead>
            <tbody>{cobrosEquipo.datos.gerentes.map((g) => <tr key={g.gerente_id}>
              <td>{g.gerente_codigo} · {g.gerente_nombre}</td>
              <td>{formatearMonto(moneda, g.produccion)}</td>
              <td>{formatearMonto(moneda, g.comision)}</td>
              <td><button type="button" onClick={() => void generarSolicitudCobro(g.gerente_id)}>Enviar solicitud de cobro</button></td>
            </tr>)}</tbody>
          </table>
          <nav className="filtros" aria-label="Vistas de cobros">
            <button type="button" aria-pressed={subpestanaCobro === "PROVEEDORES"} onClick={() => setSubpestanaCobro("PROVEEDORES")}>Proveedores</button>
            <button type="button" aria-pressed={subpestanaCobro === "CLIENTES"} onClick={() => setSubpestanaCobro("CLIENTES")}>Clientes</button>
            <button type="button" aria-pressed={subpestanaCobro === "USUARIOS"} onClick={() => setSubpestanaCobro("USUARIOS")}>Usuarios (referencia)</button>
          </nav>
          {cobrosEquipo.datos.pendientes_revision.cantidad > 0 && <section className="panel-configuracion" role="status">
            <h4>Documentos fuera del cálculo de cobros</h4>
            <p>
              Hay {cobrosEquipo.datos.pendientes_revision.cantidad} expedientes activos por {formatearMonto(moneda, cobrosEquipo.datos.pendientes_revision.produccion)} excluidos del cobro. Revisa la autorización del cliente o la relación con Gerencia/Pedido; no se atribuyen ni comisionan automáticamente.
            </p>
            <table><thead><tr><th>Comprobante</th><th>Fecha</th><th>Usuario</th><th>Cliente</th><th>Motivo</th><th>Producción excluida</th></tr></thead>
              <tbody>{cobrosEquipo.datos.pendientes_revision.expedientes.map((p) => <tr key={p.expediente_id}>
                <td>{p.comprobante}</td><td>{p.fecha}</td><td>{p.usuario_codigo} · {p.usuario_nombre}</td>
                <td>{p.cliente_nombre} · {p.cliente_ruc}</td>
                <td>{p.motivo === "RECEPTOR_NO_AUTORIZADO" ? "Cliente no autorizado" : "Sin vínculo a Gerencia/Pedido"}</td>
                <td>{formatearMonto(moneda, p.produccion)}</td>
              </tr>)}</tbody>
            </table>
          </section>}
          {subpestanaCobro === "PROVEEDORES" && <table>
            <thead><tr><th>Gerente</th><th>RUC proveedor</th><th>Proveedor</th><th>Documentos</th><th>Compras</th></tr></thead>
            <tbody>{cobrosEquipo.datos.proveedores.map((p, i) => <tr key={`${p.gerente_id}-${p.ruc}-${i}`}>
              <td>{p.gerente_codigo}</td><td>{p.ruc}</td><td>{p.razon_social}</td><td>{p.documentos}</td><td>{formatearMonto(moneda, p.produccion)}</td>
            </tr>)}</tbody>
          </table>}
          {subpestanaCobro === "PROVEEDORES" && cobrosEquipo.datos.proveedores.length === 0 && <p>No hay compras de proveedores autorizados vinculadas a los Gerentes seleccionados en este periodo.</p>}
          {subpestanaCobro === "CLIENTES" && <table>
            <thead><tr><th>Gerente</th><th>RUC cliente</th><th>Cliente / receptor</th><th>Producción</th><th>% acordado</th><th>Comisión a cobrar</th></tr></thead>
            <tbody>{cobrosEquipo.datos.clientes.map((c, i) => <tr key={`${c.gerente_id}-${c.cliente_ruc}-${i}`}>
              <td>{c.gerente_codigo}</td><td>{c.cliente_ruc}</td><td>{c.cliente_nombre}</td>
              <td>{formatearMonto(moneda, c.produccion)}</td><td>{c.porcentaje}%</td><td>{formatearMonto(moneda, c.comision)}</td>
            </tr>)}</tbody>
          </table>}
          {subpestanaCobro === "CLIENTES" && cobrosEquipo.datos.clientes.length === 0 && <p>No hay producción de clientes autorizados vinculada a los Gerentes seleccionados en este periodo.</p>}
          {subpestanaCobro === "USUARIOS" && <table>
            <thead><tr><th>Gerente</th><th>Usuario</th><th>Documentos</th><th>Producción</th><th>% Usuario</th><th>Comisión referencial</th></tr></thead>
            <tbody>{cobrosEquipo.datos.usuarios.map((u, i) => <tr key={`${u.gerente_id}-${u.usuario_id}-${i}`}>
              <td>{u.gerente_codigo}</td><td>{u.usuario_codigo} · {u.usuario_nombre}</td><td>{u.documentos}</td>
              <td>{formatearMonto(moneda, u.produccion)}</td><td>{u.porcentaje_usuario ? `${u.porcentaje_usuario}%` : "Sin tasa"}</td>
              <td>{u.comision_referencial_usuario ? formatearMonto(moneda, u.comision_referencial_usuario) : "Sin tasa"}</td>
            </tr>)}</tbody>
          </table>}
          {subpestanaCobro === "USUARIOS" && cobrosEquipo.datos.usuarios.length === 0 && <p>No hay producción vinculada a los Gerentes seleccionados para este periodo.</p>}
          <h4>Solicitudes de cobro enviadas</h4>
          {(solicitudesCobro ?? []).filter((s) => s.moneda === moneda).map((s) => <p key={s.id}>
            {s.desde}–{s.hasta} · {s.estado} · Producción {formatearMonto(moneda, s.produccion)} · Comisión {formatearMonto(moneda, s.comision)}
          </p>)}
        </>}
      </>}
      {pestana === "PAGOS" && <>
        <h3>Pago de Usuarios</h3>
        <p>Saldo programado: <strong>{formatearMonto(moneda, sumar(pagos.filter((p) => p.estado === "PROGRAMADO").map((p) => p.saldo)))}</strong></p>
        <p className="tenue">El cálculo aplica el porcentaje del plan a la producción. Los saldos pendientes se suman como dinero adeudado, sin porcentaje; los adelantos se descuentan una sola vez. Programar no equivale a pagar.</p>
        <div className="filtros">
          <label>Usuario <select value={usuarioPago} onChange={(e) => { setUsuarioPago(e.target.value); setCotizacion(null); }}>
            <option value="">Seleccionar Usuario</option>
            {(equipo?.usuarios ?? []).map((u) => <option key={u.id} value={u.id}>{u.codigo} · {u.nombre}</option>)}
          </select></label>
          <label>Desde <input type="date" value={desdePago} onChange={(e) => { setDesdePago(e.target.value); setCotizacion(null); }} /></label>
          <label>Hasta <input type="date" value={hastaPago} onChange={(e) => { setHastaPago(e.target.value); setCotizacion(null); }} /></label>
          <button type="button" disabled={!usuarioPago || (esJonatan && !usarTotalJonatan && !(Number(baseJonatan) > 0))}
            onClick={() => void cotizarPago()}>{esJonatan ? "Calcular distribución especial" : "Calcular pago"}</button>
        </div>
        {esJonatan && <section className="panel-configuracion">
          <h4>Regla especial JONA01 — distribución 2.6875 %</h4>
          <p className="tenue">Elige una base manual autorizada o confirma expresamente el total emitido. Esta simulación muestra los importes por beneficiario y no registra giros.</p>
          <label><input type="checkbox" checked={usarTotalJonatan}
            onChange={(e) => { setUsarTotalJonatan(e.target.checked); setCotizacionJonatan(null); }} />
            Confirmo usar el total emitido del periodo
          </label>
          {!usarTotalJonatan && <label>Base manual autorizada
            <input type="number" min="0.01" step="0.01" value={baseJonatan}
              onChange={(e) => { setBaseJonatan(e.target.value); setCotizacionJonatan(null); }} />
          </label>}
          {cotizacionJonatan && <table><thead><tr><th>Bolsa / beneficiario</th><th>Importe</th></tr></thead><tbody>
            <tr><td>Gente y Lima</td><td>{formatearMonto(moneda, cotizacionJonatan.gente_lima)}</td></tr>
            <tr><td>Javier</td><td>{formatearMonto(moneda, cotizacionJonatan.javier)}</td></tr>
            <tr><td>Jonatan</td><td>{formatearMonto(moneda, cotizacionJonatan.jonatan)}</td></tr>
            <tr><th>Total distribuido</th><th>{formatearMonto(moneda, cotizacionJonatan.total_distribuido)}</th></tr>
          </tbody></table>}
        </section>}
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
            </label>
          )}
          <h4>Registrar adelanto entregado</h4>
          <div className="filtros">
            <label>Fecha <input type="date" value={adelantoFecha} onChange={(e) => setAdelantoFecha(e.target.value)} /></label>
            <label>Monto <input type="number" min="0.01" step="0.01" value={adelantoMonto}
              onChange={(e) => setAdelantoMonto(e.target.value)} /></label>
            <label>Descripción <input value={adelantoDescripcion} maxLength={500}
              onChange={(e) => setAdelantoDescripcion(e.target.value)} placeholder="Motivo del adelanto" /></label>
            <button type="button" disabled={!adelantoMonto || adelantoDescripcion.trim().length < 4}
              onClick={() => void crearAdelanto()}>Agregar adelanto</button>
          </div>
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
          {!esJonatan && <button type="button" onClick={() => void programarPago()}>Programar</button>}
          {esJonatan && <span className="tenue">La fórmula especial queda en simulación; el pago estándar está deshabilitado para no enviar el total a un solo Usuario.</span>}
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
