import { useState, type FormEvent } from "react";
import { enviarJson, useDatos } from "../api";

type Categoria = { id: string; nombre: string; activa: boolean; created_at: string };

export default function CategoriasItems({ puedeAdministrar = false }: { puedeAdministrar?: boolean }) {
  const { datos, error, cargando, recargar } = useDatos<Categoria[]>("/api/v1/contabilidad-items/categorias");
  const [nombre, setNombre] = useState("");
  const [mensaje, setMensaje] = useState("");
  const [ocupado, setOcupado] = useState(false);

  async function crear(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setOcupado(true);
    setMensaje("");
    try {
      await enviarJson("/api/v1/contabilidad-items/categorias", "POST", { nombre });
      setNombre("");
      setMensaje("Categoría creada.");
      recargar();
    } catch (fallo) {
      setMensaje(fallo instanceof Error ? fallo.message : String(fallo));
    } finally {
      setOcupado(false);
    }
  }

  async function cambiarEstado(categoria: Categoria) {
    setOcupado(true);
    setMensaje("");
    try {
      await enviarJson(`/api/v1/contabilidad-items/categorias/${categoria.id}`, "PATCH", { activa: !categoria.activa });
      recargar();
    } catch (fallo) {
      setMensaje(fallo instanceof Error ? fallo.message : String(fallo));
    } finally {
      setOcupado(false);
    }
  }

  async function renombrar(categoria: Categoria) {
    const nuevoNombre = window.prompt("Nuevo nombre de categoría", categoria.nombre);
    if (!nuevoNombre || nuevoNombre.trim() === categoria.nombre) return;
    setOcupado(true);
    setMensaje("");
    try {
      await enviarJson(`/api/v1/contabilidad-items/categorias/${categoria.id}`, "PATCH", { nombre: nuevoNombre.trim() });
      recargar();
    } catch (fallo) {
      setMensaje(fallo instanceof Error ? fallo.message : String(fallo));
    } finally {
      setOcupado(false);
    }
  }

  return (
    <section aria-label="Categorías de ítems">
      <h2>Categorías de Ítems</h2>
      <p>Las categorías son propias de esta empresa. Al renombrar una categoría, se actualiza el nombre mostrado en sus ítems; desactivarla conserva el historial.</p>
      {!puedeAdministrar && <p>Vista de consulta. La administración del catálogo compartido está reservada a Administración.</p>}
      {puedeAdministrar && <form onSubmit={crear}>
        <label htmlFor="categoria-nombre">Nueva categoría</label>
        <input id="categoria-nombre" value={nombre} onChange={(evento) => setNombre(evento.target.value)} maxLength={80} minLength={2} required />
        <button type="submit" disabled={ocupado}>Agregar categoría</button>
      </form>}
      {mensaje && <p role="status">{mensaje}</p>}
      {error && <p role="alert">No se pudieron cargar las categorías: {error}</p>}
      {cargando && <p>Cargando categorías…</p>}
      {datos && <div style={{ overflowX: "auto" }}><table>
        <thead><tr><th>Categoría</th><th>Estado</th>{puedeAdministrar && <th>Acciones</th>}</tr></thead>
        <tbody>{datos.map((categoria) => <tr key={categoria.id}>
          <td>{categoria.nombre}</td><td>{categoria.activa ? "Activa" : "Inactiva"}</td>
          {puedeAdministrar && <td><button type="button" disabled={ocupado} onClick={() => void renombrar(categoria)}>Renombrar</button>{" "}
            <button type="button" disabled={ocupado} onClick={() => void cambiarEstado(categoria)}>{categoria.activa ? "Desactivar" : "Activar"}</button></td>
          }
        </tr>)}</tbody>
      </table></div>}
    </section>
  );
}
