import { useState } from "react";
import { Link } from "react-router-dom";

import { obtener, useDatos } from "../api";
import ConsultaRucSunat from "../componentes/ConsultaRucSunat";
import ConfiguracionApiEmpresas from "../componentes/ConfiguracionApiEmpresas";
import type { Empresa } from "../tipos";

type Tipo = "coactiva" | "ssco";
type Coincidencia = { razon_social: string; resolucion: string; firme: string; publicacion: string };
type Consulta = {
  razon_social?: string;
  estado: string;
  monto?: string;
  registros?: number;
  corte?: string;
  fuente?: string;
  desactualizado?: boolean;
  coincidencias?: Coincidencia[];
};
type Fila = Consulta & {
  ruc: string; razon: string; estadoSsco: string; domicilio: string; rutas: string;
};
type Columna = { clave: string; titulo: string; valor: (fila: Fila) => string | number };

const comunes: Columna[] = [
  { clave: "ruc", titulo: "RUC", valor: f => f.ruc },
  { clave: "razon", titulo: "Razón social", valor: f => f.razon },
];
const columnas: Columna[] = [
  ...comunes,
  { clave: "ruta", titulo: "Ruta", valor: f => f.rutas },
  { clave: "ssco", titulo: "SSCO", valor: f => f.estadoSsco },
  { clave: "estado", titulo: "Deuda coactiva", valor: f => f.estado },
  { clave: "monto", titulo: "Total deuda (S/)", valor: f => f.monto === undefined ? "" : Number(f.monto) },
  { clave: "registros", titulo: "Registros devueltos", valor: f => f.registros ?? "" },
  { clave: "domicilio", titulo: "Domicilio fiscal", valor: f => f.domicilio },
  { clave: "resolucion", titulo: "Resolución SSCO", valor: f => f.coincidencias?.map(c => c.resolucion).join(" · ") ?? "" },
  { clave: "firme", titulo: "Fecha firme", valor: f => f.coincidencias?.map(c => c.firme).join(" · ") ?? "" },
  { clave: "publicacion", titulo: "Publicación", valor: f => f.coincidencias?.map(c => c.publicacion).join(" · ") ?? "" },
  { clave: "corte", titulo: "Corte del padrón", valor: f => f.corte ?? "" },
  { clave: "fuente", titulo: "Fuente SSCO", valor: f => f.fuente ?? "" },
];

