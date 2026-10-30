import { useState } from "react";
import { Link } from "react-router-dom";

import { enviarJson, useDatos } from "../api";
import type { Expediente } from "../tipos";

interface SolicitudMISD {
  id: string;
  expediente_id: string;
  estado: "PENDIENTE" | "APROBADA" | "RECHAZADA" | "EJECUTADA" | string;
  rol_solicitante: string;
  motivo: string;
  es_solicitante: boolean;
}

export default function AprobacionesMISD({ rol }: { rol: "ADMINISTRADOR" | "RESPONSABLE" }) {
  const { datos, error, cargando, recargar } = useDatos<SolicitudMISD[]>(
    "/api/v1/misd/solicitudes",
  );

  return (
    <>
      <h2>{rol === "ADMINISTRADOR" ? "Aprobaciones MISD" : "Mis solicitudes MISD"}</h2>
      <p>
        {rol === "ADMINISTRADOR"
          ? "Revisa solicitudes de Responsables. Al aprobar, el Responsable solicitante ejecuta el retiro definitivo."
          : "Consulta el estado de tus solicitudes. Después de la aprobación de Administración, tú ejecutas el retiro definitivo."}
      </p>
      <p className="tenue">
        {rol === "ADMINISTRADOR"
          ? "Solo Administración puede aprobar o rechazar solicitudes."
          : "No se elimina ningún archivo hasta que Administración apruebe y tú confirmes la ejecución."}
      </p>
      {error && <p role="alert" className="error">{error}</p>}
      {cargando && <p>Cargando solicitudes…</p>}
      {!cargando && !error && (datos?.length ?? 0) === 0 && (
        <p>No tienes solicitudes MISD visibles.</p>
      )}
      {(datos?.length ?? 0) > 0 && (
        <table>
          <thead>
            <tr>
              <th>Expediente</th>
              <th>Solicitó</th>
              <th>Motivo</th>
              <th>Estado</th>
              <th>Decisión</th>
            </tr>
          </thead>
          <tbody>
            {datos?.map((solicitud) => (
              <FilaSolicitud
                key={solicitud.id}
                solicitud={solicitud}
                rol={rol}
                alResolver={recargar}
              />
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

function FilaSolicitud({
  solicitud,
  rol,
  alResolver,
}: {
  solicitud: SolicitudMISD;
  rol: "ADMINISTRADOR" | "RESPONSABLE";
  alResolver: () => void;
}) {
  const { datos: expediente, cargando } = useDatos<Expediente>(
    `/api/v1/expedientes/${solicitud.expediente_id}`,
  );
  const [procesando, setProcesando] = useState(false);
  const [error, setError] = useState("");
  const [mensaje, setMensaje] = useState("");

  const ejecutarRetiro = async () => {
    if (!window.confirm("El retiro definitivo eliminará el expediente y todos sus documentos vinculados. ¿Confirmas?")) return;
    setProcesando(true);
    setError("");
    setMensaje("");
    try {
      const resultado = await enviarJson<{ documentos_eliminados?: number; archivos_eliminados?: number; archivos_pendientes?: number }>(
        `/api/v1/misd/solicitudes/${solicitud.id}/ejecutar`,
        "POST",
      );
      alResolver();
      setMensaje(
        `Retiro ejecutado: ${resultado.documentos_eliminados ?? 0} documento(s), ${resultado.archivos_eliminados ?? 0} archivo(s) borrados físicamente.` +
        ((resultado.archivos_pendientes ?? 0) > 0 ? ` ${resultado.archivos_pendientes} archivo(s) quedaron pendientes de limpieza.` : ""),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setProcesando(false);
    }
  };

  const resolver = async (aprobar: boolean) => {
    const motivo = window.prompt(
      aprobar ? "Motivo de aprobación (mínimo 8 caracteres):" : "Motivo del rechazo (mínimo 8 caracteres):",
    );
    if (motivo === null) return;
    if (motivo.trim().length < 8) {
      setError("Escribe un motivo de al menos 8 caracteres.");
      return;
    }
    const accion = aprobar ? "aprobar" : "rechazar";
    if (!window.confirm(`¿Confirmas ${accion} esta solicitud MISD?`)) return;

    setProcesando(true);
    setError("");
    try {
      await enviarJson(
        `/api/v1/misd/solicitudes/${solicitud.id}/resolver`,
        "POST",
        { aprobar, motivo: motivo.trim() },
      );
      alResolver();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setProcesando(false);
    }
  };

  const comprobante = expediente
    ? `${expediente.serie}-${expediente.correlativo}`
    : solicitud.expediente_id;

  return (
    <tr>
      <td>
        {cargando ? "Cargando…" : expediente ? (
          <>
            <Link to={`/expedientes/${expediente.id}`}>{comprobante}</Link>
            <div>{expediente.emisor.razon_social}</div>
            <small>
              {expediente.moneda} {expediente.importe_total} · {expediente.receptor.razon_social}
            </small>
          </>
        ) : comprobante}
      </td>
      <td>{solicitud.rol_solicitante}</td>
      <td>{solicitud.motivo}</td>
      <td>{solicitud.estado}</td>
      <td>
        {rol === "ADMINISTRADOR" && solicitud.estado === "PENDIENTE" ? (
          <>
            <button disabled={procesando} onClick={() => void resolver(true)}>
              Aprobar
            </button>{" "}
            <button className="peligro" disabled={procesando} onClick={() => void resolver(false)}>
              Rechazar
            </button>
          </>
        ) : rol === "RESPONSABLE" && solicitud.estado === "APROBADA" && solicitud.es_solicitante ? (
          <button className="peligro" disabled={procesando} onClick={() => void ejecutarRetiro()}>
            Ejecutar retiro definitivo
          </button>
        ) : solicitud.estado === "EJECUTADA" ? "Ejecutada"
          : solicitud.estado === "RECHAZADA" ? "Rechazada"
            : solicitud.estado === "PENDIENTE" && solicitud.es_solicitante ? "Esperando aprobación"
              : "Resuelta"}
        {error && <small role="alert" className="error bloque">{error}</small>}
        {mensaje && <small role="status" className="bloque">{mensaje}</small>}
      </td>
    </tr>
  );
}
