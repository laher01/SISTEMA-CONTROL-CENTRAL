import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { conParametros, enviarJson, useDatos } from "../api";
import { Estado, Paginacion } from "../componentes";
import { ETIQUETA_ALERTA, formatearFecha } from "../formato";
import {
  TIPOS_ALERTA,
  type Alerta,
  type AlertaManual,
  type RegistroOpciones,
  type SesionActual,
} from "../tipos";

const POR_PAGINA = 50;

export default function Alertas({ sesion }: { sesion: SesionActual }) {
  const [parametros, setParametros] = useSearchParams();
  const tipo = parametros.get("tipo") ?? "";
  const resuelta = parametros.get("resuelta") ?? "false";
  const pagina = Number(parametros.get("pagina") ?? "0");

  const sistema = useDatos<Alerta[]>(
    conParametros("/api/v1/alertas", {
      tipo,
      resuelta,
      limit: String(POR_PAGINA),
      offset: String(pagina * POR_PAGINA),
    }),
  );
  const manuales = useDatos<AlertaManual[]>(
    conParametros("/api/v1/mensajes-alerta", {
      resuelta,
      limit: "100",
    }),
  );

  const cambiar = (clave: string, valor: string) => {
    const siguiente = new URLSearchParams(parametros);
    if (valor) siguiente.set(clave, valor);
    else siguiente.delete(clave);
    if (clave !== "pagina") siguiente.delete("pagina");
    setParametros(siguiente);
  };

  const puedeEnviar = sesion.rol === "SECRETARIA" || sesion.rol === "ADMINISTRADOR";

  return (
    <>
      <h2>Buzón de alertas</h2>
      <p className="tenue">
        Alertas automáticas del expediente y mensajes operativos entre Secretaría,
        Administración, Usuario y Gestor.
      </p>

      {puedeEnviar && <CrearAlerta alCrear={manuales.recargar} />}

      <div className="filtros">
        <select value={tipo} onChange={(e) => cambiar("tipo", e.target.value)}>
          <option value="">Todos los tipos automáticos</option>
          {TIPOS_ALERTA.map((t) => (
            <option key={t} value={t}>{ETIQUETA_ALERTA[t]}</option>
          ))}
        </select>
        <select value={resuelta} onChange={(e) => cambiar("resuelta", e.target.value)}>
          <option value="false">Abiertas</option>
          <option value="true">Resueltas</option>
        </select>
      </div>

      <h3>Mensajes</h3>
      <Estado
        cargando={manuales.cargando}
        error={manuales.error}
        vacio={manuales.datos?.length === 0}
      >
        <table>
          <thead>
            <tr>
              <th>Asunto</th>
              <th>Mensaje</th>
              <th>Emitido por</th>
              <th>Fecha</th>
              <th>Expediente</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {manuales.datos?.map((a) => (
              <tr key={a.id}>
                <td>{a.asunto}</td>
                <td>{a.mensaje}</td>
                <td>{a.creado_por_codigo} · {a.creado_por_rol}</td>
                <td>{formatearFecha(a.created_at)}</td>
                <td>
                  {a.expediente_id ? (
                    <Link to={"/expedientes/" + a.expediente_id}>Ver expediente</Link>
                  ) : "General"}
                </td>
                <td>
                  {!a.resuelta && (
                    <button
                      onClick={async () => {
                        await enviarJson<AlertaManual>(
                          "/api/v1/mensajes-alerta/" + a.id + "/resolver",
                          "PATCH",
                        );
                        manuales.recargar();
                      }}
                    >
                      Resolver
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Estado>

      <h3>Alertas automáticas</h3>
      <Estado cargando={sistema.cargando} error={sistema.error} vacio={sistema.datos?.length === 0}>
        <table>
          <thead>
            <tr>
              <th>Tipo</th>
              <th>Detalle</th>
              <th>Desde</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {sistema.datos?.map((a) => (
              <tr key={a.id}>
                <td>{ETIQUETA_ALERTA[a.tipo]}</td>
                <td>{a.mensaje}</td>
                <td>{formatearFecha(a.created_at)}</td>
                <td><Link to={"/expedientes/" + a.expediente_id}>Ver expediente</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Estado>

      <Paginacion
        pagina={pagina}
        hayMas={(sistema.datos?.length ?? 0) === POR_PAGINA}
        alCambiar={(p) => cambiar("pagina", String(p))}
      />
    </>
  );
}

function CrearAlerta({ alCrear }: { alCrear: () => void }) {
  const { datos: opciones } = useDatos<RegistroOpciones>("/api/v1/registros/opciones");
  const [usuarioId, setUsuarioId] = useState("");
  const [gestorId, setGestorId] = useState("");
  const [expedienteId, setExpedienteId] = useState("");
  const [asunto, setAsunto] = useState("");
  const [mensaje, setMensaje] = useState("");
  const [paraAdministracion, setParaAdministracion] = useState(true);
  const [estado, setEstado] = useState("");

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    setEstado("");
    try {
      await enviarJson<AlertaManual>("/api/v1/mensajes-alerta", "POST", {
        expediente_id: expedienteId || null,
        destinatario_usuario_id: usuarioId || null,
        destinatario_gestor_id: gestorId || null,
        para_administracion: paraAdministracion,
        asunto,
        mensaje,
      });
      setAsunto("");
      setMensaje("");
      setExpedienteId("");
      setUsuarioId("");
      setGestorId("");
      setEstado("Alerta enviada.");
      alCrear();
    } catch (err) {
      setEstado(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <details className="panel-alerta">
      <summary>Enviar alerta o mensaje</summary>
      <form onSubmit={enviar} className="formulario-alerta">
        <select value={usuarioId} onChange={(e) => setUsuarioId(e.target.value)}>
          <option value="">Usuario: automático o general</option>
          {opciones?.usuarios.map((u) => (
            <option key={u.id} value={u.id}>{u.codigo} · {u.nombre}</option>
          ))}
        </select>
        <select value={gestorId} onChange={(e) => setGestorId(e.target.value)}>
          <option value="">Gestor: automático o ninguno</option>
          {opciones?.gestores.map((g) => (
            <option key={g.id} value={g.id}>{g.codigo} · {g.nombre}</option>
          ))}
        </select>
        <input
          placeholder="UUID expediente (opcional)"
          value={expedienteId}
          onChange={(e) => setExpedienteId(e.target.value)}
        />
        <input
          placeholder="Asunto"
          value={asunto}
          onChange={(e) => setAsunto(e.target.value)}
          required
        />
        <textarea
          placeholder="Mensaje"
          value={mensaje}
          onChange={(e) => setMensaje(e.target.value)}
          required
        />
        <label>
          <input
            type="checkbox"
            checked={paraAdministracion}
            onChange={(e) => setParaAdministracion(e.target.checked)}
          />
          Copia visible para Administración
        </label>
        <button type="submit">Enviar alerta</button>
        {estado && <small className="bloque">{estado}</small>}
      </form>
    </details>
  );
}
