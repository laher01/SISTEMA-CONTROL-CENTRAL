import { useState, type CSSProperties } from "react";

import { useDatos } from "../api";
import { formatearMonto } from "../formato";

type Fila = {
  empresa_id: string; ruc: string; razon_social: string; moneda: "PEN" | "USD";
  expedientes: number; total: string;
};
type Resumen = { proveedores: Fila[]; clientes: Fila[] };
type DocumentoDetalle = { id: string; expediente_id: string | null; nombre_original: string; tipo_documento: string | null; estado: string; fecha_emision: string | null; serie: string | null; correlativo: string | null; moneda: string | null; importe_total: string | null }; 
type UsuarioEquipo = { id: string; codigo: string; nombre: string };
type GestorEquipo = { id: string; usuario_id: string; codigo: string; nombre: string };

export default function ResumenEmpresas({ esResponsable = false }: { esResponsable?: boolean }) {
  const [pestana, setPestana] = useState<"proveedores" | "clientes">("proveedores");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [mes, setMes] = useState("");
  const [moneda, setMoneda] = useState("");
  const [buscar, setBuscar] = useState("");
  const [usuario, setUsuario] = useState("");
  const [gestor, setGestor] = useState("");
  const [empresaDetalle, setEmpresaDetalle] = useState<{ ruc: string; nombre: string; pestana: "proveedores" | "clientes" } | null>(null);
  const { datos: usuarios } = useDatos<UsuarioEquipo[]>(esResponsable ? "/api/v1/miembros/mis-usuarios" : null);
  const { datos: gestores } = useDatos<GestorEquipo[]>(esResponsable ? "/api/v1/gestores" : null);
  const gestoresDelUsuario = (gestores ?? []).filter((g) => !usuario || g.usuario_id === usuario);
  const params = new URLSearchParams();
  if (desde) params.set("fecha_desde", desde);
  if (hasta) params.set("fecha_hasta", hasta);
  if (moneda) params.set("moneda", moneda);
  if (esResponsable && usuario) params.set("usuario_id", usuario);
  if (esResponsable && gestor) params.set("gestor_id", gestor);
  const url = "/api/v1/expedientes/resumen-empresas" + (params.size ? "?" + params.toString() : "");
  const { datos, error, cargando } = useDatos<Resumen>(url);
  const detalleParams = new URLSearchParams();
  if (empresaDetalle) detalleParams.set(empresaDetalle.pestana === "proveedores" ? "emisor_ruc" : "receptor_ruc", empresaDetalle.ruc);
  if (usuario) detalleParams.set("usuario_id", usuario);
  if (gestor) detalleParams.set("gestor_id", gestor);
  if (desde) detalleParams.set("fecha_desde", desde);
  if (hasta) detalleParams.set("fecha_hasta", hasta);
  detalleParams.set("limit", "100");
  const { datos: documentosDetalle, error: errorDetalle, cargando: cargandoDetalle } = useDatos<DocumentoDetalle[]>(
    esResponsable && empresaDetalle ? "/api/v1/documentos?" + detalleParams.toString() : null,
  );
  const filas = (datos?.[pestana] ?? []).filter((fila) =>
    (fila.ruc + " " + fila.razon_social).toLocaleLowerCase("es").includes(buscar.trim().toLocaleLowerCase("es")),
  );
  const empresasDistintas = new Set(filas.map((fila) => fila.empresa_id)).size;
  const expedientes = filas.reduce((total, fila) => total + fila.expedientes, 0);
  const periodo = mes || (desde || hasta ? (desde || "Inicio") + " → " + (hasta || "Hoy") : "Todo el historial");
  const resumenPorMoneda = filas.reduce<Record<string, { total: number; cantidad: number }>>((a, f) => {
    const previo = a[f.moneda] ?? { total: 0, cantidad: 0 };
    a[f.moneda] = { total: previo.total + Number(f.total), cantidad: previo.cantidad + f.expedientes };
    return a;
  }, {});
  const tarjeta: CSSProperties = { border: "1px solid #cbd5e1", borderRadius: 12, padding: 16, minWidth: 0 };
  return <section className="panel-configuracion" style={{ width: "100%", maxWidth: "none" }}>
    <h2>Resumen de empresas</h2>
    <p>Acumulados según los expedientes visibles para tu usuario y sus permisos.</p>
    <div className="acciones" role="tablist" aria-label="Empresas por función">
      <button type="button" role="tab" aria-selected={pestana === "proveedores"}
        onClick={() => { setPestana("proveedores"); setEmpresaDetalle(null); }}>Proveedores</button>
      <button type="button" role="tab" aria-selected={pestana === "clientes"}
        onClick={() => { setPestana("clientes"); setEmpresaDetalle(null); }}>Clientes</button>
    </div>
    {esResponsable && <div className="filtros">
      <label>Usuario de mi equipo
        <select value={usuario} onChange={(e) => { setUsuario(e.target.value); setGestor(""); }}>
          <option value="">Todos mis Usuarios</option>
          {(usuarios ?? []).map((u) => <option key={u.id} value={u.id}>{u.codigo} — {u.nombre}</option>)}
        </select>
      </label>
      <label>Gestor del Usuario
        <select value={gestor} onChange={(e) => setGestor(e.target.value)}>
          <option value="">Todos los Gestores</option>
          {gestoresDelUsuario.map((g) => <option key={g.id} value={g.id}>{g.codigo} — {g.nombre}</option>)}
        </select>
      </label>
    </div>}
    <div className="filtros">
      <label>Buscar RUC o razón social
        <input type="search" aria-label="Buscar empresa por RUC o razón social" value={buscar}
          placeholder="RUC o empresa" onChange={(e) => setBuscar(e.target.value)} />
      </label>
      <label>Mes
        <input type="month" value={mes} onChange={(e) => {
          const m = e.target.value;
          setMes(m);
          if (!m) { setDesde(""); setHasta(""); return; }
          const [anio = 2000, numero = 1] = m.split("-").map(Number);
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
      <button type="button" onClick={() => { setMes(""); setDesde(""); setHasta(""); setMoneda(""); setBuscar(""); setUsuario(""); setGestor(""); }}>
        Limpiar filtros
      </button>
    </div>
    {cargando && <p>Cargando resumen…</p>}
    {error && <p role="alert">{error}</p>}
    <div aria-label="Indicadores de resumen" style={{
      display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
      gap: 12, margin: "16px 0",
    }}>
      <div style={tarjeta}><small>Empresas</small><h3>{empresasDistintas}</h3></div>
      <div style={tarjeta}><small>Expedientes</small><h3>{expedientes}</h3></div>
      <div style={tarjeta}><small>Total facturado</small>
        {Object.entries(resumenPorMoneda).length ? Object.entries(resumenPorMoneda).map(([divisa, valor]) =>
          <h3 key={divisa}>{formatearMonto(divisa === "USD" ? "USD" : "PEN", valor.total)}</h3>
        ) : <h3>Sin registros</h3>}
      </div>
      <div style={tarjeta}><small>Periodo</small><h3>{periodo}</h3></div>
    </div>
    <p>Los indicadores responden a los filtros de búsqueda; las monedas no se mezclan.</p>
    <div className="tabla-responsive" style={{ width: "100%", overflowX: "auto" }}><table style={{ width: "100%", minWidth: 660 }}>
      <thead><tr><th>RUC</th><th>Empresa</th><th>Moneda</th><th>Expedientes</th><th>Total acumulado</th>{esResponsable && <th>Detalle</th>}</tr></thead>
      <tbody>{filas.map((f) => <tr key={f.empresa_id + "-" + f.moneda}>
        <td>{f.ruc}</td><td>{f.razon_social}</td><td>{f.moneda}</td>
        <td>{f.expedientes}</td><td>{formatearMonto(f.moneda, Number(f.total))}</td>
        {esResponsable && <td><button type="button" onClick={() => setEmpresaDetalle({ ruc: f.ruc, nombre: f.razon_social, pestana })}>Ver documentos</button></td>}
      </tr>)}{!filas.length && <tr><td colSpan={esResponsable ? 6 : 5}>No hay empresas para los filtros seleccionados.</td></tr>}</tbody>
    </table></div>
    {esResponsable && empresaDetalle && <div className="tabla-responsive" aria-label="Detalle de documentos" style={{ marginTop: 20, overflowX: "auto" }}>
      <h3>Documentos de {empresaDetalle.nombre}</h3>
      <p>Se muestran hasta 100 documentos autorizados. Las fechas del detalle corresponden al registro del documento; el resumen utiliza la fecha de emisión del expediente.</p>
      <button type="button" onClick={() => setEmpresaDetalle(null)}>Cerrar detalle</button>
      {cargandoDetalle && <p>Cargando documentos…</p>}
      {errorDetalle && <p role="alert">{errorDetalle}</p>}
      <table style={{ width: "100%", minWidth: 660 }}>
        <thead><tr><th>Archivo</th><th>Tipo</th><th>Estado</th><th>Fecha emisión</th><th>Comprobante</th></tr></thead>
        <tbody>{(documentosDetalle ?? []).map((d) => <tr key={d.id}>
          <td>{d.nombre_original}</td><td>{d.tipo_documento ?? "—"}</td><td>{d.estado}</td>
          <td>{d.fecha_emision ?? "—"}</td><td>{d.expediente_id ? <a href={`/expedientes/${encodeURIComponent(d.expediente_id)}`} target="_blank" rel="noopener noreferrer" title="Abrir expediente en otra pestaña">{[d.serie, d.correlativo].filter(Boolean).join("-") || "Ver expediente"}</a> : ([d.serie, d.correlativo].filter(Boolean).join("-") || "Sin expediente")}</td>
        </tr>)}{!cargandoDetalle && !documentosDetalle?.length && <tr><td colSpan={5}>Sin documentos para los filtros seleccionados.</td></tr>}</tbody>
      </table>
    </div>}
  </section>;
}
