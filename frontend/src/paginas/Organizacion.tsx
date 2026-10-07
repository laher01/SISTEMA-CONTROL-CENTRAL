import { useMemo, useState, type FormEvent } from "react";

import { enviarJson, useDatos } from "../api";
import type { Gestor, Miembro, RolMiembro } from "../tipos";

const ROLES: RolMiembro[] = ["ADMINISTRADOR", "GERENTE", "SECRETARIA", "USUARIO"];

export default function Organizacion() {
  const { datos: miembros, error, cargando, recargar } = useDatos<Miembro[]>("/api/v1/miembros");
  const { datos: gestores, recargar: recargarGestores } = useDatos<Gestor[]>("/api/v1/gestores");

  const [codigo, setCodigo] = useState("");
  const [nombre, setNombre] = useState("");
  const [rol, setRol] = useState<RolMiembro>("USUARIO");
  const [miembroEditando, setMiembroEditando] = useState<string | null>(null);

  const [usuarioId, setUsuarioId] = useState("");
  const [codigoGestor, setCodigoGestor] = useState("");
  const [nombreGestor, setNombreGestor] = useState("");
  const [gestorEditando, setGestorEditando] = useState<string | null>(null);

  const [mensaje, setMensaje] = useState("");

  const usuarios = useMemo(
    () => (miembros ?? []).filter((m) => m.rol === "USUARIO"),
    [miembros],
  );

  const guardarMiembro = async (e: FormEvent) => {
    e.preventDefault();
    setMensaje("");
    try {
      if (miembroEditando) {
        await enviarJson<Miembro>("/api/v1/miembros/" + miembroEditando, "PATCH", {
          codigo,
          nombre,
          rol,
        });
        setMensaje("Miembro actualizado.");
      } else {
        await enviarJson<Miembro>("/api/v1/miembros", "POST", { codigo, nombre, rol });
        setMensaje("Miembro creado.");
      }
      setCodigo("");
      setNombre("");
      setRol("USUARIO");
      setMiembroEditando(null);
      recargar();
      recargarGestores();
    } catch (error) {
      setMensaje(error instanceof Error ? error.message : String(error));
    }
  };

  const editarMiembro = (miembro: Miembro) => {
    setMiembroEditando(miembro.id);
    setCodigo(miembro.codigo);
    setNombre(miembro.nombre);
    setRol(miembro.rol);
    setMensaje("");
  };

  const cancelarMiembro = () => {
    setMiembroEditando(null);
    setCodigo("");
    setNombre("");
    setRol("USUARIO");
  };

  const guardarGestor = async (e: FormEvent) => {
    e.preventDefault();
    setMensaje("");
    try {
      const datos = {
        codigo: codigoGestor,
        nombre: nombreGestor,
        usuario_id: usuarioId,
      };
      if (gestorEditando) {
        await enviarJson<Gestor>("/api/v1/gestores/" + gestorEditando, "PATCH", datos);
        setMensaje("Gestor actualizado.");
      } else {
        await enviarJson<Gestor>("/api/v1/gestores", "POST", datos);
        setMensaje("Gestor creado y vinculado al usuario.");
      }
      setCodigoGestor("");
      setNombreGestor("");
      setGestorEditando(null);
      recargarGestores();
    } catch (error) {
      setMensaje(error instanceof Error ? error.message : String(error));
    }
  };

  const editarGestor = (gestor: Gestor) => {
    setGestorEditando(gestor.id);
    setUsuarioId(gestor.usuario_id ?? "");
    setCodigoGestor(gestor.codigo);
    setNombreGestor(gestor.nombre);
    setMensaje("");
  };

  const cancelarGestor = () => {
    setGestorEditando(null);
    setCodigoGestor("");
    setNombreGestor("");
  };

  return (
    <>
      <h2>Organización</h2>
      <p className="tenue">
        Jerarquía operativa: Administrador, Gerente, Secretaría, Usuario y Gestor.
        Cada Gestor pertenece a un Usuario.
      </p>
      {error && <p className="error">{error}</p>}
      {cargando && <p>Cargando…</p>}

      <div className="columnas">
        <section>
          <h3>{miembroEditando ? "Editar miembro" : "Crear miembro"}</h3>
          <form onSubmit={guardarMiembro} className="formulario-linea">
            <input
              placeholder="Código, ej. WILL01"
              value={codigo}
              onChange={(e) => setCodigo(e.target.value)}
              required
            />
            <input
              placeholder="Nombre"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              required
            />
            <select value={rol} onChange={(e) => setRol(e.target.value as RolMiembro)}>
              {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
            <button type="submit">{miembroEditando ? "Guardar" : "Crear"}</button>
            {miembroEditando && (
              <button type="button" onClick={cancelarMiembro}>Cancelar</button>
            )}
          </form>

          <h3>Miembros</h3>
          <table>
            <thead>
              <tr><th>Código</th><th>Nombre</th><th>Rol</th><th>Acciones</th></tr>
            </thead>
            <tbody>
              {miembros?.map((m) => (
                <tr key={m.id}>
                  <td>{m.codigo}</td>
                  <td>{m.nombre}</td>
                  <td>{m.rol}</td>
                  <td><button type="button" onClick={() => editarMiembro(m)}>Editar</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section>
          <h3>{gestorEditando ? "Editar gestor" : "Crear gestor"}</h3>
          <form onSubmit={guardarGestor} className="formulario-linea">
            <select value={usuarioId} onChange={(e) => setUsuarioId(e.target.value)} required>
              <option value="">Usuario propietario</option>
              {usuarios.map((u) => (
                <option key={u.id} value={u.id}>{u.codigo} · {u.nombre}</option>
              ))}
            </select>
            <input
              placeholder="Código gestor"
              value={codigoGestor}
              onChange={(e) => setCodigoGestor(e.target.value)}
              required
            />
            <input
              placeholder="Nombre gestor"
              value={nombreGestor}
              onChange={(e) => setNombreGestor(e.target.value)}
              required
            />
            <button type="submit">{gestorEditando ? "Guardar gestor" : "Crear gestor"}</button>
            {gestorEditando && (
              <button type="button" onClick={cancelarGestor}>Cancelar</button>
            )}
          </form>

          <h3>Gestores</h3>
          <table>
            <thead><tr><th>Gestor</th><th>Usuario</th><th>Acciones</th></tr></thead>
            <tbody>
              {gestores?.map((g) => {
                const usuario = usuarios.find((u) => u.id === g.usuario_id);
                return (
                  <tr key={g.id}>
                    <td>{g.codigo} · {g.nombre}</td>
                    <td>{usuario ? usuario.codigo + " · " + usuario.nombre : "Sin usuario"}</td>
                    <td><button type="button" onClick={() => editarGestor(g)}>Editar</button></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      </div>
      {mensaje && <p className="tenue">{mensaje}</p>}
    </>
  );
}
