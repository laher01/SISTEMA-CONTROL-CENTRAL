import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { formatearFecha, formatearMonto } from "../formato";
import type { Moneda } from "../tipos";
import { conParametros, enviarJson, useDatos } from "../api";

type Categoria = { id: string; nombre: string; activa: boolean };
type Item = { id: string; descripcion: string; unidad_base: string; categoria: string; categoria_confirmada: boolean; activo: boolean; lineas_asociadas: number };
type Catalogo = { total: number; items: Item[] };

export default function CatalogoItems({ puedeAdministrar = false }: { puedeAdministrar?: boolean }) {
  const [buscar, setBuscar] = useState("");
  const [filtro, setFiltro] = useState("");
  const [pagina, setPagina] = useState(0);
  const [itemAbierto, setItemAbierto] = useState<Item | null>(null);
  const [administrar, setAdministrar] = useState(false);
  const [descripcion, setDescripcion] = useState("");
  const [unidad, setUnidad] = useState("");
  const [categoriaId, setCategoriaId] = useState("");
  const [mensaje, setMensaje] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const categorias = useDatos<Categoria[]>("/api/v1/contabilidad-items/categorias");
  const ruta = conParametros("/api/v1/contabilidad-items/catalogo", {
    buscar: filtro, limite: "50", offset: String(pagina * 50),
    solo_con_lineas: String(!administrar), incluir_inactivos: "true",
  });
  const catalogo = useDatos<Catalogo>(ruta);

  async function crear(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setOcupado(true);
    setMensaje("");
    try {
      await enviarJson("/api/v1/contabilidad-items/catalogo", "POST", {
        descripcion,
        unidad_base: unidad,
        categoria_id: categoriaId,
      });
      setDescripcion("");
      setUnidad("");
      setCategoriaId("");
      setMensaje("Ítem agregado al catálogo. Se vinculará a nuevas líneas solo cuando coincidan descripción normalizada y unidad.");
      catalogo.recargar();
    } catch (fallo) {
      setMensaje(fallo instanceof Error ? fallo.message : String(fallo));
    } finally {
      setOcupado(false);
    }
  }

  async function actualizar(item: Item, valores: { categoria_id?: string; activo?: boolean }) {
    setOcupado(true);
    setMensaje("");
    try {
      await enviarJson(`/api/v1/contabilidad-items/catalogo/${item.id}`, "PATCH", valores);
      catalogo.recargar();
    } catch (fallo) {
      setMensaje(fallo instanceof Error ? fallo.message : String(fallo));
    } finally {
      setOcupado(false);
    }
  }

  return (
    <section aria-label="Catálogo de ítems">
      <h2>Ítems</h2>
      <p>Consulta los ítems de tus comprobantes autorizados. No se modifican las líneas fuente ni los totales de facturas.</p>
      {!puedeAdministrar && <p>Vista de consulta. La administración del catálogo compartido está reservada a Administración.</p>}
      {puedeAdministrar && <label>
        <input type="checkbox" checked={administrar} onChange={(evento) => { setAdministrar(evento.target.checked); setPagina(0); }} />
        Administrar catálogo
      </label>}
      {administrar && <form onSubmit={crear}>
        <label htmlFor="item-descripcion">Descripción del ítem</label>
        <textarea id="item-descripcion" value={descripcion} onChange={(evento) => setDescripcion(evento.target.value)} maxLength={2000} minLength={2} required rows={4} />
        <label htmlFor="item-unidad">Unidad</label>
        <input id="item-unidad" value={unidad} onChange={(evento) => setUnidad(evento.target.value)} maxLength={40} required placeholder="NIU, KG, GL, CAJA…" />
        <label htmlFor="item-categoria">Categoría</label>
        <select id="item-categoria" value={categoriaId} onChange={(evento) => setCategoriaId(evento.target.value)} required>
          <option value="">Seleccione una categoría</option>
          {(categorias.datos ?? []).filter((categoria) => categoria.activa).map((categoria) => <option key={categoria.id} value={categoria.id}>{categoria.nombre}</option>)}
        </select>
        <button type="submit" disabled={ocupado || !categoriaId}>Agregar ítem</button>
      </form>}
      {mensaje && <p role="status">{mensaje}</p>}
      {categorias.error && <p role="alert">No se pudieron cargar las categorías: {categorias.error}</p>}
      <form onSubmit={(evento) => { evento.preventDefault(); setFiltro(buscar.trim()); setPagina(0); }}>
        <label htmlFor="buscar-catalogo">Buscar ítem o categoría</label>
        <input id="buscar-catalogo" type="search" value={buscar} onChange={(evento) => setBuscar(evento.target.value)} maxLength={150} />
        <button type="submit">Buscar</button>
      </form>
      {catalogo.error && <p role="alert">No se pudo cargar el catálogo: {catalogo.error}</p>}
      {catalogo.cargando && <p>Cargando ítems…</p>}
      {catalogo.datos && <>
        <p>{catalogo.datos.total} ítems encontrados. </p>
        {catalogo.datos.items.length === 0 ? <p>No hay ítems en el catálogo para este filtro.</p> : <div style={{ overflowX: "auto" }}><table>
          <thead><tr><th>Descripción</th><th>Unidad base</th><th>Categoría</th><th>Líneas asociadas</th><th>Estado</th><th>Acciones</th></tr></thead>
          <tbody>{catalogo.datos.items.map((item) => <tr key={item.id}>
            <td>{item.descripcion}</td><td>{item.unidad_base || "No indicada"}</td>
            <td><span>{item.categoria}</span>{administrar && <><select aria-label={`Categoría para ${item.descripcion}`} value={(categorias.datos ?? []).find((categoria) => categoria.nombre === item.categoria)?.id ?? ""} disabled={ocupado} onChange={(evento) => { if (evento.target.value) void actualizar(item, { categoria_id: evento.target.value }); }}>
              <option value="">Cambiar categoría</option>{(categorias.datos ?? []).filter((categoria) => categoria.activa).map((categoria) => <option key={categoria.id} value={categoria.id}>{categoria.nombre}</option>)}
            </select></>}</td>
            <td>{item.lineas_asociadas}</td><td>{item.activo ? "Activo" : "Inactivo"}</td>
            <td>
              <button type="button" disabled={!item.lineas_asociadas} onClick={() => setItemAbierto(item)}>Mostrar facturas</button>
              {administrar && <button type="button" disabled={ocupado} onClick={() => void actualizar(item, { activo: !item.activo })}>{item.activo ? "Desactivar" : "Activar"}</button>}
            </td>
          </tr>)}</tbody>
        </table></div>}
        {(pagina > 0 || catalogo.datos.total > 50) && <div className="acciones">
          <button type="button" disabled={!pagina} onClick={() => setPagina(pagina - 1)}>Anterior</button>
          <button type="button" disabled={(pagina + 1) * 50 >= catalogo.datos.total} onClick={() => setPagina(pagina + 1)}>Siguiente</button>
        </div>}
      </>}
      {itemAbierto && <FacturasItem item={itemAbierto} cerrar={() => setItemAbierto(null)} />}
    </section>
  );
}

