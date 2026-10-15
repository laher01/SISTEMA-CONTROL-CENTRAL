import { useState } from "react";
import { conParametros, useDatos } from "../api";

type FilaItem = {
  producto_id: string;
  categoria: string;
  descripcion: string;
  unidad: string;
  cantidad: string;
  moneda: string;
  importe: string;
};

export default function ContabilidadItems() {
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [emisorId, setEmisorId] = useState("");
  const [receptorId, setReceptorId] = useState("");
  const [filtros, setFiltros] = useState({ desde: "", hasta: "", emisor_id: "", receptor_id: "" });
  const ruta = conParametros("/api/v1/contabilidad-items", {
    desde: filtros.desde,
    hasta: filtros.hasta,
    emisor_id: filtros.emisor_id,
    receptor_id: filtros.receptor_id,
  });
  const { datos, error, cargando, recargar } = useDatos<FilaItem[]>(ruta);

  return (
    <section aria-label="Contabilidad de ítems">
      <h2>Contabilidad de Ítems</h2>
      <p>
        Resumen operativo de las líneas confirmadas de comprobantes. Las cantidades
        no se convierten automáticamente entre unidades distintas.
      </p>
      <form onSubmit={(evento) => {
        evento.preventDefault();
        setFiltros({ desde, hasta, emisor_id: emisorId.trim(), receptor_id: receptorId.trim() });
        recargar();
      }}>
        <label htmlFor="items-desde">Desde</label>
        <input id="items-desde" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
        <label htmlFor="items-hasta">Hasta</label>
        <input id="items-hasta" type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
        <label htmlFor="items-emisor">ID del emisor (opcional)</label>
        <input id="items-emisor" type="text" placeholder="UUID de empresa emisora" value={emisorId} onChange={(e) => setEmisorId(e.target.value)} />
        <label htmlFor="items-receptor">ID del receptor (opcional)</label>
        <input id="items-receptor" type="text" placeholder="UUID de empresa receptora" value={receptorId} onChange={(e) => setReceptorId(e.target.value)} />
        <button type="submit">Consultar</button>
      </form>
      <p><a href={conParametros("/api/v1/contabilidad-items/exportar-csv", filtros)}>Exportar CSV de los filtros aplicados (máximo 500 grupos)</a></p>
      {cargando && <p>Consultando ítems…</p>}
      {error && <p role="alert">No se pudo consultar: {error}</p>}
      {!cargando && !error && datos?.length === 0 && (
        <p>No se encontraron líneas de comprobantes para el período seleccionado.</p>
      )}
      {datos && datos.length > 0 && (
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th scope="col">Categoría</th>
                <th scope="col">Producto</th>
                <th scope="col">Unidad</th>
                <th scope="col">Cantidad acumulada</th>
                <th scope="col">Moneda</th>
                <th scope="col">Importe de líneas</th>
              </tr>
            </thead>
            <tbody>
              {datos.map((fila) => (
                <tr key={fila.producto_id + ":" + fila.unidad + ":" + fila.moneda}>
                  <td>{fila.categoria}</td>
                  <td>{fila.descripcion}</td>
                  <td>{fila.unidad}</td>
                  <td>{fila.cantidad}</td>
                  <td>{fila.moneda}</td>
                  <td>{fila.importe || "Sin importe"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
