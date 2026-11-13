import { useEffect, useRef, useState, type FormEvent } from "react";
import { Paginacion } from "../componentes";
import { Link } from "react-router-dom";
import { formatearFecha, formatearMonto } from "../formato";
import type { Moneda } from "../tipos";
import { conParametros, enviarJson, useDatos } from "../api";

type Categoria = { id: string; nombre: string; activa: boolean };
type Item = { id: string; descripcion: string; unidad_base: string; categoria: string; categoria_confirmada: boolean; activo: boolean; fuera_rubro: boolean; precio: string | null; moneda_precio: Moneda | null; varios_precios: boolean; lineas_asociadas: number };
type Catalogo = { total: number; items: Item[] };

export default function CatalogoItems({ puedeAdministrar = false }: { puedeAdministrar?: boolean }) {
  const [buscar, setBuscar] = useState("");
  const [filtro, setFiltro] = useState("");
  const [pagina, setPagina] = useState(0);
  const [itemAbierto, setItemAbierto] = useState<Item | null>(null);
  const [precioAbierto, setPrecioAbierto] = useState<Item | null>(null);
  const [combinar, setCombinar] = useState<Item | null>(null);
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

  async function actualizar(item: Item, valores: { categoria_id?: string; activo?: boolean; fuera_rubro?: boolean; combinar_en?: string }) {
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
        Configuración de ítems
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
          <thead><tr><th>Descripción</th><th>Precio ítem</th><th>Unidad base</th><th>Categoría</th><th>Líneas asociadas</th><th>Estado</th><th>Acciones</th></tr></thead>
          <tbody>{catalogo.datos.items.map((item) => <tr key={item.id} className={item.fuera_rubro ? "item-fuera-rubro" : undefined}>
            <td>{item.descripcion}</td><td>{item.varios_precios ? <button type="button" onClick={() => setPrecioAbierto(item)}>Ver precios</button>
              : item.precio && item.moneda_precio ? `${item.moneda_precio} ${precioVisible(item.precio)}` : "Sin precio"}</td><td>{item.unidad_base || "No indicada"}</td>
            <td><span>{item.categoria}</span>{administrar && <><select aria-label={`Categoría para ${item.descripcion}`} value={(categorias.datos ?? []).find((categoria) => categoria.nombre === item.categoria)?.id ?? ""} disabled={ocupado} onChange={(evento) => { if (evento.target.value) void actualizar(item, { categoria_id: evento.target.value }); }}>
              <option value="">Cambiar categoría</option>{(categorias.datos ?? []).filter((categoria) => categoria.activa).map((categoria) => <option key={categoria.id} value={categoria.id}>{categoria.nombre}</option>)}
            </select></>}</td>
            <td>{item.lineas_asociadas}</td><td>{item.fuera_rubro ? "Fuera del rubro" : item.activo ? "Activo" : "Inactivo"}</td>
            <td>
              <button type="button" disabled={!item.lineas_asociadas} onClick={() => setItemAbierto(item)}>Mostrar facturas</button>
              {administrar && <>
                <button type="button" disabled={ocupado} onClick={() => setCombinar(item)}>Combinar</button>
                <button type="button" disabled={ocupado} onClick={() => void actualizar(item, { fuera_rubro: !item.fuera_rubro })}>
                  {item.fuera_rubro ? "Reincorporar al rubro" : "Marcar fuera del rubro"}
                </button>
              </>}
              {administrar && <button type="button" disabled={ocupado} onClick={() => void actualizar(item, { activo: !item.activo })}>{item.activo ? "Desactivar" : "Activar"}</button>}
            </td>
          </tr>)}</tbody>
        </table></div>}
        {(pagina > 0 || catalogo.datos.total > 50) && <div className="acciones">
          <button type="button" disabled={!pagina} onClick={() => setPagina(pagina - 1)}>Anterior</button>
          <button type="button" disabled={(pagina + 1) * 50 >= catalogo.datos.total} onClick={() => setPagina(pagina + 1)}>Siguiente</button>
        </div>}
      </>}
      {precioAbierto && <PreciosItem item={precioAbierto} cerrar={() => setPrecioAbierto(null)} />}
      {combinar && <CombinarItem item={combinar} cerrar={() => setCombinar(null)} aplicar={(id) => {
        setCombinar(null);
        void actualizar(combinar, { combinar_en: id });
      }} />}
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
  fuera_rubro: string;
};

