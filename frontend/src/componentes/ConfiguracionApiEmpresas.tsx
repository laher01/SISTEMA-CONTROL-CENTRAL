import { useRef, useState } from "react";
import { enviarJson, obtener } from "../api";

type Config = {
  token_configurado: boolean;
  endpoints: Record<string, string>;
  permitidos: Record<string, string[]>;
};
const campos = [
  ["coactiva", "Deuda coactiva"], ["ssco", "SSCO"],
  ["domicilio", "Domicilio fiscal"], ["sunat", "Ficha RUC SUNAT"],
] as const;
const ruta = "/api/v1/empresas/consultas/configuracion";

export default function ConfiguracionApiEmpresas() {
  const ventana = useRef<HTMLDialogElement>(null);
  const [config, setConfig] = useState<Config>();
  const [token, setToken] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState("");
  const [guardado, setGuardado] = useState(false);

  const abrir = async () => {
    ventana.current?.showModal();
    setConfig(undefined);
    setToken("");
    setError("");
    setGuardado(false);
    setOcupado(true);
    try {
      setConfig(await obtener<Config>(ruta));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Configuración no disponible");
    } finally {
      setOcupado(false);
    }
  };

  const guardar = async () => {
    if (!config || ocupado) return;
    setError("");
    setGuardado(false);
    setOcupado(true);
    try {
      setConfig(await enviarJson<Config>(ruta, "PATCH", {
        endpoints: config.endpoints,
        api_token: token.trim() || null,
      }));
      setToken("");
      setGuardado(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo guardar");
    } finally {
      setOcupado(false);
    }
  };

  return <>
    <button type="button" onClick={() => void abrir()}>Configurar APIPERU</button>
    <dialog ref={ventana} aria-label="Configuración de APIPERU" onClose={() => setToken("")}>
      <h3>Configuración de APIPERU</h3>
      {error && <p role="alert">{error}</p>}
      {guardado && <p role="status">Configuración guardada.</p>}
      {config && <form onSubmit={ev => { ev.preventDefault(); void guardar(); }}>
        <fieldset disabled={ocupado}>
          <legend>Credencial y endpoints</legend>
          <label>API token
            <input type="password" autoComplete="new-password" maxLength={512}
              placeholder={config.token_configurado ? "••••••••" : "Ingresa el token"}
              value={token} onChange={ev => setToken(ev.target.value)} />
          </label>
          {config.token_configurado && <p>Deja el token en blanco para conservar el actual.</p>}
          {campos.map(([clave, titulo]) => <p key={clave}><label>{titulo}
            <select value={config.endpoints[clave]} onChange={ev => {
              const url = ev.target.value;
              setConfig({ ...config, endpoints: { ...config.endpoints, [clave]: url } });
            }}>
              {config.permitidos[clave]?.map(url => <option key={url} value={url}>{url}</option>)}
            </select>
          </label></p>)}
          <button type="submit">Guardar</button>
        </fieldset>
      </form>}
      <button type="button" disabled={ocupado} onClick={() => ventana.current?.close()}>Cerrar</button>
    </dialog>
  </>;
}
