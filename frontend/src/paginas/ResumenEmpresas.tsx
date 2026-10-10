import { useState } from "react";

import { useDatos } from "../api";
import { formatearMonto } from "../formato";

type Fila = {
  empresa_id: string; ruc: string; razon_social: string; moneda: string;
  expedientes: number; total: string;
};
type Resumen = { proveedores: Fila[]; clientes: Fila[] };

export default function ResumenEmpresas() {
  const [pestana, setPestana] = useState<"proveedores" | "clientes">("proveedores");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [mes, setMes] = useState("");
  const [moneda, setMoneda] = useState("");
  const params = new URLSearchParams();
  if (desde) params.set("fecha_desde", desde);
  if (hasta) params.set("fecha_hasta", hasta);
  if (moneda) params.set("moneda", moneda);
  const url = "/api/v1/expedientes/resumen-empresas" + (params.size ? "?" + params.toString() : "");
  const { datos, error, cargando } = useDatos<Resumen>(url);
  const filas = datos?.[pestana] ?? [];
  const resumenPorMoneda = filas.reduce<Record<string, { total: number; cantidad: number }>>((a, f) => {
    if (!a[f.moneda]) a[f.moneda] = { total: 0, cantidad: 0 };
    a[f.moneda].total += Number(f.total);
    a[f.moneda].cantidad += f.expedientes;
    return a;
  }, {});
  return <section className="panel-configuracion">
    <h2>Resumen de empresas</h2>
    <p>Acumulados según los expedientes visibles para tu usuario y sus permisos.</p>
    <div className="acciones" role="tablist" aria-label="Empresas por función">
      <button type="button" role="tab" aria-selected={pestana === "proveedores"}
        onClick={() => setPestana("proveedores")}>Proveedores</button>
      <button type="button" role="tab" aria-selected={pestana === "clientes"}
        onClick={() => setPestana("clientes")}>Clientes</button>
    </div>
    <div className="filtros">
      <label>Mes
        <input type="month" value={mes} onChange={(e) => {
          const m = e.target.value;
          setMes(m);
          if (!m) { setDesde(""); setHasta(""); return; }
          const [anio, numero] = m.split("-").map(Number);
          setDesde(m + "-01");
          setHasta(new Date(Date.UTC(anio, numero, 0)).toISOString().slice(0, 10));
        }} />
      </label>
      <label>Desde
        <input type="date" value={desde} onChange={(e) => { setDesde(e.target.value); setMes(""); }} />
      </label>
      <label>Hasta
        <input type="date" value={hasta} onChange={(e) => { setHasta(e.target.value); setMes(""); }} />
      </label>
      <label>Moneda
        <select value={moneda} onChange={(e) => setMoneda(e.target.value)}>
          <option value="">Todas (separadas)</option>
          <option value="PEN">Soles</option>
          <option value="USD">Dólares</option>
        </select>
      </label>
      <button type="button" onClick={() => { setMes(""); setDesde(""); setHasta(""); setMoneda(""); }}>
        Limpiar filtros
      </button>
    </div>
    {cargando && <p>Cargando resumen…</p>}
    {error && <p role="alert">{error}</p>}
    <p><strong>Empresas:</strong> {filas.length}</p>
    {Object.entries(resumenPorMoneda).map(([divisa, valores]) =>
      <p key={divisa}><strong>{divisa}:</strong> {formatearMonto(divisa, valores.total)}
        {" · "}{valores.cantidad} expedientes</p>
    )}
    <div className="tabla-responsive"><table>
      <thead><tr><th>RUC</th><th>Empresa</th><th>Moneda</th><th>Expedientes</th><th>Total acumulado</th></tr></thead>
      <tbody>{filas.map((f) => <tr key={f.empresa_id + "-" + f.moneda}>
        <td>{f.ruc}</td><td>{f.razon_social}</td><td>{f.moneda}</td>
        <td>{f.expedientes}</td><td>{formatearMonto(f.moneda, Number(f.total))}</td>
      </tr>)}</tbody>
    </table></div>
  </section>;
}