type FiltrosFacturas = { desde: string; hasta: string; emisor_buscar: string; receptor_buscar: string };
const FILTROS_VACIOS = { desde: "", hasta: "", emisor_buscar: "", receptor_buscar: "" };

export function FacturasItem({ item, cerrar, inicial = FILTROS_VACIOS }: {
  item: { id: string; descripcion: string }; cerrar: () => void; inicial?: FiltrosFacturas;
}) {
  const modal = useRef<HTMLDialogElement>(null);
  const [pagina, setPagina] = useState(0);
  const [filtros, setFiltros] = useState({ ...inicial, tipo_empresa: "" });
  const [orden, setOrden] = useState("emisor");
  const ruta = `/api/v1/contabilidad-items/productos/${item.id}/facturas`;
  const parametros = { ...filtros, vista_catalogo: "true" };
  const facturas = useDatos<FacturaItem[]>(conParametros(
    ruta, { ...parametros, limite: "50", offset: String(pagina * 50), ordenar_por: orden },
  ));
  const totales = useDatos<{ moneda: Moneda; importe_total: string; comprobantes: string }[]>(
    conParametros(ruta, { ...parametros, solo_totales: "true" }),
  );
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
      <form onSubmit={(evento) => {
        evento.preventDefault();
        const datos = new FormData(evento.currentTarget);
        const mes = String(datos.get("mes") ?? "");
        const [anio = 0, numeroMes = 0] = mes.split("-").map(Number);
        const ultimoDia = mes ? new Date(Date.UTC(anio, numeroMes, 0)).getUTCDate() : 0;
        setPagina(0);
        setFiltros({
          desde: mes ? `${mes}-01` : String(datos.get("desde") ?? ""),
          hasta: mes ? `${mes}-${ultimoDia}` : String(datos.get("hasta") ?? ""),
          tipo_empresa: String(datos.get("tipo") ?? ""),
          emisor_buscar: String(datos.get("emisor") ?? "").trim(),
          receptor_buscar: String(datos.get("receptor") ?? "").trim(),
        });
      }}>
        <label>Mes <input name="mes" type="month" /></label>
        <label>Desde <input name="desde" type="date" defaultValue={inicial.desde} /></label>
        <label>Hasta <input name="hasta" type="date" defaultValue={inicial.hasta} /></label>
        <label>Tipo de proveedor <select name="tipo"><option value="">Todos</option><option>A</option><option>B</option></select></label>
        <label>Proveedor <input defaultValue={inicial.emisor_buscar} name="emisor" type="search" maxLength={150} placeholder="RUC o razón social" /></label>
        <label>Cliente <input defaultValue={inicial.receptor_buscar} name="receptor" type="search" maxLength={150} placeholder="RUC o razón social" /></label>
        <button type="submit">Filtrar</button>
      </form>
      <section className="tarjeta" aria-label="Total de comprobantes asociados" aria-live="polite">
        <h4>Total de comprobantes asociados</h4>
        {totales.cargando && <p>Calculando total…</p>}
        {totales.error && <p role="alert">{totales.error}</p>}
        {totales.datos?.length === 0 && <p>Sin comprobantes para estos filtros.</p>}
        {totales.datos?.map((total) => <p key={total.moneda}>
          <strong style={{ fontSize: "1.6rem" }}>{formatearMonto(total.moneda, total.importe_total)}</strong>
          {" · "}{total.comprobantes} comprobantes
        </p>)}
      </section>
      <div role="tablist" aria-label="Orden de comprobantes" className="acciones">
        {["emisor", "receptor"].map((opcion) => <button key={opcion} type="button" role="tab"
          aria-selected={orden === opcion} onClick={() => { setOrden(opcion); setPagina(0); }}>
          {opcion === "emisor" ? "Por emisor" : "Por receptor"}
        </button>)}
      </div>
      {facturas.cargando && <p role="status">Cargando facturas…</p>}
      {facturas.error && <p role="alert">{facturas.error}</p>}
      {facturas.datos && (facturas.datos.length ? (
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead><tr><th>ID</th><th>Emisor</th><th>Fecha</th><th>Receptor</th><th>Correlativo</th><th>Monto</th></tr></thead>
            <tbody>{facturas.datos.map((factura) => <tr key={factura.expediente_id} className={factura.fuera_rubro === "true" ? "item-fuera-rubro" : undefined}>
              <td style={{ overflowWrap: "anywhere" }}>{factura.expediente_id}</td>
              <td>{factura.emisor_ruc}<br />{factura.emisor_nombre}</td>
              <td>{formatearFecha(factura.fecha_emision)}</td>
              <td>{factura.receptor_ruc}<br />{factura.receptor_nombre}</td>
              <td><Link to={`/expedientes/${factura.expediente_id}`}>{factura.comprobante}</Link>{factura.fuera_rubro === "true" && <small> · Fuera del rubro</small>}</td>
              <td>{formatearMonto(factura.moneda, factura.importe_total)}</td>
            </tr>)}</tbody>
          </table>
        </div>
      ) : <p>No hay facturas asociadas.</p>)}
      {totales.datos && <Paginacion pagina={pagina} hayMas={false} porPagina={50}
        total={totales.datos.reduce((suma, total) => suma + Number(total.comprobantes), 0)}
        alCambiar={setPagina} />}
    </dialog>
  );
}

