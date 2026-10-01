import { useState } from "react";

import { enviarJson, urlArchivo, useDatos } from "../api";
import { Estado } from "../componentes";
import {
  ETIQUETA_ESTADO_DOCUMENTO,
  ETIQUETA_TIPO_DOCUMENTO,
  formatearFecha,
  formatearMonto,
  numeroComprobante,
} from "../formato";
import { TIPOS_DOCUMENTO, type Documento, type Expediente, type TipoDocumento } from "../tipos";

export default function Pendientes() {
  const clasificacion = useDatos<Documento[]>(
    "/api/v1/documentos?estado=PENDIENTE_CLASIFICACION&limit=500",
  );
  const relacion = useDatos<Documento[]>("/api/v1/documentos?estado=PENDIENTE_RELACION&limit=500");
  const expedientes = useDatos<Expediente[]>("/api/v1/expedientes?limit=500");

  const documentos = [...(clasificacion.datos ?? []), ...(relacion.datos ?? [])];
  const recargar = () => {
    clasificacion.recargar();
    relacion.recargar();
  };

  return (
    <>
      <h2>Documentos pendientes</h2>
      <p className="tenue">
        Archivos que no se pudieron asociar solos (PDF, imágenes o guías sin factura). Indica su tipo
        y el expediente al que pertenecen.
      </p>
      <Estado
        cargando={clasificacion.cargando || relacion.cargando}
        error={clasificacion.error ?? relacion.error ?? expedientes.error}
        vacio={documentos.length === 0}
      >
        <table>
          <thead>
            <tr>
              <th>Archivo</th>
              <th>Estado</th>
              <th>Subido</th>
              <th>Vincular</th>
            </tr>
          </thead>
          <tbody>
            {documentos.map((d) => (
              <tr key={d.id}>
                <td>
                  <a href={urlArchivo(d.id)} target="_blank" rel="noreferrer">
                    {d.nombre_original}
                  </a>
                </td>
                <td>{ETIQUETA_ESTADO_DOCUMENTO[d.estado]}</td>
                <td>{formatearFecha(d.created_at)}</td>
                <td>
                  <Vincular documento={d} expedientes={expedientes.datos ?? []} alVincular={recargar} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Estado>
    </>
  );
}

function Vincular({
  documento,
  expedientes,
  alVincular,
}: {
  documento: Documento;
  expedientes: Expediente[];
  alVincular: () => void;
}) {
  const [tipo, setTipo] = useState<TipoDocumento>(documento.tipo_documento ?? "VCHR");
  const [expedienteId, setExpedienteId] = useState("");
  const [error, setError] = useState("");

  const vincular = async () => {
    setError("");
    try {
      await enviarJson(`/api/v1/documentos/${documento.id}/vincular`, "POST", {
        expediente_id: expedienteId,
        tipo_documento: tipo,
      });
      alVincular();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <div className="formulario-linea">
      <select value={tipo} onChange={(e) => setTipo(e.target.value as TipoDocumento)}>
        {TIPOS_DOCUMENTO.map((t) => (
          <option key={t} value={t}>
            {ETIQUETA_TIPO_DOCUMENTO[t]}
          </option>
        ))}
      </select>
      <select value={expedienteId} onChange={(e) => setExpedienteId(e.target.value)}>
        <option value="">Elegir expediente…</option>
        {expedientes.map((e) => (
          <option key={e.id} value={e.id}>
            {numeroComprobante(e.serie, e.correlativo)} · {e.emisor.razon_social} ·{" "}
            {formatearMonto(e.moneda, e.importe_total)}
          </option>
        ))}
      </select>
      <button disabled={!expedienteId} onClick={vincular}>
        Vincular
      </button>
      {error && <span className="error">{error}</span>}
    </div>
  );
}
