/** Editor CMS interno. No modifica la activación de la landing pública. */
import { useState } from "react";
import { enviarJson, useDatos } from "../api";
import type { ContenidoLanding } from "../contenidoLanding";
import { contenidoLandingInicial } from "../contenidoLanding";

type EstadoCms = {
  existe: boolean;
  version: number;
  estado: "borrador" | "vista_previa" | "aprobado" | "publicado";
  contenido: ContenidoLanding | null;
};
const CAMPOS = [
  "marca", "etiqueta", "titulo", "descripcion", "beneficiosTitulo",
  "planesTitulo", "planesDescripcion", "registroTitulo", "registroDescripcion",
] as const;

export default function PanelEditorCms() {
  const { datos, error, cargando, recargar } = useDatos<EstadoCms>("/api/v1/plataforma/cms");
  const [borrador, setBorrador] = useState<ContenidoLanding | null>(null);
  const contenido = borrador ?? datos?.contenido ?? contenidoLandingInicial;
  const [ocupado, setOcupado] = useState(false);
  const [mensaje, setMensaje] = useState("");
  async function ejecutar(url: string, metodo: "PUT" | "POST", payload: object) {
    setOcupado(true);
    setMensaje("");
    try {
      await enviarJson(url, metodo, payload);
      setBorrador(null);
      recargar();
      setMensaje("Cambio registrado y pendiente de las aprobaciones correspondientes.");
    } catch (e) {
      setMensaje(e instanceof Error ? e.message : String(e));
      recargar();
    } finally {
      setOcupado(false);
    }
  }
  const bloqueado = ocupado || cargando || !datos;
  return (
    <section className="panel-configuracion" aria-labelledby="cms-titulo">
      <h3 id="cms-titulo">CMS comercial — edición y aprobación</h3>
      <p className="tenue">Solo SUPERADMIN. La aprobación editorial no activa la landing pública.</p>
      {error && <p role="alert">{error}</p>}
      <p><strong>Estado:</strong> {datos?.estado ?? "Consultando"} · Versión: {datos?.version ?? "—"}</p>
      <fieldset disabled={bloqueado || datos?.estado !== "borrador"}>
        <legend>Contenido comercial</legend>
        {CAMPOS.map((campo) => (
          <label key={campo} className="bloque">
            {campo}
            <textarea
              aria-label={campo}
              value={contenido[campo]}
              onChange={(e) => setBorrador({ ...contenido, [campo]: e.target.value })}
            />
          </label>
        ))}
        {contenido.beneficios.map((beneficio, indice) => (
          <fieldset key={beneficio.id || indice}>
            <legend>Beneficio {indice + 1}</legend>
            {(["id", "titulo", "descripcion"] as const).map((campo) => (
              <label key={campo} className="bloque">
                {campo}
                <input
                  value={beneficio[campo]}
                  onChange={(e) => setBorrador({
                    ...contenido,
                    beneficios: contenido.beneficios.map((item, i) => i === indice
                      ? { ...item, [campo]: e.target.value } : item),
                  })}
                />
              </label>
            ))}
          </fieldset>
        ))}
        <button
          disabled={bloqueado || datos?.estado !== "borrador"}
          onClick={() => void ejecutar("/api/v1/plataforma/cms/borrador", "PUT", {
            version: datos?.version ?? 0, contenido,
          })}
        >Guardar borrador</button>
      </fieldset>
      <details>
        <summary>Vista previa interna (sin publicación)</summary>
        <h4>{contenido.titulo}</h4>
        <p>{contenido.descripcion}</p>
        <h4>{contenido.beneficiosTitulo}</h4>
        {contenido.beneficios.map((b) => <p key={b.id}><strong>{b.titulo}</strong>: {b.descripcion}</p>)}
        <p>{contenido.planesTitulo}: {contenido.planesDescripcion}</p>
        <p>{contenido.registroTitulo}: {contenido.registroDescripcion}</p>
      </details>
      <div className="panel-configuracion">
        {([
          ["borrador", "vista_previa", "Enviar a vista previa"],
          ["vista_previa", "aprobado", "Aprobar contenido"],
          ["aprobado", "publicado", "Marcar como publicado"],
          ["vista_previa", "borrador", "Devolver al borrador"],
          ["aprobado", "borrador", "Reabrir borrador"],
          ["publicado", "borrador", "Crear nueva revisión"],
        ] as const).filter(([origen]) => origen === datos?.estado).map(([, destino, etiqueta]) => (
          <button
            key={destino}
            disabled={bloqueado || !datos?.existe}
            onClick={() => void ejecutar("/api/v1/plataforma/cms/transicion", "POST", {
              version: datos?.version, destino,
            })}
          >{etiqueta}</button>
        ))}
      </div>
      {mensaje && <p role="status">{mensaje}</p>}
    </section>
  );
}
