import { useState } from "react";
import { Link } from "react-router-dom";

import { obtener, useDatos } from "../api";
import type { Empresa } from "../tipos";

type Tipo = "coactiva" | "ssco";
type Coincidencia = { razon_social: string; resolucion: string; firme: string; publicacion: string };
type Consulta = {
  razon_social?: string;
  estado: string;
  monto?: string;
  registros?: number;
  corte?: string;
  desactualizado?: boolean;
  coincidencias?: Coincidencia[];
};
type Fila = Consulta & { ruc: string; razon: string };
type Columna = { clave: string; titulo: string; valor: (fila: Fila) => string | number };

const comunes: Columna[] = [
  { clave: "ruc", titulo: "RUC", valor: f => f.ruc },
  { clave: "razon", titulo: "Razón social", valor: f => f.razon },
  { clave: "estado", titulo: "Resultado", valor: f => f.estado },
];
const columnas: Record<Tipo, Columna[]> = {
  coactiva: [
    ...comunes,
    { clave: "monto", titulo: "Total deuda (S/)", valor: f => f.monto === undefined ? "" : Number(f.monto) },
    { clave: "registros", titulo: "Registros devueltos", valor: f => f.registros ?? "" },
  ],
  ssco: [
    ...comunes,
    { clave: "resolucion", titulo: "Resolución", valor: f => f.coincidencias?.map(c => c.resolucion).join(" · ") ?? "" },
    { clave: "firme", titulo: "Fecha firme", valor: f => f.coincidencias?.map(c => c.firme).join(" · ") ?? "" },
    { clave: "publicacion", titulo: "Publicación", valor: f => f.coincidencias?.map(c => c.publicacion).join(" · ") ?? "" },
    { clave: "corte", titulo: "Corte del padrón", valor: f => f.corte ?? "" },
  ],
};

