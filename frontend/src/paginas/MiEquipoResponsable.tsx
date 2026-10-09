import { useState } from "react";

import { useDatos } from "../api";
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
  pedidos: { usuario_id: string; cliente: string; periodo: string; moneda: string; monto_asignado: string; estado: string }[];
  pagos: { usuario_id: string; periodo_desde: string; periodo_hasta: string; moneda: string; produccion: string; bruto: string; adelantos: string; saldo: string; estado: string }[];
}
type Pestana = "USUARIOS" | "PEDIDOS" | "COBROS" | "PAGOS";

export default function MiEquipoResponsable({ inicial = "USUARIOS" }: { inicial?: Pestana }) {
  const [pestana, setPestana] = useState<Pestana>(inicial);
  const { datos, error, cargando, recargar } = useDatos<UsuarioResponsable[]>(
    "/api/v1/miembros/mis-usuarios",
  );
  const { datos: equipo, error: errorEquipo, cargando: cargandoEquipo, recargar: recargarEquipo } =
    useDatos<Equipo>("/api/v1/responsable/resumen");
  const [moneda, setMoneda] = useState<"PEN" | "USD">("PEN");
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
        {([
          ["USUARIOS", "Mis Usuarios"], ["PEDIDOS", "Pedidos"],
          ["COBROS", "Cobros y clientes"], ["PAGOS", "Pago de Usuarios"],
        ] as const).map(([id, titulo]) => (
          <button key={id} type="button" onClick={() => setPestana(id)}
            aria-pressed={pestana === id}>{titulo}</button>
        ))}
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
        <h3>Pedidos asignados por Gerencia a mis Usuarios</h3>
        <p>Importe asignado: <strong>{formatearMonto(moneda, sumar(pedidos.map((p) => p.monto_asignado)))}</strong></p>
        <p className="tenue">No se incluye ningún pedido sin asignación a un Usuario del equipo.</p>
        <table><thead><tr><th>Usuario</th><th>Cliente</th><th>Mes</th><th>Asignado</th><th>Estado</th></tr></thead>
          <tbody>{pedidos.map((p, i) => <tr key={i}><td>{nombreUsuario(p.usuario_id)}</td>
            <td>{p.cliente}</td><td>{p.periodo}</td>
            <td>{formatearMonto(moneda, p.monto_asignado)}</td><td>{p.estado}</td></tr>)}</tbody>
        </table>
        {pedidos.length === 0 && <p>No hay pedidos distribuidos a tus Usuarios en esta moneda.</p>}
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
