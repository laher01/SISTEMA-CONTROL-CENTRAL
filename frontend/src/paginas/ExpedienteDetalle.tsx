import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { enviarFormulario, urlArchivo, urlPdfExpediente, urlZipExpediente, useDatos } from "../api";
import { Estado, Semaforo } from "../componentes";
import {
  ETIQUETA_ALERTA,
  ETIQUETA_TIPO_DOCUMENTO,
  formatearFecha,
  formatearMonto,
  formatearTamano,
  numeroExpediente,
} from "../formato";
import { TIPOS_DOCUMENTO, type Documento, type ExpedienteDetalle as Detalle, type TipoDocumento } from "../tipos";

export default function ExpedienteDetalle() {
  const { id = "" } = useParams();
  const { datos, error, cargando, recargar } = useDatos<Detalle>(`/api/v1/expedientes/${id}`);

  return (
    <Estado cargando={cargando} error={error} vacio={!datos}>
      {datos && (
        <>
          <h2>
            {datos.tipo_comprobante === "RHE"
              ? numeroExpediente(datos.tipo_comprobante, datos.serie, datos.correlativo)
              : "FACT " + numeroExpediente(datos.tipo_comprobante, datos.serie, datos.correlativo)}{" "}
            <Semaforo estado={datos.estado} />
          </h2>
          <p><a className="boton-enlace" href={urlZipExpediente(datos.id)}>Descargar expediente completo (.zip)</a>{" · "}<a className="boton-enlace" href={urlPdfExpediente(datos.id)}>Descargar PDF ordenado</a></p>
          <dl className="ficha">
            <dt>Emisor</dt>
            <dd>
              {datos.emisor.razon_social} ({datos.emisor.ruc})
              {(!datos.emisor.clasificacion_proveedor || datos.emisor.tipo_relacion === "SIN_CLASIFICAR") && <span className="etiqueta">Sin clasificar · <Link to={`/empresas?pendientes=1&ruc=${datos.emisor.ruc}`}>Revisar empresa</Link></span>}
            </dd>
            <dt>Receptor</dt>
            <dd>
              {datos.receptor.razon_social} ({datos.receptor.ruc})
              {datos.pendiente_aprobacion && <span className="etiqueta">No autorizado</span>}
              {datos.receptor.tipo_relacion === "SIN_CLASIFICAR" && <span className="etiqueta">Sin clasificar · <Link to={`/empresas?pendientes=1&ruc=${datos.receptor.ruc}`}>Revisar empresa</Link></span>}
            </dd>
            <dt>Emisión</dt>
            <dd>{formatearFecha(datos.fecha_emision)}</dd>
            <dt>Fecha límite</dt>
            <dd>{formatearFecha(datos.fecha_limite)}</dd>
            <dt>Importe</dt>
            <dd>{formatearMonto(datos.moneda, datos.importe_total)}</dd>
            <dt>Faltan</dt>
            <dd>
              {datos.faltantes.length === 0
                ? "Nada"
                : datos.faltantes.map((t) => ETIQUETA_TIPO_DOCUMENTO[t]).join(", ")}
            </dd>
          </dl>

          <h3>Alertas</h3>
          {datos.alertas.filter((a) => !a.resuelta).length === 0 ? (
            <p className="tenue">Sin alertas abiertas.</p>
          ) : (
            <ul className="alertas">
              {datos.alertas
                .filter((a) => !a.resuelta)
                .map((a) => (
                  <li key={a.id}>
                    <strong>{ETIQUETA_ALERTA[a.tipo]}:</strong> {a.mensaje}
                  </li>
                ))}
            </ul>
          )}

          <h3>Documentos</h3>
          <TablaDocumentos documentos={datos.documentos} />
          <AgregarDocumento expedienteId={datos.id} sugerido={datos.faltantes[0]} alSubir={recargar} />
        </>
      )}
    </Estado>
  );
}

function TablaDocumentos({ documentos }: { documentos: Documento[] }) {
  if (documentos.length === 0) return <p className="tenue">Sin documentos.</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>Tipo</th>
          <th>Archivo</th>
          <th>Tamaño</th>
          <th>Subido</th>
        </tr>
      </thead>
      <tbody>
        {documentos.map((d) => (
          <tr key={d.id}>
            <td>{d.tipo_documento ? ETIQUETA_TIPO_DOCUMENTO[d.tipo_documento] : "Sin tipo"}</td>
            <td>
              <a href={urlArchivo(d.id)} target="_blank" rel="noreferrer">
                {d.nombre_original}
              </a>
            </td>
            <td>{formatearTamano(d.tamano_bytes)}</td>
            <td>{formatearFecha(d.created_at)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function AgregarDocumento({
  expedienteId,
  sugerido,
  alSubir,
}: {
  expedienteId: string;
  sugerido?: TipoDocumento;
  alSubir: () => void;
}) {
  const [tipo, setTipo] = useState<TipoDocumento | "">("");
  const [archivo, setArchivo] = useState<File | null>(null);
  const [mensaje, setMensaje] = useState("");
  const [enviando, setEnviando] = useState(false);
  const tipoElegido = tipo || sugerido || "VCHR";

  const enviar = async (evento: FormEvent) => {
    evento.preventDefault();
    if (!archivo) return;
    const formulario = new FormData();
    formulario.append("archivo", archivo);
    formulario.append("tipo_documento", tipoElegido);
    formulario.append("expediente_id", expedienteId);
    setEnviando(true);
    try {
      await enviarFormulario<Documento>("/api/v1/documentos", formulario);
      setMensaje("Documento agregado.");
      setArchivo(null);
      setTipo("");
      alSubir();
    } catch (error) {
      setMensaje(error instanceof Error ? error.message : String(error));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form className="formulario-linea" onSubmit={enviar}>
      <strong>Agregar documento:</strong>
      <select value={tipoElegido} onChange={(e) => setTipo(e.target.value as TipoDocumento)}>
        {TIPOS_DOCUMENTO.map((t) => (
          <option key={t} value={t}>
            {ETIQUETA_TIPO_DOCUMENTO[t]}
          </option>
        ))}
      </select>
      <input
        key={archivo ? "con" : "sin"}
        type="file"
        accept=".xml,.pdf,image/*"
        onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
      />
      <button type="submit" disabled={!archivo || enviando}>
        {enviando ? "Subiendo…" : "Subir"}
      </button>
      {mensaje && <span className="tenue">{mensaje}</span>}
    </form>
  );
}
