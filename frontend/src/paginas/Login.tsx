import { useState, type FormEvent } from "react";

import { enviarJson, useDatos } from "../api";
import type { SesionActual } from "../tipos";

export function Login({ alIngresar }: { alIngresar: () => void }) {
  const [espacio, setEspacio] = useState("");
  const [login, setLogin] = useState("");
  const [clave, setClave] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [solicitar, setSolicitar] = useState(false);
  const [correo, setCorreo] = useState("");
  const [nombre, setNombre] = useState("");
  const [codigo, setCodigo] = useState("");
  const [mensajeSolicitud, setMensajeSolicitud] = useState("");
  const { datos: administracion } = useDatos<{ por_subdominio: boolean; nombre: string; codigo: string }>("/api/v1/auth/administracion-publica");
  const { datos: accesoPublico } = useDatos<{ registro_publico: boolean }>(
    "/api/v1/auth/acceso-publico",
  );

  const ingresar = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setEnviando(true);
    try {
      await enviarJson<SesionActual>("/api/v1/auth/login", "POST", { espacio: administracion?.por_subdominio ? null : espacio.trim() || null, login, clave });
      alIngresar();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setEnviando(false);
    }
  };


  const enviarSolicitud = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setMensajeSolicitud("");
    try {
      await enviarJson("/api/v1/auth/solicitar-acceso", "POST", {
        email: correo,
        nombre,
        codigo_solicitado: codigo,
      });
      setMensajeSolicitud("Solicitud enviada. Debe ser aprobada por SUPERADMIN.");
      setCorreo("");
      setNombre("");
      setCodigo("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <main className="login-contenedor">
      <section className="login-tarjeta">
        <h1>FACT CENTRAL</h1>
        <p className="tenue">{administracion?.por_subdominio ? `Administración: ${administracion.nombre}` : "Ingresa con la cuenta asignada por Administración."}</p>
        <form onSubmit={ingresar} className="login-formulario">
          {!administracion?.por_subdominio && <label>
            Espacio administrativo
            <input value={espacio} onChange={(e) => setEspacio(e.target.value)} placeholder="Código o nombre de Administración" autoComplete="organization" />
          </label>}
          <label>
            Usuario o correo
            <input
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              autoComplete="username"
              required
            />
          </label>
          <label>
            Clave
            <input
              type="password"
              value={clave}
              onChange={(e) => setClave(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          <button type="submit" disabled={enviando}>
            {enviando ? "Ingresando…" : "Iniciar sesión"}
          </button>
          {error && <p className="error">{error}</p>}
        </form>

        {accesoPublico?.registro_publico && (
          <button
            type="button"
            className="enlace-boton"
            onClick={() => setSolicitar((v) => !v)}
          >
            {solicitar ? "Volver al inicio de sesión" : "Solicitar acceso"}
          </button>
        )}

        {accesoPublico?.registro_publico && solicitar && (
          <form onSubmit={enviarSolicitud} className="login-formulario">
            <h3>Solicitar acceso</h3>
            <input
              type="text"
              placeholder="Nombre completo"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              required
            />
            <input
              type="email"
              placeholder="Correo autorizado"
              value={correo}
              onChange={(e) => setCorreo(e.target.value)}
              required
            />
            <input
              type="text"
              placeholder="Código solicitado, por ejemplo LUIS01"
              value={codigo}
              onChange={(e) => setCodigo(e.target.value.toUpperCase())}
              required
            />
            <button type="submit">Enviar solicitud</button>
            {mensajeSolicitud && <p>{mensajeSolicitud}</p>}
          </form>
        )}
      </section>
    </main>
  );
}

export function CambiarClave({
  sesion,
  alCambiar,
}: {
  sesion: SesionActual;
  alCambiar: () => void;
}) {
  const [actual, setActual] = useState("");
  const [nueva, setNueva] = useState("");
  const [repetir, setRepetir] = useState("");
  const [error, setError] = useState("");

  const cambiar = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (nueva !== repetir) {
      setError("Las claves nuevas no coinciden");
      return;
    }
    try {
      await enviarJson<SesionActual>("/api/v1/auth/cambiar-clave", "POST", {
        clave_actual: actual,
        clave_nueva: nueva,
      });
      alCambiar();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <main className="login-contenedor">
      <section className="login-tarjeta">
        <h2>Cambiar clave temporal</h2>
        <p>
          {sesion.codigo} · {sesion.nombre}
        </p>
        <p className="tenue">
          Por seguridad debes reemplazar la clave temporal antes de usar FACT CENTRAL.
        </p>
        <form onSubmit={cambiar} className="login-formulario">
          <input
            type="password"
            placeholder="Clave temporal"
            value={actual}
            onChange={(e) => setActual(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Nueva clave"
            value={nueva}
            onChange={(e) => setNueva(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Repetir nueva clave"
            value={repetir}
            onChange={(e) => setRepetir(e.target.value)}
            required
          />
          <button type="submit">Guardar nueva clave</button>
          {error && <p className="error">{error}</p>}
        </form>
      </section>
    </main>
  );
}
