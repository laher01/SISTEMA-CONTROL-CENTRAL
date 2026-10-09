import { useState } from "react";

import { conParametros, useDatos } from "../api";
import { formatearMonto } from "../formato";

type Fila = { id: string; codigo: string; nombre: string; registros: number; monto: string };
type Resumen = { total: string; filas: Fila[] };
type Moneda = "PEN" | "USD";

function limiteMes(fecha: Date) {
  const y = fecha.getFullYear();
  const m = String(fecha.getMonth() + 1).padStart(2, "0");
  const ultimo = String(new Date(y, fecha.getMonth() + 1, 0).getDate()).padStart(2, "0");
  return { desde: `${y}-${m}-01`, hasta: `${y}-${m}-${ultimo}` };
}

export default function ConsolidadoGerencia() {
  const hoy = new Date();
  const actual = limiteMes(hoy);
  const anterior = limiteMes(new Date(hoy.getFullYear(), hoy.getMonth() - 1, 1));
  const [grupo, setGrupo] = useState<"CLIENTE" | "RESPONSABLE">("CLIENTE");
  const [desde, setDesde] = useState(actual.desde);
  const [hasta, setHasta] = useState(actual.hasta);
  const [moneda, setMoneda] = useState<Moneda>("PEN");
  const [filtrado, setFiltrado] = useState(false);
  const resumen = useDatos<Resumen>(conParametros("/api/v1/pagos/consolidado", { desde, hasta, moneda, agrupar: grupo }));
  const actualGlobal = useDatos<Resumen>(conParametros("/api/v1/pagos/consolidado", { ...actual, moneda, agrupar: grupo }));
  const anteriorGlobal = useDatos<Resumen>(conParametros("/api/v1/pagos/consolidado", { ...anterior, moneda, agrupar: grupo }));
  return <section>
    <h3>Consolidado de compras</h3>
    <p className="tenue">Montos brutos de expedientes registrados. No representan pagos o cobros confirmados.</p>
    <div className="acciones">
      <button className={grupo === "CLIENTE" ? "activo" : undefined} onClick={() => setGrupo("CLIENTE")}>Por clientes / receptores</button>
      <button className={grupo === "RESPONSABLE" ? "activo" : undefined} onClick={() => setGrupo("RESPONSABLE")}>Por responsables</button>
    </div>
    <div className="filtros">
      <label>Desde <input type="date" value={desde} onChange={e => { setDesde(e.target.value); setFiltrado(true); }} /></label>
      <label>Hasta <input type="date" value={hasta} onChange={e => { setHasta(e.target.value); setFiltrado(true); }} /></label>
      <label>Moneda <select value={moneda} onChange={e => setMoneda(e.target.value as Moneda)}>
        <option value="PEN">PEN</option><option value="USD">USD</option>
      </select></label>
      <button type="button" onClick={() => { setDesde(actual.desde); setHasta(actual.hasta); setFiltrado(false); }}>Restablecer meses</button>
    </div>
    <div className="tarjetas" style={{ display: "flex", flexWrap: "wrap", gap: "1rem", minWidth: 0 }}>
      {filtrado ? <div className="tarjeta" style={{ boxSizing: "border-box", minWidth: "min(100%, 260px)", width: "fit-content", maxWidth: "100%", flex: "0 1 auto" }}><strong>Rango seleccionado</strong><span className="cifra" style={{ display: "block", fontSize: "clamp(1rem, 2.2vw, 1.65rem)", whiteSpace: "normal", overflowWrap: "anywhere", lineHeight: 1.25, maxWidth: "100%" }}>{formatearMonto(moneda, resumen.datos?.total ?? "0")}</span></div> : <>
        <div className="tarjeta" style={{ boxSizing: "border-box", minWidth: "min(100%, 260px)", width: "fit-content", maxWidth: "100%", flex: "0 1 auto" }}><strong>Mes actual</strong><span className="cifra" style={{ display: "block", fontSize: "clamp(1rem, 2.2vw, 1.65rem)", whiteSpace: "normal", overflowWrap: "anywhere", lineHeight: 1.25, maxWidth: "100%" }}>{formatearMonto(moneda, actualGlobal.datos?.total ?? "0")}</span></div>
        <div className="tarjeta" style={{ boxSizing: "border-box", minWidth: "min(100%, 260px)", width: "fit-content", maxWidth: "100%", flex: "0 1 auto" }}><strong>Mes anterior</strong><span className="cifra" style={{ display: "block", fontSize: "clamp(1rem, 2.2vw, 1.65rem)", whiteSpace: "normal", overflowWrap: "anywhere", lineHeight: 1.25, maxWidth: "100%" }}>{formatearMonto(moneda, anteriorGlobal.datos?.total ?? "0")}</span></div>
      </>}
    </div>
    {resumen.error && <p className="error">{resumen.error}</p>}
    <div className="tabla-responsive"><table><thead><tr>
      <th>{grupo === "CLIENTE" ? "Cliente receptor" : "Responsable"}</th><th>Registros</th><th className="num">Producción del periodo</th>
    </tr></thead><tbody>{(resumen.datos?.filas ?? []).map(f => <tr key={f.id}>
      <td>{f.codigo} · {f.nombre}</td><td>{f.registros}</td><td className="num">{formatearMonto(moneda, f.monto)}</td>
    </tr>)}</tbody></table></div>
  </section>;
}
