import { useEffect, useState, type FormEvent } from "react";

import { conParametros, enviarFormulario, urlAdjuntoChat, useDatos } from "../api";

interface ContactoChat {
  cuenta_id: string;
  nombre: string;
  codigo: string;
  rol: string;
}

interface MensajeChat {
  id: string;
  remitente_cuenta_id: string;
  destinatario_cuenta_id: string;
  texto: string;
  archivo_nombre: string | null;
  archivo_tamano: number | null;
  created_at: string;
}

export default function Chat() {
  const { datos: contactos, cargando: cargandoContactos } = useDatos<ContactoChat[]>(
    "/api/v1/chat/contactos",
  );
  const [seleccionado, setSeleccionado] = useState("");
  const [texto, setTexto] = useState("");
  const [archivo, setArchivo] = useState<File | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [aviso, setAviso] = useState("");
  const rutaMensajes = seleccionado
    ? conParametros("/api/v1/chat/mensajes", { con: seleccionado })
    : "";
  const { datos: mensajes, cargando, recargar } = useDatos<MensajeChat[]>(rutaMensajes);

  useEffect(() => {
    if (!seleccionado) return;
    const intervalo = window.setInterval(() => recargar(), 15000);
    return () => window.clearInterval(intervalo);
  }, [seleccionado]);

  const enviar = async (evento: FormEvent) => {
    evento.preventDefault();
    if (!seleccionado || (!texto.trim() && !archivo)) return;
    setEnviando(true);
    setAviso("");
    const formulario = new FormData();
    formulario.append("destinatario_cuenta_id", seleccionado);
    formulario.append("texto", texto);
    if (archivo) formulario.append("archivo", archivo);
    try {
      await enviarFormulario<MensajeChat>("/api/v1/chat/mensajes", formulario);
      setTexto("");
      setArchivo(null);
      recargar();
    } catch (error) {
      setAviso(error instanceof Error ? error.message : String(error));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <>
      <div className="encabezado-pagina">
        <div>
          <h2>Chat interno</h2>
          <p className="tenue">Mensajes y adjuntos privados entre contactos autorizados.</p>
        </div>
      </div>
      <section className="panel-configuracion">
        <label>
          Contacto
          <select
            aria-label="Seleccionar contacto"
            value={seleccionado}
            onChange={(e) => setSeleccionado(e.target.value)}
          >
            <option value="">Seleccionar contacto</option>
            {(contactos ?? []).map((c) => (
              <option key={c.cuenta_id} value={c.cuenta_id}>
                {c.codigo} · {c.nombre} ({c.rol})
              </option>
            ))}
          </select>
        </label>
        {cargandoContactos && <p className="tenue">Buscando contactos…</p>}
        {contactos?.length === 0 && (
          <p className="tenue">No existen contactos autorizados para tu rol.</p>
        )}
        {seleccionado && (
          <>
            <div className="mensajes-chat" aria-live="polite">
              {cargando && <p className="tenue">Actualizando mensajes…</p>}
              {(mensajes ?? []).map((m) => (
                <article key={m.id} className="tarjeta">
                  <strong>
                    {m.remitente_cuenta_id === seleccionado ? "Contacto" : "Tú"}
                  </strong>
                  <small className="bloque tenue">
                    {new Date(m.created_at).toLocaleString("es-PE")}
                  </small>
                  {m.texto && <p>{m.texto}</p>}
                  {m.archivo_nombre && (
                    <a href={urlAdjuntoChat(m.id)}>
                      Descargar archivo: {m.archivo_nombre}
                    </a>
                  )}
                </article>
              ))}
            </div>
            <form onSubmit={(e) => void enviar(e)} className="formulario-linea">
              <textarea
                aria-label="Escribir mensaje"
                value={texto}
                maxLength={2000}
                rows={3}
                placeholder="Escribe un mensaje para este contacto"
                onChange={(e) => setTexto(e.target.value)}
              />
              <input
                aria-label="Adjuntar archivo"
                key={archivo ? archivo.name : "sin-archivo"}
                type="file"
                accept=".pdf,.xml,.jpg,.jpeg,.png,.webp,.txt"
                onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
              />
              <button disabled={enviando || (!texto.trim() && !archivo)}>
                {enviando ? "Enviando…" : "Enviar"}
              </button>
              <button type="button" className="secundario" onClick={recargar}>
                Actualizar conversación
              </button>
            </form>
            {aviso && <p className="error">{aviso}</p>}
          </>
        )}
      </section>
    </>
  );
}
