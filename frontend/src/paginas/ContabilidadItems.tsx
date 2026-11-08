import { useState } from "react";
import { conParametros, useDatos } from "../api";

type FacturaItem = { expediente_id: string; documento_id: string; comprobante: string; fecha_emision: string; moneda: string; descripcion_original: string; cantidad: string; unidad: string; importe: string; };

type FilaItem = {
  producto_id: string;
  categoria: string;
  descripcion: string;
  unidad: string;
  cantidad: string;
  moneda: string;
  importe: string;
};

type Conciliacion = {
  moneda: string;
  total_documentos: number;
  importe_total: string;
  aprobados: number;
  importe_aprobado: string;
  observados: number;
  importe_observado: string;
  otros: number;
  importe_otros: string;
};

export default function ContabilidadItems() {
  const [buscar, setBuscar] = useState("");
  const [categoria, setCategoria] = useState("");
  const [productoSeleccionado, setProductoSeleccionado] = useState<string | null>(null);
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [emisorId, setEmisorId] = useState("");
  const [receptorId, setReceptorId] = useState("");
  const [errorFiltros, setErrorFiltros] = useState("");
  const [errorDescarga, setErrorDescarga] = useState("");
  const [descargando, setDescargando] = useState(false);
  const [filtros, setFiltros] = useState({ desde: "", hasta: "", emisor_id: "", receptor_id: "", buscar: "", categoria: "" });
  const ruta = conParametros("/api/v1/contabilidad-items", {
    desde: filtros.desde,
    hasta: filtros.hasta,
    emisor_id: filtros.emisor_id,
    receptor_id: filtros.receptor_id,
    buscar: filtros.buscar,
    categoria: filtros.categoria,
  });
  const { datos, error, cargando, recargar } = useDatos<FilaItem[]>(ruta);
  const rutaFacturas = productoSeleccionado ? conParametros(`/api/v1/contabilidad-items/productos/${productoSeleccionado}/facturas`, { desde: filtros.desde, hasta: filtros.hasta, emisor_id: filtros.emisor_id, receptor_id: filtros.receptor_id }) : null;
  const { datos: facturas, error: errorFacturas, cargando: cargandoFacturas } = useDatos<FacturaItem[]>(rutaFacturas);
  const conciliacion = useDatos<Conciliacion[]>(conParametros("/api/v1/contabilidad-items/conciliacion", filtros));

  return (
    <section aria-label="Contabilidad de ítems">
      <h2>Contabilidad de Ítems</h2>
      <p>
        Resumen operativo de las líneas confirmadas de comprobantes. Las cantidades
        no se convierten automáticamente entre unidades distintas.
      </p>
      <form onSubmit={(evento) => {
        evento.preventDefault();
        const uuidValido = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
        if ([emisorId, receptorId].some((id) => id.trim() !== "" && !uuidValido.test(id.trim()))) {
          setErrorFiltros("Los identificadores de emisor y receptor deben tener formato UUID.");
          return;
        }
        setErrorFiltros("");
        setProductoSeleccionado(null);
        setFiltros({ desde, hasta, emisor_id: emisorId.trim(), receptor_id: receptorId.trim(), buscar: buscar.trim(), categoria: categoria.trim() });
        recargar();
      }}>
        <label htmlFor="items-buscar">Buscar producto o servicio</label>
        <input id="items-buscar" value={buscar} onChange={(e) => setBuscar(e.target.value)} placeholder="Descripción original o nombre del producto" />
        <label htmlFor="items-categoria">Categoría</label>
        <input id="items-categoria" value={categoria} onChange={(e) => setCategoria(e.target.value)} placeholder="Categoría exacta (opcional)" />
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
      {errorFiltros && <p role="alert">{errorFiltros}</p>}
      <p>
        <button type="button" disabled={descargando} onClick={async () => {
          setDescargando(true);
          setErrorDescarga("");
          try {
            const rutaCsv = conParametros("/api/v1/contabilidad-items/exportar-csv", filtros);
            const respuesta = await fetch((import.meta.env.VITE_API_URL ?? "") + rutaCsv, {
              credentials: "include",
            });
            if (!respuesta.ok) {
              throw new Error(`No se pudo exportar CSV (HTTP ${respuesta.status}).`);
            }
            const blob = await respuesta.blob();
            const enlace = document.createElement("a");
            const url = URL.createObjectURL(blob);
            enlace.href = url;
            enlace.download = "contabilidad-items.csv";
            document.body.appendChild(enlace);
            try {
              enlace.click();
            } finally {
              enlace.remove();
              window.setTimeout(() => URL.revokeObjectURL(url), 60000);
            }
          } catch (fallo) {
            setErrorDescarga(fallo instanceof Error ? fallo.message : String(fallo));
          } finally {
            setDescargando(false);
          }
        }}>
          {descargando ? "Exportando…" : "Exportar CSV de los filtros aplicados (máximo 500 grupos)"}
        </button>
      </p>
      {errorDescarga && <p role="alert">{errorDescarga}</p>}
      <h3>Conciliación de comprobantes por moneda</h3>
      <p>Importe total = aprobado + observado + otros estados internos. Los valores corresponden a comprobantes, no a la suma de líneas de productos.</p>
      {conciliacion.error && <p role="alert">No se pudo conciliar: {conciliacion.error}</p>}
      {conciliacion.cargando && <p>Calculando conciliación…</p>}
      {conciliacion.datos && <div style={{ overflowX: "auto" }}>
        <table>
          <thead><tr><th>Moneda</th><th>Total comprobantes</th><th>Importe total</th><th>Aprobados</th><th>Importe aprobado</th><th>Observados</th><th>Importe observado</th><th>Otros estados</th><th>Importe otros</th></tr></thead>
          <tbody>{conciliacion.datos.map((fila) => <tr key={fila.moneda}>
            <td>{fila.moneda}</td><td>{fila.total_documentos}</td><td>{fila.importe_total}</td>
            <td>{fila.aprobados}</td><td>{fila.importe_aprobado}</td>
            <td>{fila.observados}</td><td>{fila.importe_observado}</td>
            <td>{fila.otros}</td><td>{fila.importe_otros}</td>
          </tr>)}</tbody>
        </table>
      </div>}
      {cargando && <p>Consultando ítems…</p>}
      {error && <p role="alert">No se pudo consultar: {error}</p>}
      {!cargando && !error && datos?.length === 0 && (
        <div role="status">
          <p>No hay líneas de productos visibles con los filtros y permisos actuales.</p>
          {conciliacion.datos?.some((fila) => Number(fila.total_documentos) > 0) && (
            <p>Existen comprobantes en la conciliación, pero eso no confirma que sus líneas se hayan extraído. Revise la disponibilidad de XML/UBL, la extracción, la clasificación y el alcance autorizado antes de interpretar el resultado como cero productos.</p>
          )}
          {(filtros.buscar || filtros.categoria || filtros.desde || filtros.hasta || filtros.emisor_id || filtros.receptor_id) && (
            <p>Los filtros aplicados también pueden excluir productos existentes.</p>
          )}
        </div>
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
                <th scope="col">Facturas</th>
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
                  <td><button type="button" onClick={() => setProductoSeleccionado(fila.producto_id)}>Ver facturas</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {productoSeleccionado && (
        <section aria-label="Facturas vinculadas al ítem">
          <h3>Facturas que contienen el producto seleccionado</h3>
          <button type="button" onClick={() => setProductoSeleccionado(null)}>Cerrar detalle</button>
          {cargandoFacturas && <p>Consultando facturas…</p>}
          {errorFacturas && <p role="alert">{errorFacturas}</p>}
          {facturas?.length === 0 && <p>No hay facturas visibles para los filtros aplicados.</p>}
          {facturas && facturas.length > 0 && <div style={{ overflowX: "auto" }}>
            <table>
              <thead><tr><th>Factura</th><th>Fecha</th><th>Descripción original</th><th>Cantidad</th><th>Importe</th><th>Expediente</th></tr></thead>
              <tbody>{facturas.map((factura) => (
                <tr key={factura.documento_id + ":" + factura.comprobante + ":" + factura.descripcion_original}>
                  <td>{factura.comprobante}</td><td>{factura.fecha_emision}</td><td>{factura.descripcion_original}</td>
                  <td>{factura.cantidad} {factura.unidad}</td><td>{factura.importe} {factura.moneda}</td>
                  <td><a href={`/expedientes/${factura.expediente_id}`}>Abrir expediente</a></td>
                </tr>
              ))}</tbody>
            </table>
          </div>}
        </section>
      )}
    </section>
  );
}