function PreciosItem({ item, cerrar }: { item: Item; cerrar: () => void }) {
  const modal = useRef<HTMLDialogElement>(null);
  const precios = useDatos<{ moneda: Moneda; unidad: string; precio: string; lineas: string }[]>(
    `/api/v1/contabilidad-items/productos/${item.id}/facturas?vista_catalogo=true&solo_precios=true`,
  );
  useEffect(() => { modal.current?.showModal(); }, []);
  return <dialog ref={modal} onClose={cerrar} aria-label="Precios del ítem">
    <h3>Precios · {item.descripcion}</h3>
    {precios.cargando && <p>Cargando precios…</p>}
    {precios.error && <p role="alert">{precios.error}</p>}
    {precios.datos?.length === 0 && <p>Sin precio unitario registrado. Reescanea los comprobantes históricos para recuperarlo.</p>}
    {precios.datos?.length ? <table>
      <thead><tr><th>Moneda</th><th>Unidad</th><th>Valor unitario</th><th>Líneas</th></tr></thead>
      <tbody>{precios.datos.map((p) => <tr key={`${p.moneda}-${p.unidad}-${p.precio}`}>
        <td>{p.moneda}</td><td>{p.unidad}</td><td>{precioVisible(p.precio)}</td><td>{p.lineas}</td>
      </tr>)}</tbody>
    </table> : null}
    <button type="button" onClick={() => modal.current?.close()}>Cerrar</button>
  </dialog>;
}

function CombinarItem({ item, cerrar, aplicar }: { item: Item; cerrar: () => void; aplicar: (id: string) => void }) {
  const modal = useRef<HTMLDialogElement>(null);
  const [buscar, setBuscar] = useState("");
  const [destino, setDestino] = useState("");
  const candidatos = useDatos<Catalogo>(buscar.trim() ? conParametros("/api/v1/contabilidad-items/catalogo",
    { buscar: buscar.trim(), incluir_inactivos: "true" }) : null);
  useEffect(() => { modal.current?.showModal(); }, []);
  return <dialog ref={modal} onClose={cerrar} aria-label="Combinar ítems">
    <h3>Combinar · {item.descripcion}</h3>
    <label>Buscar ítem principal <input type="search" maxLength={150} value={buscar}
      onChange={(evento) => { setBuscar(evento.target.value); setDestino(""); }} /></label>
    {candidatos.error && <p role="alert">{candidatos.error}</p>}
    <label>Ítem principal <select value={destino} onChange={(evento) => setDestino(evento.target.value)}>
      <option value="">Selecciona un ítem</option>
      {buscar.trim() && candidatos.datos?.items.filter((p) => p.id !== item.id).map((p) =>
        <option key={p.id} value={p.id}>{p.descripcion} · {p.unidad_base}</option>)}
    </select></label>
    <p>Las líneas y las futuras coincidencias de este nombre se asociarán al ítem principal.</p>
    <button type="button" onClick={() => modal.current?.close()}>Cancelar</button>
    <button type="button" disabled={!destino} onClick={() => aplicar(destino)}>Confirmar combinación</button>
  </dialog>;
}

function precioVisible(precio: string) {
  return precio.replace(/(\.\d*?[1-9])0+$|\.0+$/, "$1");
}
