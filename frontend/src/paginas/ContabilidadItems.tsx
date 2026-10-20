import { useState } from "react";
import { conParametros, useDatos } from "../api";

type DetalleExpediente = { expediente_id: string; moneda: string; estado_auditoria: string; lineas: { documento_id: string; numero_linea: number; categoria: string; descripcion: string; unidad: string; cantidad: string; importe: string }[] };
type EmpresaVinculada = { id: string; ruc: string; razon_social: string };
type VistaItems = "dashboard" | "items" | "proveedor" | "cliente";

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
  const [vista, setVista] = useState<VistaItems>("dashboard");
  const [categoriaEditable, setCategoriaEditable] = useState<Record<string, string>>({});
  const [mensajeCategoria, setMensajeCategoria] = useState("");
  const [expedienteSeleccionado, setExpedienteSeleccionado] = useState<string | null>(null);
  const [empresaSeleccionada, setEmpresaSeleccionada] = useState<EmpresaVinculada | null>(null);
  const [buscarEmpresa, setBuscarEmpresa] = useState("");
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
  const { datos: detalle, cargando: cargandoDetalle, error: errorDetalle } = useDatos<DetalleExpediente>(expedienteSeleccionado ? `/api/v1/contabilidad-items/expedientes/${expedienteSeleccionado}/detalle` : null);
  const rutaEmpresas = vista === "proveedor" || vista === "cliente"
    ? conParametros("/api/v1/contabilidad-items/empresas-vinculadas", {
        tipo: vista, buscar: buscarEmpresa,
      })
    : null;
  const { datos: empresas, cargando: cargandoEmpresas, error: errorEmpresas } = useDatos<EmpresaVinculada[]>(rutaEmpresas);
  const filasVisibles = vista === "proveedor" || vista === "cliente" ? (empresaSeleccionada ? datos : null) : datos;
  const cambiarVista = (siguiente: VistaItems) => {
    setVista(siguiente);
    setEmpresaSeleccionada(null);
    setProductoSeleccionado(null);
    setExpedienteSeleccionado(null);
    setBuscarEmpresa("");
    setEmisorId("");
    setReceptorId("");
    setFiltros((actual) => ({ ...actual, emisor_id: "", receptor_id: "" }));
  };
  const seleccionarEmpresa = (empresa: EmpresaVinculada) => {
    setEmpresaSeleccionada(empresa);
    setProductoSeleccionado(null);
    setExpedienteSeleccionado(null);
    setFiltros((actual) => ({
      ...actual,
      emisor_id: vista === "proveedor" ? empresa.id : "",
      receptor_id: vista === "cliente" ? empresa.id : "",
    }));
  };

  return (
    <section aria-label="Contabilidad de ítems">
      <h2>Contabilidad de Ítems</h2>
      <p>
        Resumen operativo de las líneas confirmadas de comprobantes. Las cantidades
        no se convierten automáticamente entre unidades distintas.
      </p>
      <nav aria-label="Vistas de Contabilidad de Ítems">
        {(["dashboard", "items", "proveedor", "cliente"] as const).map((opcion) => (
          <button key={opcion} type="button" aria-current={vista === opcion ? "page" : undefined}
            onClick={() => cambiarVista(opcion)}>
            {{ dashboard: "Dashboard", items: "Por ítem", proveedor: "Por proveedor", cliente: "Por cliente" }[opcion]}
          </button>
        ))}
      </nav>
      {vista === "dashboard" && (
        <section aria-label="Resumen documental informativo">
          <h3>Indicadores de comprobantes registrados</h3>
          <p>La conciliación refleja comprobantes, no cobertura de extracción de líneas.</p>
          {conciliacion.cargando && <p>Cargando indicadores…</p>}
          {conciliacion.error && <p role="alert">{conciliacion.error}</p>}
          {conciliacion.datos?.map((dato) => (
            <p key={dato.moneda}>{dato.moneda}: {dato.total_documentos} comprobantes, {dato.aprobados} aprobados, {dato.observados} observados y {dato.otros} en otros estados.</p>
          ))}
          <p>Productos visibles en esta consulta: {datos?.length ?? "consultando"}. Este valor no equivale al total histórico de líneas procesadas.</p>
          <p>El diagnóstico de facturas pendientes de extracción se desarrolla por separado (Issue #365).</p>
        </section>
      )}
      {(vista === "proveedor" || vista === "cliente") && (
        <section aria-label="Selección de empresa vinculada">
          <h3>{vista === "proveedor" ? "Proveedores con ítems documentados" : "Clientes con ítems documentados"}</h3>
          <label htmlFor="items-buscar-empresa">Buscar por RUC o razón social</label>
          <input id="items-buscar-empresa" value={buscarEmpresa} onChange={(e) => setBuscarEmpresa(e.target.value)} />
          {cargandoEmpresas && <p>Consultando empresas…</p>}
          {errorEmpresas && <p role="alert">{errorEmpresas}</p>}
          {empresas && empresas.length === 0 && <p>No se encontraron empresas con ítems visibles en su ámbito autorizado.</p>}
          {empresas?.map((empresa) => (
            <p key={empresa.id}><button type="button" onClick={() => seleccionarEmpresa(empresa)}>
              {empresa.razon_social} — {empresa.ruc}
            </button></p>
          ))}
          {empresaSeleccionada && <p>Mostrando productos de: <strong>{empresaSeleccionada.razon_social}</strong> ({empresaSeleccionada.ruc}).</p>}
        </section>
      )}
      {vista !== "dashboard" && <>
      <form onSubmit={(evento) => {
        evento.preventDefault();
        const uuidValido = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
        if ([emisorId, receptorId].some((id) => id.trim() !== "" && !uuidValido.test(id.trim()))) {
          setErrorFiltros("Los identificadores de emisor y receptor deben tener formato UUID.");
          return;
        }
        setErrorFiltros("");
        setProductoSeleccionado(null);
        setFiltros({ desde, hasta, emisor_id: vista === "proveedor" ? (empresaSeleccionada?.id ?? "") : emisorId.trim(), receptor_id: vista === "cliente" ? (empresaSeleccionada?.id ?? "") : receptorId.trim(), buscar: buscar.trim(), categoria: categoria.trim() });
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
      {vista === "items" && <><h3>Conciliación de comprobantes por moneda</h3>
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
      </>}
      {mensajeCategoria && <p role="status">{mensajeCategoria}</p>}
      {cargando && <p>Consultando ítems…</p>}
      {error && <p role="alert">No se pudo consultar: {error}</p>}
      {!cargando && !error && filasVisibles?.length === 0 && (
        <p>No se encontraron líneas de comprobantes para el período seleccionado.</p>
      )}
      {filasVisibles && filasVisibles.length > 0 && (
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th scope="col">N.º</th>
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
              {filasVisibles.map((fila, indice) => (
                <tr key={fila.producto_id + ":" + fila.unidad + ":" + fila.moneda}>
                  <td>{indice + 1}</td>
                  <td>{fila.categoria}{vista === "items" && (
                    <details>
                      <summary>Clasificar</summary>
                      <label>Asignar categoría
                        <input aria-label={"Categoría de " + fila.descripcion} value={categoriaEditable[fila.producto_id] ?? fila.categoria} onChange={(e) => setCategoriaEditable((anterior) => ({ ...anterior, [fila.producto_id]: e.target.value }))} />
                      </label>
                      <button type="button" onClick={async () => {
                        const categoriaNueva = (categoriaEditable[fila.producto_id] ?? fila.categoria).trim();
                        if (categoriaNueva.length < 2) { setMensajeCategoria("Indique una categoría válida."); return; }
                        try {
                          const respuesta = await fetch((import.meta.env.VITE_API_URL ?? "") + "/api/v1/contabilidad-items/productos/" + fila.producto_id + "/categoria", {
                            method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ categoria: categoriaNueva }),
                          });
                          if (!respuesta.ok) { throw new Error(respuesta.status === 403 ? "Solo Administración puede clasificar productos." : "No se pudo clasificar (HTTP " + respuesta.status + ")."); }
                          setMensajeCategoria("Categoría confirmada y auditada.");
                          recargar();
                        } catch (fallo) { setMensajeCategoria(fallo instanceof Error ? fallo.message : String(fallo)); }
                      }}>Guardar categoría</button>
                    </details>
                  )}</td>
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
                  <td><button type="button" onClick={() => setExpedienteSeleccionado(factura.expediente_id)}>Ver todos los productos</button> <a href={`/expedientes/${factura.expediente_id}`}>Abrir expediente</a></td>
                </tr>
              ))}</tbody>
            </table>
          </div>}
        </section>
      )}
      {expedienteSeleccionado && (
        <section aria-label="Detalle de todos los ítems del expediente">
          <h3>Todos los ítems del comprobante seleccionado</h3>
          <button type="button" onClick={() => setExpedienteSeleccionado(null)}>Cerrar</button>
          {cargandoDetalle && <p>Consultando detalle…</p>}
          {errorDetalle && <p role="alert">{errorDetalle}</p>}
          {detalle && (
            <>
              <p>Moneda: {detalle.moneda}. Estado de auditoría: {detalle.estado_auditoria}.</p>
              {detalle.lineas.length === 0 ? <p>Este expediente no tiene líneas recuperables.</p> : (
                <div style={{ overflowX: "auto" }}>
                  <table><thead><tr><th>Línea</th><th>Categoría</th><th>Descripción</th><th>Cantidad</th><th>Importe</th></tr></thead>
                    <tbody>{detalle.lineas.map((linea) => (
                      <tr key={linea.documento_id + ":" + linea.numero_linea}>
                        <td>{linea.numero_linea}</td><td>{linea.categoria}</td><td>{linea.descripcion}</td>
                        <td>{linea.cantidad} {linea.unidad}</td><td>{linea.importe} {detalle.moneda}</td>
                      </tr>
                    ))}</tbody></table>
                </div>
              )}
              <a href={`/expedientes/${detalle.expediente_id}`}>Abrir expediente original</a>
            </>
          )}
        </section>
      )}
      </>}
    </section>
  );
}
