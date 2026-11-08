import { useState, type FormEvent } from "react";
import { conParametros, enviarJson, useDatos } from "../api";

type Categoria = { id: string; nombre: string; activa: boolean };
type Item = { id: string; descripcion: string; unidad_base: string; categoria: string; categoria_confirmada: boolean; activo: boolean; lineas_asociadas: number };
type Catalogo = { total: number; items: Item[] };

export default function CatalogoItems() {
  const [buscar, setBuscar] = useState("");
  const [filtro, setFiltro] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [unidad, setUnidad] = useState("");
  const [categoriaId, setCategoriaId] = useState("");
  const [mensaje, setMensaje] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const categorias = useDatos<Categoria[]>("/api/v1/contabilidad-items/categorias");
  const ruta = conParametros("/api/v1/contabilidad-items/catalogo", { buscar: filtro, limite: "200" });
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
      <p>Agrega productos canónicos por descripción y unidad. No se crean líneas de factura; las líneas fuente permanecen intactas y las asociaciones nuevas solo se incorporan al reescanear si coinciden exactamente.</p>
      <form onSubmit={crear}>
        <label htmlFor="item-descripcion">Descripción del ítem</label>
        <input id="item-descripcion" value={descripcion} onChange={(evento) => setDescripcion(evento.target.value)} maxLength={500} minLength={2} required />
        <label htmlFor="item-unidad">Unidad</label>
        <input id="item-unidad" value={unidad} onChange={(evento) => setUnidad(evento.target.value)} maxLength={40} required placeholder="NIU, KG, GL, CAJA…" />
        <label htmlFor="item-categoria">Categoría</label>
        <select id="item-categoria" value={categoriaId} onChange={(evento) => setCategoriaId(evento.target.value)} required>
          <option value="">Seleccione una categoría</option>
          {(categorias.datos ?? []).filter((categoria) => categoria.activa).map((categoria) => <option key={categoria.id} value={categoria.id}>{categoria.nombre}</option>)}
        </select>
        <button type="submit" disabled={ocupado || !categoriaId}>Agregar ítem</button>
      </form>
      {mensaje && <p role="status">{mensaje}</p>}
      {categorias.error && <p role="alert">No se pudieron cargar las categorías: {categorias.error}</p>}
      <form onSubmit={(evento) => { evento.preventDefault(); setFiltro(buscar.trim()); }}>
        <label htmlFor="buscar-catalogo">Buscar ítem o categoría</label>
        <input id="buscar-catalogo" type="search" value={buscar} onChange={(evento) => setBuscar(evento.target.value)} maxLength={150} />
        <button type="submit">Buscar</button>
      </form>
      {catalogo.error && <p role="alert">No se pudo cargar el catálogo: {catalogo.error}</p>}
      {catalogo.cargando && <p>Cargando ítems…</p>}
      {catalogo.datos && <>
        <p>{catalogo.datos.total} ítems encontrados. Se muestran hasta 200 por consulta.</p>
        {catalogo.datos.items.length === 0 ? <p>No hay ítems en el catálogo para este filtro.</p> : <div style={{ overflowX: "auto" }}><table>
          <thead><tr><th>Descripción</th><th>Unidad base</th><th>Categoría</th><th>Líneas asociadas</th><th>Estado</th><th>Acciones</th></tr></thead>
          <tbody>{catalogo.datos.items.map((item) => <tr key={item.id}>
            <td>{item.descripcion}</td><td>{item.unidad_base || "No indicada"}</td>
            <td><select aria-label={`Categoría para ${item.descripcion}`} value={(categorias.datos ?? []).find((categoria) => categoria.nombre === item.categoria)?.id ?? ""} disabled={ocupado} onChange={(evento) => { if (evento.target.value) void actualizar(item, { categoria_id: evento.target.value }); }}>
              <option value="">{item.categoria}</option>{(categorias.datos ?? []).filter((categoria) => categoria.activa).map((categoria) => <option key={categoria.id} value={categoria.id}>{categoria.nombre}</option>)}
            </select>{item.categoria_confirmada ? " · Confirmada" : " · Sugerida"}</td>
            <td>{item.lineas_asociadas}</td><td>{item.activo ? "Activo" : "Inactivo"}</td>
            <td><button type="button" disabled={ocupado} onClick={() => void actualizar(item, { activo: !item.activo })}>{item.activo ? "Desactivar" : "Activar"}</button></td>
          </tr>)}</tbody>
        </table></div>}
      </>}
    </section>
  );
}
