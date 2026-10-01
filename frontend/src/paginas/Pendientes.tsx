import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { conParametros, enviarJson, urlArchivo, useDatos } from "../api";
import { Estado, Paginacion } from "../componentes";
import {
  ETIQUETA_ESTADO_DOCUMENTO,
  ETIQUETA_TIPO_DOCUMENTO,
  formatearFecha,
  formatearMonto,
  numeroComprobante,
} from "../formato";
import { TIPOS_DOCUMENTO, type Documento, type Expediente, type TipoDocumento } from "../tipos";

const POR_PAGINA = 50;
const ESTADOS_PENDIENTES = ["PENDIENTE_CLASIFICACION", "PENDIENTE_RELACION"] as const;

export default function Pendientes() {
  const [parametros, setParametros] = useSearchParams();
  const estado = parametros.get("estado") === "PENDIENTE_RELACION" ? "PENDIENTE_RELACION" : "PENDIENTE_CLASIFICACION";
  const pagina = Number(parametros.get("pagina") ?? "0");
  const { datos, error, cargando, recargar } = useDatos<Documento[]>(
    conParametros("/api/v1/documentos", {
      estado,
      limit: String(POR_PAGINA),
      offset: String(pagina * POR_PAGINA),
    }),
  );

  const cambiar = (siguienteEstado: string, siguientePagina: number) =>
    setParametros({ estado: siguienteEstado, pagina: String(siguientePagina) });

  return (
    <>
      <h2>Documentos pendientes</h2>
      <p className="tenue">
        Archivos que no se pudieron asociar solos (PDF, imágenes o guías sin factura). Indica su tipo
        y el expediente al que pertenecen.
      </p>
      <div className="filtros">
        <select value={estado} onChange={(e) => cambiar(e.target.value, 0)}>
          {ESTADOS_PENDIENTES.map((e) => (
            <option key={e} value={e}>
              {ETIQUETA_ESTADO_DOCUMENTO[e]}
            </option>
          ))}
        </select>
      </div>
      <Estado cargando={cargando} error={error} vacio={datos?.length === 0}>
        <table>
          <thead>
            <tr>
              <th>Archivo</th>
              <th>Subido</th>
              <th>Vincular</th>
            </tr>
          </thead>
          <tbody>
            {datos?.map((d) => (
              <tr key={d.id}>
                <td>
                  <a href={urlArchivo(d.id)} target="_blank" rel="noreferrer">
                    {d.nombre_original}
                  </a>
                </td>
                <td>{formatearFecha(d.created_at)}</td>
                <td>
                  <Vincular documento={d} alVincular={recargar} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Estado>
      <Paginacion
        pagina={pagina}
        hayMas={(datos?.length ?? 0) === POR_PAGINA}
        alCambiar={(p) => cambiar(estado, p)}
      />
    </>
  );
}

function Vincular({ documento, alVincular }: { documento: Documento; alVincular: () => void }) {
  const [tipo, setTipo] = useState<TipoDocumento>(documento.tipo_documento ?? "VCHR");
  const [buscar, setBuscar] = useState("");
  const [expedienteId, setExpedienteId] = useState("");
  const [error, setError] = useState("");
  const candidatos = useDatos<Expediente[]>(
    conParametros("/api/v1/expedientes", { buscar: buscar.trim(), limit: "20" }),
  );

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
      <input
        placeholder="Buscar F001-123, RUC o proveedor"
        value={buscar}
        maxLength={100}
        onChange={(e) => {
          setBuscar(e.target.value);
          setExpedienteId("");
        }}
      />
      <select value={expedienteId} onChange={(e) => setExpedienteId(e.target.value)}>
        <option value="">
          {candidatos.cargando ? "Buscando…" : `Elegir expediente (${candidatos.datos?.length ?? 0})`}
        </option>
        {candidatos.datos?.map((e) => (
          <option key={e.id} value={e.id}>
            {numeroComprobante(e.serie, e.correlativo)} · {e.emisor.razon_social} ·{" "}
            {formatearMonto(e.moneda, e.importe_total)}
          </option>
        ))}
      </select>
      <button disabled={!expedienteId} onClick={vincular}>
        Vincular
      </button>
      {(error || candidatos.error) && <span className="error">{error || candidatos.error}</span>}
    </div>
  );
}