export default function ConsultasEmpresas({ tipo, puedeConfigurar = false }: { tipo: Tipo; puedeConfigurar?: boolean }) {
  const { datos, error, cargando } = useDatos<Empresa[]>("/api/v1/empresas?autorizada=true");
  const empresas = datos ?? [];
  const proveedores = empresas.filter(e => e.tipo_relacion === "PROVEEDOR" || e.tipo_relacion === "AMBOS");
  const [modo, setModo] = useState<"todos" | "proveedor" | "ruc" | "seleccionadas">("todos");
  const [seleccion, setSeleccion] = useState("");
  const [seleccionadas, setSeleccionadas] = useState<Set<string>>(new Set());
  const empresasSeleccionadas = empresas.filter(e => seleccionadas.has(e.id));
  const [ruc, setRuc] = useState("");
  const [filas, setFilas] = useState<Fila[]>([]);
  const [ocupado, setOcupado] = useState(false);
  const [completado, setCompletado] = useState(false);
  const [orden, setOrden] = useState({ clave: "ruc", ascendente: true });

  const ejecutar = async () => {
    const codigoManual = ruc.trim();
    const empresaManual = empresas.find(e => e.ruc === codigoManual);
    const objetivos = modo === "ruc"
      ? [empresaManual ?? { ruc: codigoManual, razon_social: "", rutas: [] }]
      : modo === "proveedor" ? proveedores.filter(p => p.ruc === seleccion)
        : modo === "seleccionadas" ? empresasSeleccionadas : proveedores;
    setOcupado(true);
    setCompletado(false);
    setFilas([]);
    try {
      for (let i = 0; i < objetivos.length; i += 2) {
        const bloque = await Promise.all(objetivos.slice(i, i + 2).map(async empresa => {
          const base = { ruc: empresa.ruc, razon: empresa.razon_social, rutas: (empresa.rutas ?? []).join(" · ") };
          const ruta = "/api/v1/empresas/consultas";
          const codigo = encodeURIComponent(empresa.ruc);
          const [deuda, ssco, domicilio] = await Promise.allSettled([
            obtener<Consulta>(`${ruta}/coactiva/${codigo}${modo === "ruc" && !base.razon ? "?buscar_razon=true" : ""}`),
            obtener<Consulta>(`${ruta}/ssco/${codigo}?ssco_apiperu=true`),
            obtener<{ direccion_completa?: string; estado_consulta?: string }>(`${ruta}/domicilio/${codigo}`),
          ]);
          const d = deuda.status === "fulfilled" ? deuda.value : { estado: "Consulta no disponible" };
          const s = ssco.status === "fulfilled" ? ssco.value : { estado: "Consulta no disponible" };
          return {
            ...base, ...s, ...d, estadoSsco: s.estado,
            razon: s.coincidencias?.[0]?.razon_social ?? d.razon_social ?? base.razon,
            domicilio: domicilio.status === "fulfilled"
              ? domicilio.value.direccion_completa ?? domicilio.value.estado_consulta ?? "Dirección no disponible"
              : "Consulta no disponible",
          };

        }));
        setFilas(anteriores => [...anteriores, ...bloque]);
      }
    } finally {
      setOcupado(false);
      setCompletado(true);
    }
  };

  const col = columnas.find(c => c.clave === orden.clave);
  const resultados = [...filas].sort((a, b) => {
    const av = col?.valor(a) ?? a.ruc, bv = col?.valor(b) ?? b.ruc;
    if (av === "" || bv === "") return Number(av === "") - Number(bv === "");
    const comparar = typeof av === "number" && typeof bv === "number"
      ? av - bv : String(av).localeCompare(String(bv), "es", { numeric: true });
    return orden.ascendente ? comparar : -comparar;
  });
  const puedeConsultar = modo === "ruc" ? /^[0-9]{11}$/.test(ruc.trim())
    : modo === "proveedor" ? Boolean(seleccion)
      : modo === "seleccionadas" ? empresasSeleccionadas.length > 0 : proveedores.length > 0;

  return (
    <section>
      <nav aria-label="Empresas" className="acciones">
        <Link to="/empresas">Empresas</Link>
        <Link to="/empresas/coactiva">Consulta Coactiva</Link>
        <Link to="/empresas/ssco">Consulta SSCO</Link>
      </nav>
      <h2>{tipo === "coactiva" ? "Consulta Coactiva" : "Consulta SSCO"}</h2>
      {tipo === "coactiva" && puedeConfigurar && <ConfiguracionApiEmpresas />}
      <form className="acciones" onSubmit={ev => { ev.preventDefault(); if (!ocupado && puedeConsultar) void ejecutar(); }}>
        <label>Modo de consulta <select value={modo} disabled={ocupado} onChange={ev => setModo(ev.target.value as typeof modo)}>
          <option value="todos">Todos los proveedores activos</option>
          <option value="proveedor">Seleccionar proveedor</option>
          <option value="ruc">Ingresar RUC</option>
          <option value="seleccionadas">Seleccionar empresas a consultar</option>
        </select></label>
        {modo === "proveedor" && <label>Proveedor <select value={seleccion} disabled={ocupado} onChange={ev => setSeleccion(ev.target.value)}>
          <option value="">Seleccione un proveedor</option>
          {proveedores.map(p => <option key={p.ruc} value={p.ruc}>{p.ruc} · {p.razon_social}</option>)}
        </select></label>}
        {modo === "ruc" && <label>RUC <input value={ruc} disabled={ocupado} onChange={ev => setRuc(ev.target.value)} inputMode="numeric" maxLength={11} placeholder="11 dígitos" /></label>}
        {modo === "seleccionadas" && empresas.length > 0 && <fieldset disabled={ocupado}>
          <legend>Empresas a consultar ({empresasSeleccionadas.length})</legend>
          {empresas.map(empresa => <div key={empresa.id}><label>
            <input type="checkbox" checked={seleccionadas.has(empresa.id)} onChange={ev => {
              const marcada = ev.target.checked;
              setSeleccionadas(anterior => {
                const actual = new Set(anterior);
                if (marcada) actual.add(empresa.id);
                else actual.delete(empresa.id);
                return actual;
              });
            }} />
            {empresa.ruc} · {empresa.razon_social}
          </label></div>)}
        </fieldset>}
        <button disabled={ocupado || !puedeConsultar}>Consultar</button>
      </form>
      {modo !== "ruc" && cargando && <p role="status">Cargando proveedores…</p>}
      {modo !== "ruc" && error && <p role="alert">{error}</p>}
      {modo !== "ruc" && !cargando && !error && (modo === "seleccionadas" ? !empresas.length : !proveedores.length) && <p>Sin empresas disponibles para este modo.</p>}
      {(ocupado || completado) && <p role="status">{ocupado ? "Consultando" : "Consulta finalizada"} · {filas.length} resultados</p>}
      {filas.some(f => f.desactualizado) && <p role="alert">No se pudo actualizar SUNAT. Se usó la última copia disponible en el servidor.</p>}
      {filas.length > 0 && <div className="tabla-contenedor"><table>
        <thead><tr>{columnas.map(c => <th key={c.clave} aria-sort={orden.clave === c.clave ? (orden.ascendente ? "ascending" : "descending") : "none"}>
          <button type="button" onClick={() => setOrden(o => ({ clave: c.clave, ascendente: o.clave !== c.clave || !o.ascendente }))}>
            {c.titulo}{orden.clave === c.clave ? (orden.ascendente ? " ↑" : " ↓") : ""}
          </button>
        </th>)}<th>Ficha RUC</th></tr></thead>
        <tbody>{resultados.map(f => <tr key={f.ruc}>{columnas.map(c => {
          const valor = c.valor(f);
          return <td key={c.clave}>{valor === "" ? "—" : c.clave === "monto" ? Number(valor).toLocaleString("es-PE", { minimumFractionDigits: 2 }) : valor}</td>;
        })}<td><ConsultaRucSunat ruc={f.ruc} /></td></tr>)}</tbody>
      </table></div>}
      {tipo === "ssco" && <p><a href="https://www.sunat.gob.pe/padronesnotificaciones/sujeSinCapacidadOperativa.html" target="_blank" rel="noreferrer">Padrón oficial de SUNAT</a></p>}
    </section>
  );
}
