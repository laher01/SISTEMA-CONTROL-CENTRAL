import { useMemo, useState, type FormEvent } from "react";

import { enviarJson, useDatos } from "../api";
import type {
  AltaGestor,
  AltaMiembro,
  CredencialTemporal,
  Gestor,
  Miembro,
  RolMiembro,
  SesionActual,
} from "../tipos";

const ROLES: RolMiembro[] = ["ADMINISTRADOR", "GERENTE", "SECRETARIA", "RESPONSABLE", "USUARIO"];

export default function Organizacion({ sesion }: { sesion: SesionActual }) {
  if (sesion.rol === "SUPERADMIN" || sesion.rol === "ADMINISTRADOR") {
    return <OrganizacionAdmin />;
  }
  if (sesion.rol === "USUARIO") return <OrganizacionUsuario sesion={sesion} />;
  return <p>No tiene permiso para administrar la organización.</p>;
}

function OrganizacionAdmin() {
  const { datos: miembros, error, cargando, recargar } = useDatos<Miembro[]>("/api/v1/miembros");
  const { datos: gestores, recargar: recargarGestores } = useDatos<Gestor[]>("/api/v1/gestores");
  const [codigo, setCodigo] = useState("");
  const [nombre, setNombre] = useState("");
  const [rol, setRol] = useState<RolMiembro>("USUARIO");
  const [porcentajeProduccion, setPorcentajeProduccion] = useState("1.5");
  const [miembroEditando, setMiembroEditando] = useState<string | null>(null);
  const [usuarioId, setUsuarioId] = useState("");
  const [codigoGestor, setCodigoGestor] = useState("");
  const [nombreGestor, setNombreGestor] = useState("");
  const [porcentajeGestor, setPorcentajeGestor] = useState("");
  const [gestorEditando, setGestorEditando] = useState<string | null>(null);
  const [credencial, setCredencial] = useState<CredencialTemporal | null>(null);
  const [mensaje, setMensaje] = useState("");

  const responsables = useMemo(
    () => (miembros ?? []).filter((m) => m.rol === "RESPONSABLE"),
    [miembros],
  );
  const usuarios = useMemo(
    () => (miembros ?? []).filter((m) => m.rol === "USUARIO"),
    [miembros],
  );

  const asignarResponsable = async (usuario: Miembro, responsableId: string) => {
    try {
      await enviarJson<Miembro>(`/api/v1/miembros/${usuario.id}/responsable`, "PUT", {
        responsable_id: responsableId || null,
      });
      recargar();
      setMensaje("Responsable actualizado para " + usuario.codigo);
    } catch (e) {
      setMensaje(e instanceof Error ? e.message : String(e));
    }
  };

  const guardarMiembro = async (e: FormEvent) => {
    e.preventDefault();
    setMensaje("");
    setCredencial(null);
    try {
      if (miembroEditando) {
        await enviarJson<Miembro>("/api/v1/miembros/" + miembroEditando, "PATCH", {
          codigo,
          nombre,
          rol,
          porcentaje_produccion: rol === "USUARIO" ? porcentajeProduccion : null,
        });
        setMensaje("Miembro actualizado.");
      } else {
        const alta = await enviarJson<AltaMiembro>("/api/v1/miembros", "POST", {
          codigo,
          nombre,
          rol,
          porcentaje_produccion: rol === "USUARIO" ? porcentajeProduccion : null,
        });
        setCredencial(alta.credencial);
        setMensaje("Miembro creado. Entrega la clave temporal de forma segura.");
      }
      setCodigo("");
      setNombre("");
      setRol("USUARIO");
      setPorcentajeProduccion("1.5");
      setMiembroEditando(null);
      recargar();
      recargarGestores();
    } catch (e) {
      setMensaje(e instanceof Error ? e.message : String(e));
    }
  };

  const restablecerMiembro = async (miembro: Miembro) => {
    setMensaje("");
    const nueva = await enviarJson<CredencialTemporal>(
      "/api/v1/miembros/" + miembro.id + "/restablecer-acceso",
      "POST",
    );
    setCredencial(nueva);
    setMensaje("Acceso restablecido. La nueva clave temporal se muestra una sola vez.");
  };

  const guardarGestor = async (e: FormEvent) => {
    e.preventDefault();
    setMensaje("");
    setCredencial(null);
    try {
      const datos = { codigo: codigoGestor, nombre: nombreGestor, usuario_id: usuarioId };
      if (gestorEditando) {
        await enviarJson<Gestor>("/api/v1/gestores/" + gestorEditando, "PATCH", {
          ...datos, porcentaje_comision: porcentajeGestor === "" ? null : porcentajeGestor,
        });
        setMensaje("Gestor actualizado.");
      } else {
        const alta = await enviarJson<AltaGestor>("/api/v1/gestores", "POST", datos);
        setCredencial(alta.credencial);
        setMensaje("Gestor creado y vinculado. Entrega la clave temporal de forma segura.");
      }
      setCodigoGestor("");
      setNombreGestor("");
      setPorcentajeGestor("");
      setGestorEditando(null);
      recargarGestores();
    } catch (e) {
      setMensaje(e instanceof Error ? e.message : String(e));
    }
  };

  const restablecerGestor = async (gestor: Gestor) => {
    const nueva = await enviarJson<CredencialTemporal>(
      "/api/v1/gestores/" + gestor.id + "/restablecer-acceso",
      "POST",
    );
    setCredencial(nueva);
    setMensaje("Acceso del Gestor restablecido.");
  };

  return (
    <>
      <h2>Organización</h2>
      <p className="tenue">
        Administración crea miembros y puede crear Gestores. Cada alta genera una clave temporal
        que debe cambiarse en el primer inicio de sesión.
      </p>
      <Credencial credencial={credencial} />
      {mensaje && <p className="tenue">{mensaje}</p>}
      {error && <p className="error">{error}</p>}
      {cargando && <p>Cargando…</p>}

      <section className="panel-configuracion">
        <h3>Asignación de Usuarios a Responsables</h3>
        <p className="tenue">La asignación se limita a esta Administración. No modifica los pagos históricos.</p>
        <table>
          <thead><tr><th>Usuario</th><th>Responsable asignado</th></tr></thead>
          <tbody>{usuarios.map((u) => (
            <tr key={u.id}>
              <td>{u.codigo} · {u.nombre}</td>
              <td><select value={u.responsable_id ?? ""} onChange={(e) => void asignarResponsable(u, e.target.value)}>
                <option value="">Sin asignar</option>
                {responsables.map((r) => <option key={r.id} value={r.id}>{r.codigo} · {r.nombre}</option>)}
              </select></td>
            </tr>
          ))}</tbody>
        </table>
      </section>
      <div className="columnas">
        <section>
          <h3>{miembroEditando ? "Editar miembro" : "Crear miembro"}</h3>
          <form onSubmit={guardarMiembro} className="formulario-linea">
            <input
              placeholder="Código automático (opcional, editable)"
              value={codigo}
              onChange={(e) => setCodigo(e.target.value.toUpperCase())}
            />
            <input placeholder="Nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
            <select
              value={rol}
              onChange={(e) => setRol(e.target.value as RolMiembro)}
            >
              {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
            {rol === "USUARIO" && (
              <label>
                % producción predeterminado
                <input
                  type="number"
                  step="0.0001"
                  min="0"
                  max="100"
                  value={porcentajeProduccion}
                  onChange={(e) => setPorcentajeProduccion(e.target.value)}
                  required
                />
              </label>
            )}
            <button type="submit">{miembroEditando ? "Guardar" : "Crear y generar clave"}</button>
            {miembroEditando && (
              <button type="button" onClick={() => {
                setMiembroEditando(null);
                setCodigo("");
                setNombre("");
                setRol("USUARIO");
                setPorcentajeProduccion("1.5");
              }}>Cancelar</button>
            )}
          </form>

          <h3>Miembros</h3>
          <table>
            <thead><tr><th>Código</th><th>Nombre</th><th>Rol</th><th>% producción</th><th>Acciones</th></tr></thead>
            <tbody>
              {miembros?.map((m) => (
                <tr key={m.id}>
                  <td>{m.codigo}</td><td>{m.nombre}</td><td>{m.rol}</td>
                  <td>{m.rol === "USUARIO" ? (m.porcentaje_produccion ?? "0") + "%" : "—"}</td>
                  <td>
                    <button type="button" onClick={() => {
                      setMiembroEditando(m.id);
                      setCodigo(m.codigo);
                      setNombre(m.nombre);
                      setRol(m.rol);
                      setPorcentajeProduccion(m.porcentaje_produccion ?? "1.5");
                    }}>Editar</button>{" "}
                    <button type="button" onClick={() => void restablecerMiembro(m)}>
                      Restablecer acceso
                    </button>
                  </td>
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
              {usuarios.map((u) => <option key={u.id} value={u.id}>{u.codigo} · {u.nombre}</option>)}
            </select>
            <input
              placeholder="Código automático (opcional, editable)"
              value={codigoGestor}
              onChange={(e) => setCodigoGestor(e.target.value.toUpperCase())}
            />
            <input
              placeholder="Nombre gestor"
              value={nombreGestor}
              onChange={(e) => setNombreGestor(e.target.value)}
              required
            />
            {gestorEditando && <label>Tasa Gestor (%)
              <input type="number" min="0" max="100" step="0.0001"
                placeholder="Porcentaje de comisión"
                value={porcentajeGestor}
                onChange={(e) => setPorcentajeGestor(e.target.value)} />
            </label>}
            <button type="submit">{gestorEditando ? "Guardar gestor" : "Crear y generar clave"}</button>
            {gestorEditando && (
              <button type="button" onClick={() => {
                setGestorEditando(null);
                setCodigoGestor("");
                setNombreGestor("");
              }}>Cancelar</button>
            )}
          </form>
          <TablaGestores
            gestores={gestores ?? []}
            usuarios={usuarios}
            alEditar={(g) => {
              setGestorEditando(g.id);
              setUsuarioId(g.usuario_id ?? "");
              setCodigoGestor(g.codigo);
              setNombreGestor(g.nombre);
              setPorcentajeGestor(g.porcentaje_comision ?? "");
            }}
            alRestablecer={(g) => void restablecerGestor(g)}
          />
        </section>
      </div>
    </>
  );
}

function OrganizacionUsuario({ sesion }: { sesion: SesionActual }) {
  const { datos: gestores, error, cargando, recargar } = useDatos<Gestor[]>("/api/v1/gestores");
  const [codigo, setCodigo] = useState("");
  const [nombre, setNombre] = useState("");
  const [editando, setEditando] = useState<string | null>(null);
  const [credencial, setCredencial] = useState<CredencialTemporal | null>(null);
  const [mensaje, setMensaje] = useState("");

  const guardar = async (e: FormEvent) => {
    e.preventDefault();
    if (!sesion.usuario_id) return;
    setCredencial(null);
    try {
      const datos = { codigo, nombre, usuario_id: sesion.usuario_id };
      if (editando) {
        await enviarJson<Gestor>("/api/v1/gestores/" + editando, "PATCH", datos);
        setMensaje("Gestor actualizado.");
      } else {
        const alta = await enviarJson<AltaGestor>("/api/v1/gestores", "POST", datos);
        setCredencial(alta.credencial);
        setMensaje("Gestor creado. Entrega la clave temporal de forma segura.");
      }
      setCodigo("");
      setNombre("");
      setEditando(null);
      recargar();
    } catch (e) {
      setMensaje(e instanceof Error ? e.message : String(e));
    }
  };

  const restablecer = async (g: Gestor) => {
    const nueva = await enviarJson<CredencialTemporal>(
      "/api/v1/gestores/" + g.id + "/restablecer-acceso",
      "POST",
    );
    setCredencial(nueva);
    setMensaje("Acceso del Gestor restablecido.");
  };

  return (
    <>
      <h2>Mis Gestores</h2>
      <p className="tenue">
        Usuario {sesion.codigo} · {sesion.nombre}. Los Gestores creados aquí quedan vinculados
        automáticamente a tu Usuario.
      </p>
      <Credencial credencial={credencial} />
      {mensaje && <p className="tenue">{mensaje}</p>}
      {error && <p className="error">{error}</p>}
      {cargando && <p>Cargando…</p>}
      <form onSubmit={guardar} className="formulario-linea">
        <input
          placeholder="Código / login gestor"
          value={codigo}
          onChange={(e) => setCodigo(e.target.value.toUpperCase())}
          required
        />
        <input placeholder="Nombre gestor" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
        <button type="submit">{editando ? "Guardar gestor" : "Crear Gestor"}</button>
        {editando && <button type="button" onClick={() => {
          setEditando(null);
          setCodigo("");
          setNombre("");
        }}>Cancelar</button>}
      </form>
      <TablaGestores
        gestores={gestores ?? []}
        usuarios={[]}
        alEditar={(g) => {
          setEditando(g.id);
          setCodigo(g.codigo);
          setNombre(g.nombre);
        }}
        alRestablecer={(g) => void restablecer(g)}
        ocultarUsuario
      />
    </>
  );
}

function Credencial({ credencial }: { credencial: CredencialTemporal | null }) {
  if (!credencial) return null;
  return (
    <div className="credencial-temporal">
      <strong>Credencial temporal — mostrar una sola vez</strong>
      <div>Usuario: <code>{credencial.login}</code></div>
      <div>Clave temporal: <code>{credencial.clave_temporal}</code></div>
      <small>El titular deberá cambiarla al iniciar sesión.</small>
    </div>
  );
}

function TablaGestores({
  gestores,
  usuarios,
  alEditar,
  alRestablecer,
  ocultarUsuario = false,
}: {
  gestores: Gestor[];
  usuarios: Miembro[];
  alEditar: (gestor: Gestor) => void;
  alRestablecer: (gestor: Gestor) => void;
  ocultarUsuario?: boolean;
}) {
  return (
    <>
      <h3>Gestores</h3>
      <table>
        <thead>
          <tr>
            <th>Gestor</th>
            <th>Comisión</th>
            {!ocultarUsuario && <th>Usuario</th>}
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {gestores.map((g) => {
            const usuario = usuarios.find((u) => u.id === g.usuario_id);
            return (
              <tr key={g.id}>
                <td>{g.codigo} · {g.nombre}</td>
                <td>{g.porcentaje_comision != null ? g.porcentaje_comision + "%" : "Sin configurar"}</td>
                {!ocultarUsuario && <td>{usuario ? usuario.codigo + " · " + usuario.nombre : "Sin usuario"}</td>}
                <td>
                  <button type="button" onClick={() => alEditar(g)}>Editar</button>{" "}
                  <button type="button" onClick={() => alRestablecer(g)}>Restablecer acceso</button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </>
  );
}
