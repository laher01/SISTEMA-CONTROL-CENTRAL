import { useState } from "react";

import { enviarJson, useDatos } from "../api";
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
  pagos: { usuario_id: string; periodo_desde: string; periodo_hasta: string; moneda: string; produccion: string; bruto: string; adelantos: string; saldo: string; estado: string }[];
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
          <select value={moneda} onChange={(e) => setMoneda(e.target.value as "PEN" | "USD")}>
            <option value="PEN">Soles</option><option value="USD">Dólares</option>
          </select>
        </label>}
      </div>
      {(cargando || cargandoEquipo) && <p>Cargando…</p>}
      {(error || errorEquipo) && <p role="alert">{error || errorEquipo}</p>}
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
        <h3>Liquidaciones de mis Usuarios</h3>
        <p>Saldo registrado a Usuarios: <strong>{formatearMonto(moneda, sumar(pagos.filter((p) => p.estado !== "PAGADO").map((p) => p.saldo)))}</strong></p>
        <p className="tenue">Solo se incluyen liquidaciones programadas en el ERP. La remuneración propia del Responsable requiere un plan o liquidación específica y no se calcula de forma automática.</p>
        <table><thead><tr><th>Usuario</th><th>Desde</th><th>Hasta</th><th>Bruto</th><th>Adelantos</th><th>Saldo</th><th>Estado</th></tr></thead>
          <tbody>{pagos.map((p, i) => <tr key={i}><td>{nombreUsuario(p.usuario_id)}</td>
            <td>{p.periodo_desde}</td><td>{p.periodo_hasta}</td>
            <td>{formatearMonto(moneda, p.bruto)}</td><td>{formatearMonto(moneda, p.adelantos)}</td>
            <td>{formatearMonto(moneda, p.saldo)}</td><td>{p.estado}</td></tr>)}</tbody>
        </table>
        {pagos.length === 0 && <p>No existen liquidaciones programadas para tu equipo en esta moneda.</p>}
      </>}
    </>
  );
}
