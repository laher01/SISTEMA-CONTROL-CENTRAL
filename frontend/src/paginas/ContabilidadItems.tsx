import { useState } from "react";
import { conParametros, useDatos } from "../api";

type FacturaItem = { expediente_id: string; documento_id: string; comprobante: string; fecha_emision: string; moneda: string; emisor_id: string; receptor_id: string; emisor_ruc: string; emisor_nombre: string; receptor_ruc: string; receptor_nombre: string; descripcion_original: string; cantidad: string; unidad: string; importe: string; };
type VistaFacturas = "general" | "proveedor" | "cliente";

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
  const [vistaFacturas, setVistaFacturas] = useState<VistaFacturas>("general");
  const [offsetFacturas, setOffsetFacturas] = useState(0);
  const limiteFacturas = 100;
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [emisorBuscar, setEmisorBuscar] = useState("");
  const [receptorBuscar, setReceptorBuscar] = useState("");
  const [errorFiltros, setErrorFiltros] = useState("");
  const [errorDescarga, setErrorDescarga] = useState("");
  const [descargando, setDescargando] = useState(false);
  const [filtros, setFiltros] = useState({ desde: "", hasta: "", emisor_buscar: "", receptor_buscar: "", buscar: "", categoria: "" });
  const ruta = conParametros("/api/v1/contabilidad-items", {
    desde: filtros.desde,
    hasta: filtros.hasta,
    emisor_buscar: filtros.emisor_buscar,
    receptor_buscar: filtros.receptor_buscar,
    buscar: filtros.buscar,
    categoria: filtros.categoria,
  });
  const { datos, error, cargando, recargar } = useDatos<FilaItem[]>(ruta);
  const rutaFacturas = productoSeleccionado ? conParametros(`/api/v1/contabilidad-items/productos/${productoSeleccionado}/facturas`, { desde: filtros.desde, hasta: filtros.hasta, emisor_buscar: filtros.emisor_buscar, receptor_buscar: filtros.receptor_buscar, limite: limiteFacturas, offset: offsetFacturas }) : null;
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
        setErrorFiltros("");
        setProductoSeleccionado(null);
        setFiltros({ desde, hasta, emisor_buscar: emisorBuscar.trim(), receptor_buscar: receptorBuscar.trim(), buscar: buscar.trim(), categoria: categoria.trim() });
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
        <label htmlFor="items-emisor">Emisor (opcional)</label>
        <input id="items-emisor" type="search" maxLength={150} placeholder="RUC, razón social o UUID" value={emisorBuscar} onChange={(e) => setEmisorBuscar(e.target.value)} />
        <label htmlFor="items-receptor">Receptor (opcional)</label>
        <input id="items-receptor" type="search" maxLength={150} placeholder="RUC, razón social o UUID" value={receptorBuscar} onChange={(e) => setReceptorBuscar(e.target.value)} />
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
                  <td><button type="button" onClick={() => { setVistaFacturas("general"); setOffsetFacturas(0); setProductoSeleccionado(fila.producto_id); }}>Ver facturas</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {productoSeleccionado && (
        <div
          role="presentation"
          onMouseDown={(evento) => {
            if (evento.target === evento.currentTarget) setProductoSeleccionado(null);
          }}
          style={{ position: "fixed", inset: 0, zIndex: 1000, padding: 16, background: "rgba(15, 23, 42, 0.58)", display: "grid", placeItems: "center" }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="items-modal-titulo"
            style={{ width: "min(1120px, 96vw)", maxHeight: "88vh", overflow: "auto", padding: 20, borderRadius: 12, background: "var(--surface, #fff)", color: "var(--text, #172033)", boxShadow: "0 20px 60px rgba(0,0,0,.3)" }}
          >
            <header style={{ display: "flex", justifyContent: "space-between", alignItems: "start", gap: 16 }}>
              <div>
                <h3 id="items-modal-titulo">Facturas asociadas: {datos?.find((fila) => fila.producto_id === productoSeleccionado)?.descripcion ?? "Ítem"}</h3>
                <p>Consulta el detalle general o agrúpalo por proveedor o cliente.</p>
              </div>
              <button type="button" aria-label="Cerrar facturas del ítem" onClick={() => setProductoSeleccionado(null)}>Cerrar</button>
            </header>
            <div role="tablist" aria-label="Vistas de facturas asociadas" style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
              {([
                ["general", "General"],
                ["proveedor", "Por proveedor"],
                ["cliente", "Por cliente"],
              ] as const).map(([vista, etiqueta]) => (
                <button
                  key={vista}
                  type="button"
                  role="tab"
                  aria-selected={vistaFacturas === vista}
                  onClick={() => setVistaFacturas(vista)}
                >
                  {etiqueta}
                </button>
              ))}
            </div>
            {cargandoFacturas && <p>Consultando facturas…</p>}
            {errorFacturas && <p role="alert">No se pudieron consultar las facturas: {errorFacturas}</p>}
            {!cargandoFacturas && !errorFacturas && facturas?.length === 0 && (
              <p>No hay facturas visibles para este ítem y los filtros aplicados.</p>
            )}
            {facturas && facturas.length > 0 && (
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBlock: 12 }}>
                <span>Facturas {offsetFacturas + 1}–{offsetFacturas + facturas.length}; página de {limiteFacturas} registros.</span>
                <div style={{ display: "flex", gap: 8 }}>
                  <button type="button" disabled={offsetFacturas === 0 || cargandoFacturas} onClick={() => setOffsetFacturas(Math.max(0, offsetFacturas - limiteFacturas))}>Anterior</button>
                  <button type="button" disabled={facturas.length < limiteFacturas || cargandoFacturas} onClick={() => setOffsetFacturas(offsetFacturas + limiteFacturas)}>Siguiente</button>
                </div>
              </div>
            )}
            {facturas && facturas.length > 0 && (() => {
              const tabla = (filas: FacturaItem[]) => (
                <div style={{ overflowX: "auto" }}>
                  <table>
                    <thead><tr><th>Factura</th><th>Fecha</th><th>Proveedor (emisor)</th><th>Cliente (receptor)</th><th>Descripción original</th><th>Cantidad</th><th>Importe</th><th>Expediente</th></tr></thead>
                    <tbody>{filas.map((factura) => (
                      <tr key={factura.documento_id + ":" + factura.comprobante + ":" + factura.descripcion_original}>
                        <td>{factura.comprobante}</td>
                        <td>{factura.fecha_emision}</td>
                        <td>{factura.emisor_nombre || factura.emisor_ruc || "Sin identificar"}</td>
                        <td>{factura.receptor_nombre || factura.receptor_ruc || "Sin identificar"}</td>
                        <td>{factura.descripcion_original}</td>
                        <td>{factura.cantidad} {factura.unidad}</td>
                        <td>{factura.importe} {factura.moneda}</td>
                        <td><a href={`/expedientes/${factura.expediente_id}`}>Abrir expediente</a></td>
                      </tr>
                    ))}</tbody>
                  </table>
                </div>
              );
              if (vistaFacturas === "general") return tabla(facturas);
              const grupos = new Map<string, FacturaItem[]>();
              for (const factura of facturas) {
                const esProveedor = vistaFacturas === "proveedor";
                const idEmpresa = esProveedor ? factura.emisor_id : factura.receptor_id;
                const nombre = esProveedor
                  ? factura.emisor_nombre || factura.emisor_ruc || "Proveedor sin identificar"
                  : factura.receptor_nombre || factura.receptor_ruc || "Cliente sin identificar";
                const clave = idEmpresa || nombre;
                grupos.set(clave, [...(grupos.get(clave) ?? []), factura]);
              }
              return Array.from(grupos.entries()).map(([idEmpresa, filas]) => {
                const primera = filas[0];
                const nombre = vistaFacturas === "proveedor"
                  ? primera.emisor_nombre || primera.emisor_ruc || "Proveedor sin identificar"
                  : primera.receptor_nombre || primera.receptor_ruc || "Cliente sin identificar";
                return (
                  <section key={idEmpresa} aria-label={nombre} style={{ marginBlock: 16 }}>
                    <h4>{nombre} · {filas.length} líneas</h4>
                    {tabla(filas)}
                  </section>
                );
              });
            })()}
          </section>
        </div>
      )}
    </section>
  );
}
