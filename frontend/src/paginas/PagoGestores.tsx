import { useState } from "react";

import { eliminar, enviarJson, useDatos } from "../api";
import { formatearMonto } from "../formato";

interface Gestor {
  id: string;
  codigo: string;
  nombre: string;
  porcentaje_comision: string | null;
}
interface PagoGestor {
  id: string; gestor_id: string; desde: string; hasta: string;
  moneda: "PEN" | "USD"; produccion: string; porcentaje: string;
  saldo: string; estado: string;
}
interface Cotizacion {
  produccion: string; porcentaje: string; bruto: string;
}

export default function PagoGestores() {
  const gestores = useDatos<Gestor[]>("/api/v1/gestores");
  const pagos = useDatos<PagoGestor[]>("/api/v1/pagos-gestores");
  const [gestorId, setGestorId] = useState("");
  const [desde, setDesde] = useState("2026-10-01");
  const [hasta, setHasta] = useState("2026-10-31");
  const [moneda, setMoneda] = useState<"PEN" | "USD">("PEN");
  const [cotizacion, setCotizacion] = useState<Cotizacion | null>(null);
  const [mensaje, setMensaje] = useState("");
  const [error, setError] = useState("");
  const parametros = { gestor_id: gestorId, desde, hasta, moneda };
  const cotizar = async () => {
    setError(""); setCotizacion(null);
    try {
      const datos = await enviarJson<Cotizacion>("/api/v1/pagos-gestores/cotizar", "POST", parametros);
      setCotizacion(datos);
    } catch (e) { setError(String(e)); }
  };
  const programar = async () => {
    try {
      await enviarJson("/api/v1/pagos-gestores/programar", "POST", parametros);
      pagos.recargar(); setCotizacion(null);
      setMensaje("Pago programado, pendiente de ejecución.");
    } catch (e) { setError(String(e)); }
  };
  const anular = async (id: string) => {
    if (!window.confirm("¿Anular esta programación? La auditoría conservará el registro.")) return;
    try {
      await eliminar("/api/v1/pagos-gestores/" + id);
      pagos.recargar(); setMensaje("Programación anulada.");
    } catch (e) { setError(String(e)); }
  };
  return <>
    <h2>Pago de Gestores</h2>
    <p className="tenue">Cada Usuario programa exclusivamente los pagos de sus Gestores. La comisión usa producción documentada y el porcentaje asignado por Administración; esto no transfiere dinero.</p>
    <div className="filtros">
      <label>Gestor <select value={gestorId} onChange={(e) => { setGestorId(e.target.value); setCotizacion(null); }}>
        <option value="">Seleccionar Gestor</option>
        {gestores.datos?.map((g) => <option key={g.id} value={g.id}>{g.codigo} · {g.nombre} ({g.porcentaje_comision ?? "Sin tasa"}%)</option>)}
      </select></label>
      <label>Desde <input type="date" value={desde} onChange={(e) => { setDesde(e.target.value); setCotizacion(null); }} /></label>
      <label>Hasta <input type="date" value={hasta} onChange={(e) => { setHasta(e.target.value); setCotizacion(null); }} /></label>
      <label>Moneda <select value={moneda} onChange={(e) => { setMoneda(e.target.value as "PEN" | "USD"); setCotizacion(null); }}>
        <option value="PEN">Soles</option><option value="USD">Dólares</option>
      </select></label>
      <button disabled={!gestorId} onClick={() => void cotizar()}>Calcular</button>
    </div>
    {cotizacion && <p>
      Producción: <strong>{formatearMonto(moneda, cotizacion.produccion)}</strong> ·
      Tasa: {cotizacion.porcentaje}% ·
      Comisión: <strong>{formatearMonto(moneda, cotizacion.bruto)}</strong>{" "}
      <button onClick={() => void programar()}>Programar</button>
    </p>}
    {error && <p role="alert">{error}</p>}
    {mensaje && <p role="status">{mensaje}</p>}
    {(gestores.error || pagos.error) && <p role="alert">{gestores.error || pagos.error}</p>}
    <h3>Programaciones registradas</h3>
    <table><thead><tr><th>Gestor</th><th>Periodo</th><th>Producción</th><th>Tasa</th><th>Saldo</th><th>Estado</th><th>Acción</th></tr></thead>
    <tbody>{(pagos.datos ?? []).filter((p) => p.moneda === moneda).map((p) => <tr key={p.id}>
      <td>{gestores.datos?.find((g) => g.id === p.gestor_id)?.codigo ?? p.gestor_id}</td>
      <td>{p.desde} — {p.hasta}</td><td>{formatearMonto(moneda, p.produccion)}</td>
      <td>{p.porcentaje}%</td><td>{formatearMonto(moneda, p.saldo)}</td><td>{p.estado}</td>
      <td>{p.estado === "PROGRAMADO" && <button onClick={() => void anular(p.id)}>Anular</button>}</td>
    </tr>)}</tbody></table>
  </>;
}
