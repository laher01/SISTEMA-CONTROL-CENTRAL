import { useMemo, useState, type FormEvent } from "react";
import { useLocation } from "react-router-dom";

import { enviarJson, useDatos } from "../api";
import type { NexusEstado, NexusRespuesta, SesionActual } from "../tipos";

interface Mensaje {
  autor: "usuario" | "nexus";
  texto: string;
  fuentes?: NexusRespuesta["fuentes"];
  internet?: boolean;
  configuracion?: boolean;
  motor?: string;
}

export default function NexusFlotante({ sesion }: { sesion: SesionActual }) {
  const location = useLocation();
  const { datos: estado } = useDatos<NexusEstado>("/api/v1/nexus/estado");
  const [abierto, setAbierto] = useState(false);
  const [texto, setTexto] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [mensajes, setMensajes] = useState<Mensaje[]>([
    {
      autor: "nexus",
      texto:
        "Soy NEXUS. Ahora trabajo con el contexto de la pantalla, tu rol, los datos autorizados de FACT CENTRAL y la base de conocimiento del proyecto.",
    },
  ]);

  const expedienteId = useMemo(() => {
    const coincidencia = location.pathname.match(/^\/expedientes\/([0-9a-f-]{36})$/i);
    return coincidencia?.[1] ?? null;
  }, [location.pathname]);

  const consultar = async (mensaje: string) => {
    const limpio = mensaje.trim();
    if (!limpio || ocupado) return;
    setMensajes((actual) => [...actual, { autor: "usuario", texto: limpio }]);
    setTexto("");
    setOcupado(true);
    try {
      const historial = mensajes.slice(-10).map((item) => ({
        autor: item.autor === "usuario" ? "usuario" : "nexus",
        texto: item.texto,
      }));
      const respuesta = await enviarJson<NexusRespuesta>("/api/v1/nexus/chat", "POST", {
        mensaje: limpio,
        ruta: location.pathname + location.search,
        expediente_id: expedienteId,
        historial,
      });
      setMensajes((actual) => [
        ...actual,
        {
          autor: "nexus",
          texto: respuesta.respuesta,
          fuentes: respuesta.fuentes,
          internet: respuesta.internet_usado,
          configuracion: respuesta.requiere_configuracion_externa,
          motor: respuesta.motor,
        },
      ]);
    } catch (error) {
      setMensajes((actual) => [
        ...actual,
        {
          autor: "nexus",
          texto: error instanceof Error ? error.message : String(error),
        },
      ]);
    } finally {
      setOcupado(false);
    }
  };

  const enviar = (e: FormEvent) => {
    e.preventDefault();
    void consultar(texto);
  };

  const acciones = useMemo(() => {
    if (expedienteId) {
      return [
        "¿Qué falta en este expediente?",
        "¿Ves alguna inconsistencia aquí?",
        "Explícame el estado de este expediente",
      ];
    }
    if (location.pathname.startsWith("/pagos")) {
      return [
        "¿Qué está pasando en Pagos?",
        "Explícame pedidos, cobros y liquidaciones",
        "¿Qué debería revisar en esta pantalla?",
      ];
    }
    if (location.pathname.startsWith("/empresas")) {
      return [
        "¿Qué diferencia hay entre Proveedores y Clientes?",
        "¿Qué debería revisar en estas empresas?",
        "Explícame Tipo A y Tipo B",
      ];
    }
    if (location.pathname.startsWith("/produccion")) {
      return [
        "¿Cómo va la producción este mes?",
        "¿Cómo se calcula la producción por Usuario y Gestor?",
        "¿Qué debería revisar aquí?",
      ];
    }
    if (location.pathname.startsWith("/documentos")) {
      return [
        "¿Qué documentos necesitan atención?",
        "¿Cómo funciona la extracción automática?",
        "¿Qué debería revisar aquí?",
      ];
    }
    if (location.pathname.startsWith("/organizacion")) {
      return [
        "Explícame la jerarquía actual",
        "¿Qué permisos tiene cada rol?",
        "¿Qué debería revisar aquí?",
      ];
    }
    return [
      "¿Cuánto llevo comprado este mes?",
      "¿Qué está pasando en esta pantalla?",
      "¿Qué puedes hacer aquí?",
    ];
  }, [expedienteId, location.pathname]);

  return (
    <>
      <button
        className={"nexus-boton-flotante" + (abierto ? " abierto" : "")}
        onClick={() => setAbierto((valor) => !valor)}
        aria-label="Abrir asistente NEXUS"
      >
        NEXUS
      </button>

      {abierto && (
        <section className="nexus-panel" aria-label="Asistente NEXUS">
          <header className="nexus-cabecera">
            <div>
              <strong>NEXUS</strong>
              <small>
                {sesion.codigo} · {sesion.rol}
              </small>
            </div>
            <button onClick={() => setAbierto(false)} aria-label="Cerrar NEXUS">×</button>
          </header>

          <div className="nexus-estado">
            <span className={estado?.asistente_activo ? "nexus-online" : "nexus-offline"}>
              Asistente {estado?.asistente_activo ? "activo" : "sin estado"}
            </span>
            <span>
              RUC externo: {estado?.consulta_ruc_externa ? "activo" : "pendiente"}
            </span>
            <span>
              Conversacional: {estado?.motor_conversacional ? "activo" : "contextual"}
            </span>
            <span>
              Knowledge Base: {estado?.knowledge_base ? "activa" : "pendiente"}
            </span>
            <span>
              Internet/SUNAT: {estado?.busqueda_internet ? "activo" : "pendiente"}
            </span>
          </div>

          <div className="nexus-contexto">
            Contexto: <strong>{expedienteId ? "Expediente actual" : location.pathname}</strong>
          </div>

          <div className="nexus-mensajes">
            {mensajes.map((mensaje, indice) => (
              <article
                key={indice}
                className={"nexus-mensaje " + (mensaje.autor === "usuario" ? "usuario" : "asistente")}
              >
                <p>{mensaje.texto}</p>
                {mensaje.motor && <small>Motor: {mensaje.motor}</small>}
                {mensaje.internet && <small>Consulta externa utilizada</small>}
                {mensaje.configuracion && (
                  <small>
                    La función externa está preparada, pero falta configurar el proveedor en el servidor.
                  </small>
                )}
                {mensaje.fuentes && mensaje.fuentes.length > 0 && (
                  <div className="nexus-fuentes">
                    {mensaje.fuentes.map((fuente, i) =>
                      fuente.url ? (
                        <a key={i} href={fuente.url} target="_blank" rel="noreferrer">
                          {fuente.titulo}
                        </a>
                      ) : (
                        <span key={i}>{fuente.titulo}</span>
                      ),
                    )}
                  </div>
                )}
              </article>
            ))}
            {ocupado && <article className="nexus-mensaje asistente"><p>Consultando…</p></article>}
          </div>

          <div className="nexus-rapidas">
            {acciones.map((accion) => (
              <button key={accion} onClick={() => void consultar(accion)} disabled={ocupado}>
                {accion}
              </button>
            ))}
          </div>

          <form className="nexus-formulario" onSubmit={enviar}>
            <textarea
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              placeholder="Pregúntale a NEXUS…"
              rows={2}
            />
            <button type="submit" disabled={ocupado || !texto.trim()}>
              Enviar
            </button>
          </form>
        </section>
      )}
    </>
  );
}