type FacturaItem = {
  expediente_id: string;
  comprobante: string;
  fecha_emision: string;
  moneda: Moneda;
  importe_total: string;
  emisor_ruc: string;
  emisor_nombre: string;
  receptor_ruc: string;
  receptor_nombre: string;
};

function FacturasItem({ item, cerrar }: { item: Item; cerrar: () => void }) {
  const modal = useRef<HTMLDialogElement>(null);
  const [pagina, setPagina] = useState(0);
  const facturas = useDatos<FacturaItem[]>(conParametros(
    `/api/v1/contabilidad-items/productos/${item.id}/facturas`,
    { vista_catalogo: "true", limite: "51", offset: String(pagina * 50) },
  ));
  useEffect(() => {
    modal.current?.showModal();
  }, []);
  return (
    <dialog ref={modal} onClose={cerrar} aria-labelledby="facturas-item-titulo"
      style={{ width: "min(1100px, 94vw)", maxHeight: "86vh" }}>
      <header className="acciones">
        <h3 id="facturas-item-titulo">Facturas asociadas · {item.descripcion}</h3>
        <button type="button" onClick={() => modal.current?.close()}>Cerrar</button>
      </header>
      {facturas.cargando && <p role="status">Cargando facturas…</p>}
      {facturas.error && <p role="alert">{facturas.error}</p>}
      {facturas.datos && (facturas.datos.length ? (
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead><tr><th>ID</th><th>Emisor</th><th>Fecha</th><th>Receptor</th><th>Correlativo</th><th>Monto</th></tr></thead>
            <tbody>{facturas.datos.slice(0, 50).map((factura) => <tr key={factura.expediente_id}>
              <td style={{ overflowWrap: "anywhere" }}>{factura.expediente_id}</td>
              <td>{factura.emisor_ruc}<br />{factura.emisor_nombre}</td>
              <td>{formatearFecha(factura.fecha_emision)}</td>
              <td>{factura.receptor_ruc}<br />{factura.receptor_nombre}</td>
              <td><Link to={`/expedientes/${factura.expediente_id}`}>{factura.comprobante}</Link></td>
              <td>{formatearMonto(factura.moneda, factura.importe_total)}</td>
            </tr>)}</tbody>
          </table>
        </div>
      ) : <p>No hay facturas asociadas.</p>)}
      {(pagina > 0 || (facturas.datos?.length ?? 0) > 50) && <div className="acciones">
        <button type="button" disabled={facturas.cargando || !pagina} onClick={() => setPagina(pagina - 1)}>Anterior</button>
        <button type="button" disabled={facturas.cargando || (facturas.datos?.length ?? 0) <= 50} onClick={() => setPagina(pagina + 1)}>Siguiente</button>
      </div>}
    </dialog>
  );
}
