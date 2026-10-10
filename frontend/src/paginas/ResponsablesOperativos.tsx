import { useState, type FormEvent } from "react";

import { enviarJson, useDatos } from "../api";

type Responsable = { id: string; codigo: string; nombre: string; activo: boolean; creador: string; rol_creador: string; puede_gestionar: boolean };
type Alta = { miembro: Responsable; credencial: { login: string; clave_temporal: string } };

export default function ResponsablesOperativos() {
  const { datos, error, cargando, recargar } = useDatos<Responsable[]>(
    "/api/v1/miembros/responsables-operativos/directorio",
  );
  const [nombre, setNombre] = useState("");
  const [credencial, setCredencial] = useState<Alta["credencial"] | null>(null);
  const [mensaje, setMensaje] = useState("");
  const [guardando, setGuardando] = useState(false);
  const crear = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setGuardando(true);
    setMensaje("");
    setCredencial(null);
    try {
      const alta = await enviarJson<Alta>("/api/v1/miembros/responsables-operativos", "POST", { nombre });
      setCredencial(alta.credencial);
      setNombre("");
      setMensaje("Responsable registrado en la Administración.");
      recargar();
    } catch (err) {
      setMensaje(err instanceof Error ? err.message : String(err));
    } finally {
      setGuardando(false);
    }
  };
  const [procesandoId, setProcesandoId] = useState("");
  const gestionar = async (r: Responsable, accion: "editar" | "desactivar" | "clave") => {
    if (!r.puede_gestionar) return;
    const nuevoNombre = accion === "editar" ? window.prompt("Nuevo nombre del Responsable", r.nombre) : null;
    if (accion === "editar" && !nuevoNombre?.trim()) return;
    if (accion === "desactivar" && !window.confirm("Desactivar acceso del Responsable? Se conserva el historial.")) return;
    if (accion === "clave" && !window.confirm("Revocar la clave anterior y emitir una clave temporal?")) return;
    setProcesandoId(r.id);
    setMensaje("");
    setCredencial(null);
    try {
      const ruta = `/api/v1/miembros/responsables-operativos/${r.id}`;
      if (accion === "editar") {
        await enviarJson(ruta, "PATCH", { nombre: nuevoNombre?.trim() });
        setMensaje("Nombre actualizado.");
      } else if (accion === "desactivar") {
        await enviarJson(ruta + "/desactivar", "POST", {});
        setMensaje("Responsable desactivado; historial conservado.");
      } else {
        const acceso = await enviarJson<Alta["credencial"]>(ruta + "/restablecer-acceso", "POST", {});
        setCredencial(acceso);
        setMensaje("Clave temporal emitida. La anterior queda revocada.");
      }
      recargar();
    } catch (err) {
      setMensaje(err instanceof Error ? err.message : String(err));
    } finally {
      setProcesandoId("");
    }
  };
  return <section className="panel-configuracion">
    <h2>Responsables del espacio administrativo</h2>
    <p>Los Responsables creados desde Administración, Gerencia o Secretaría
      comparten este directorio. Los vínculos operativos con Gerentes se autorizan
      posteriormente desde Administración.</p>
    <form className="filtros" onSubmit={(e) => void crear(e)}>
      <label>Nombre completo
        <input required minLength={3} maxLength={200} value={nombre}
          onChange={(e) => setNombre(e.target.value)} />
      </label>
      <button type="submit" disabled={guardando}>
        {guardando ? "Creando…" : "Crear Responsable"}
      </button>
    </form>
    {mensaje && <p role="status">{mensaje}</p>}
    {credencial && <div className="panel-configuracion">
      <strong>Clave temporal — se muestra una sola vez</strong>
      <p>Usuario: {credencial.login}</p>
      <p>Contraseña temporal: {credencial.clave_temporal}</p>
      <button type="button" onClick={() => setCredencial(null)}>Ocultar</button>
    </div>}
    {cargando && <p>Cargando…</p>}
    {error && <p role="alert">{error}</p>}
    <table><thead><tr><th>Usuario</th><th>Nombre</th><th>Estado</th><th>Creado por</th><th>Acciones</th></tr></thead>
      <tbody>{(datos ?? []).map((r) => <tr key={r.id}><td>{r.codigo}</td>
        <td>{r.nombre}</td><td>{r.activo ? "Activo" : "Inactivo"}</td>
        <td>{r.creador} ({r.rol_creador})</td>
        <td>{r.puede_gestionar ? <>
          <button type="button" disabled={Boolean(procesandoId)} onClick={() => void gestionar(r, "editar")}>Editar</button>
          {r.activo && <button type="button" disabled={Boolean(procesandoId)} onClick={() => void gestionar(r, "clave")}>Nueva clave</button>}
          {r.activo && <button type="button" disabled={Boolean(procesandoId)} onClick={() => void gestionar(r, "desactivar")}>Desactivar</button>}
        </> : <span className="tenue">Solo consulta</span>}</td>
      </tr>)}</tbody>
    </table>
  </section>;
}