export default function ConsultasEmpresas({ tipo }: { tipo: Tipo }) {
  const { datos, error, cargando } = useDatos<Empresa[]>("/api/v1/empresas?autorizada=true");
  const proveedores = (datos ?? []).filter(e => e.tipo_relacion === "PROVEEDOR" || e.tipo_relacion === "AMBOS");
  const [modo, setModo] = useState<"todos" | "proveedor" | "ruc">("todos");
  const [seleccion, setSeleccion] = useState("");
  const [ruc, setRuc] = useState("");
  const [filas, setFilas] = useState<Fila[]>([]);
  const [ocupado, setOcupado] = useState(false);
  const [completado, setCompletado] = useState(false);
  const [orden, setOrden] = useState({ clave: "ruc", ascendente: true });

  const ejecutar = async () => {
    const objetivos = modo === "ruc"
      ? [{ ruc: ruc.trim(), razon_social: proveedores.find(p => p.ruc === ruc.trim())?.razon_social ?? "" }]
      : modo === "proveedor" ? proveedores.filter(p => p.ruc === seleccion) : proveedores;
    setOcupado(true);
    setCompletado(false);
    setFilas([]);
    try {
      for (let i = 0; i < objetivos.length; i += 4) {
        const bloque = await Promise.all(objetivos.slice(i, i + 4).map(async empresa => {
          const base = { ruc: empresa.ruc, razon: empresa.razon_social };
          try {
            const resultado = await obtener<Consulta>(`/api/v1/empresas/consultas/${tipo}/${encodeURIComponent(empresa.ruc)}${modo === "ruc" && !base.razon ? "?buscar_razon=true" : ""}`);
            return { ...base, ...resultado, razon: resultado.coincidencias?.[0]?.razon_social ?? resultado.razon_social ?? base.razon };
          } catch {
            return { ...base, estado: "Consulta no disponible" };
          }
        }));
        setFilas(anteriores => [...anteriores, ...bloque]);
      }
    } finally {
      setOcupado(false);
      setCompletado(true);
    }
  };

  const col = columnas[tipo].find(c => c.clave === orden.clave);
  const resultados = [...filas].sort((a, b) => {
    const av = col?.valor(a) ?? a.ruc, bv = col?.valor(b) ?? b.ruc;
    if (av === "" || bv === "") return Number(av === "") - Number(bv === "");
    const comparar = typeof av === "number" && typeof bv === "number"
      ? av - bv : String(av).localeCompare(String(bv), "es", { numeric: true });
    return orden.ascendente ? comparar : -comparar;
  });
  const puedeConsultar = modo === "ruc" ? /^[0-9]{11}$/.test(ruc.trim())
    : modo === "proveedor" ? Boolean(seleccion) : proveedores.length > 0;

  return (
    <section>
      <nav aria-label="Empresas" className="acciones">
        <Link to="/empresas">Empresas</Link>
        <Link to="/empresas/coactiva">Consulta Coactiva</Link>
        <Link to="/empresas/ssco">Consulta SSCO</Link>
      </nav>
      <h2>{tipo === "coactiva" ? "Consulta Coactiva" : "Consulta SSCO"}</h2>
      <form className="acciones" onSubmit={ev => { ev.preventDefault(); if (!ocupado && puedeConsultar) void ejecutar(); }}>
        <label>Modo de consulta <select value={modo} disabled={ocupado} onChange={ev => setModo(ev.target.value as typeof modo)}>
          <option value="todos">Todos los proveedores activos</option>
          <option value="proveedor">Seleccionar proveedor</option>
          <option value="ruc">Ingresar RUC</option>
        </select></label>
        {modo === "proveedor" && <label>Proveedor <select value={seleccion} disabled={ocupado} onChange={ev => setSeleccion(ev.target.value)}>
          <option value="">Seleccione un proveedor</option>
          {proveedores.map(p => <option key={p.ruc} value={p.ruc}>{p.ruc} · {p.razon_social}</option>)}
        </select></label>}
        {modo === "ruc" && <label>RUC <input value={ruc} disabled={ocupado} onChange={ev => setRuc(ev.target.value)} inputMode="numeric" maxLength={11} placeholder="11 dígitos" /></label>}
        <button disabled={ocupado || !puedeConsultar}>Consultar</button>
      </form>
      {modo !== "ruc" && cargando && <p role="status">Cargando proveedores…</p>}
      {modo !== "ruc" && error && <p role="alert">{error}</p>}
      {modo !== "ruc" && !cargando && !error && !proveedores.length && <p>Sin proveedores activos en tu ámbito.</p>}
      {(ocupado || completado) && <p role="status">{ocupado ? "Consultando" : "Consulta finalizada"} · {filas.length} resultados</p>}
      {filas.some(f => f.desactualizado) && <p role="alert">No se pudo actualizar SUNAT. Se usó la última copia disponible en el servidor.</p>}
      {filas.length > 0 && <div className="tabla-contenedor"><table>
        <thead><tr>{columnas[tipo].map(c => <th key={c.clave} aria-sort={orden.clave === c.clave ? (orden.ascendente ? "ascending" : "descending") : "none"}>
          <button type="button" onClick={() => setOrden(o => ({ clave: c.clave, ascendente: o.clave !== c.clave || !o.ascendente }))}>
            {c.titulo}{orden.clave === c.clave ? (orden.ascendente ? " ↑" : " ↓") : ""}
          </button>
        </th>)}</tr></thead>
        <tbody>{resultados.map(f => <tr key={f.ruc}>{columnas[tipo].map(c => {
          const valor = c.valor(f);
          return <td key={c.clave}>{valor === "" ? "—" : c.clave === "monto" ? Number(valor).toLocaleString("es-PE", { minimumFractionDigits: 2 }) : valor}</td>;
        })}</tr>)}</tbody>
      </table></div>}
      {tipo === "ssco" && <p><a href="https://www.sunat.gob.pe/padronesnotificaciones/sujeSinCapacidadOperativa.html" target="_blank" rel="noreferrer">Padrón oficial de SUNAT</a></p>}
    </section>
  );
}
