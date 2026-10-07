import { useState, type FormEvent } from "react";

import { enviarJson } from "../api";
import type { SesionActual } from "../tipos";

export function Login({ alIngresar }: { alIngresar: () => void }) {
  const [login, setLogin] = useState("");
  const [clave, setClave] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  const ingresar = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setEnviando(true);
    try {
      await enviarJson<SesionActual>("/api/v1/auth/login", "POST", { login, clave });
      alIngresar();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <main className="login-contenedor">
      <section className="login-tarjeta">
        <h1>FACT CENTRAL</h1>
        <p className="tenue">Ingresa con la cuenta asignada por Administración.</p>
        <form onSubmit={ingresar} className="login-formulario">
          <label>
            Usuario
            <input
              value={login}
              onChange={(e) => setLogin(e.target.value.toUpperCase())}
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
