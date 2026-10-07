import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { conParametros, eliminar, enviarJson, urlArchivo, useDatos } from "../api";
import { Estado, Paginacion } from "../componentes";
import {
  ETIQUETA_ESTADO_DOCUMENTO,
  ETIQUETA_TIPO_DOCUMENTO,
  formatearFecha,
} from "../formato";
import {
  ESTADOS_DOCUMENTO,
  TIPOS_DOCUMENTO,
  type Documento,
  type EstadoDocumento,
  type TipoDocumento,
} from "../tipos";

const POR_PAGINA = 50;

export default function Documentos() {
  const [parametros, setParametros] = useSearchParams();
  const estado = parametros.get("estado") ?? "";
  const tipo = parametros.get("tipo_documento") ?? "";
  const emisor = parametros.get("emisor_ruc") ?? "";
  const receptor = parametros.get("receptor_ruc") ?? "";
  const desde = parametros.get("fecha_desde") ?? "";
  const hasta = parametros.get("fecha_hasta") ?? "";
  const pagina = Number(parametros.get("pagina") ?? "0");

  const ruta = conParametros("/api/v1/documentos", {
    estado,
    tipo_documento: tipo,
    emisor_ruc: emisor.length === 11 ? emisor : undefined,
    receptor_ruc: receptor.length === 11 ? receptor : undefined,
    fecha_desde: desde,
    fecha_hasta: hasta,
    limit: String(POR_PAGINA),
    offset: String(pagina * POR_PAGINA),
  });
  const { datos, error, cargando, recargar } = useDatos<Documento[]>(ruta);

  const cambiar = (clave: string, valor: string) => {
    const siguiente = new URLSearchParams(parametros);
    if (valor) siguiente.set(clave, valor);
    else siguiente.delete(clave);
    if (clave !== "pagina") siguiente.delete("pagina");
    setParametros(siguiente);
  };

  const limpiar = () => setParametros({});

  return (
    <>
      <div className="encabezado-pagina">
        <div>
          <h2>Documentos</h2>
          <p className="tenue">
            Bandeja central para revisar, filtrar, reprocesar y retirar documentos sin perder trazabilidad.
          </p>
        </div>
        <Link className="boton-enlace" to="/subir">Subir documentos</Link>
      </div>

      <div className="filtros filtros-documentos">
        <select value={estado} onChange={(e) => cambiar("estado", e.target.value)}>
          <option value="">Todos los estados</option>
          {ESTADOS_DOCUMENTO.map((e) => (
            <option key={e} value={e}>{ETIQUETA_ESTADO_DOCUMENTO[e]}</option>
          ))}
        </select>

        <select value={tipo} onChange={(e) => cambiar("tipo_documento", e.target.value)}>
          <option value="">Todos los tipos</option>
          {TIPOS_DOCUMENTO.map((t) => (
            <option key={t} value={t}>{ETIQUETA_TIPO_DOCUMENTO[t]}</option>
          ))}
        </select>

        <input
          aria-label="RUC emisor"
          placeholder="RUC emisor"
          value={emisor}
          maxLength={11}
          onChange={(e) => cambiar("emisor_ruc", e.target.value.replace(/\D/g, ""))}
        />
        <input
          aria-label="RUC receptor"
          placeholder="RUC receptor"
          value={receptor}
          maxLength={11}
          onChange={(e) => cambiar("receptor_ruc", e.target.value.replace(/\D/g, ""))}
        />
        <label className="filtro-fecha">
          Desde
          <input type="date" value={desde} onChange={(e) => cambiar("fecha_desde", e.target.value)} />
        </label>
        <label className="filtro-fecha">
          Hasta
          <input type="date" value={hasta} onChange={(e) => cambiar("fecha_hasta", e.target.value)} />
        </label>
        <button className="secundario" onClick={limpiar}>Limpiar filtros</button>
      </div>

      <Estado cargando={cargando} error={error} vacio={datos?.length === 0}>
        <div className="tabla-responsive">
          <table>
            <thead>
              <tr>
                <th>Estado</th>
                <th>Archivo</th>
                <th>Tipo</th>
                <th>Subido</th>
                <th>Lectura</th>
                <th>Expediente</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {datos?.map((documento) => (
                <FilaDocumento key={documento.id} documento={documento} alCambiar={recargar} />
              ))}
            </tbody>
          </table>
        </div>
      </Estado>

      <Paginacion
        pagina={pagina}
        hayMas={(datos?.length ?? 0) === POR_PAGINA}
        alCambiar={(p) => cambiar("pagina", String(p))}
      />
    </>
  );
}

function FilaDocumento({
  documento,
  alCambiar,
}: {
  documento: Documento;
  alCambiar: () => void;
}) {
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState("");
  const lectura = resumenLectura(documento);

  const reprocesar = async () => {
    setOcupado(true);
    setError("");
    try {
      await enviarJson<Documento>(`/api/v1/documentos/${documento.id}/procesar`, "POST");
      alCambiar();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setOcupado(false);
    }
  };

  const retirar = async () => {
    const confirmado = window.confirm(
      `¿Retirar "${documento.nombre_original}" de FACT CENTRAL? La acción quedará auditada.`,
    );
    if (!confirmado) return;
    setOcupado(true);
    setError("");
    try {
      await eliminar(`/api/v1/documentos/${documento.id}`);
      alCambiar();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setOcupado(false);
    }
  };

  return (
    <tr>
      <td>
        <span className={`estado-documento estado-${documento.estado.toLowerCase()}`}>
          {ETIQUETA_ESTADO_DOCUMENTO[documento.estado as EstadoDocumento]}
        </span>
      </td>
      <td>
        <a href={urlArchivo(documento.id)} target="_blank" rel="noreferrer">
          {documento.nombre_original}
        </a>
        {error && <small className="error bloque">{error}</small>}
      </td>
      <td>
        {documento.tipo_documento
          ? ETIQUETA_TIPO_DOCUMENTO[documento.tipo_documento as TipoDocumento]
          : "Sin clasificar"}
      </td>
      <td>{formatearFecha(documento.created_at)}</td>
      <td>
        {lectura ? (
          <span title={lectura.detalle}>{lectura.texto}</span>
        ) : (
          <span className="tenue">Sin lectura</span>
        )}
      </td>
      <td>
        {documento.expediente_id ? (
          <Link to={`/expedientes/${documento.expediente_id}`}>Ver expediente</Link>
        ) : (
          <Link to={`/pendientes?estado=${documento.estado}`}>Revisar</Link>
        )}
      </td>
      <td>
        <div className="acciones-documento">
          {documento.estado !== "RELACIONADO" && (
            <button disabled={ocupado} onClick={reprocesar}>Reprocesar</button>
          )}
          <button className="peligro" disabled={ocupado} onClick={retirar}>Eliminar</button>
        </div>
      </td>
    </tr>
  );
}

function resumenLectura(documento: Documento): { texto: string; detalle: string } | undefined {
  const datos = documento.datos_extraidos;
  if (!datos || typeof datos !== "object") return undefined;
  const proceso = datos.procesamiento_documental;
  if (!proceso || typeof proceso !== "object") return undefined;

  const metodo = "metodo" in proceso ? String(proceso.metodo) : "Procesado";
  const confianza =
    "confianza" in proceso && typeof proceso.confianza === "number"
      ? ` · ${Math.round(proceso.confianza * 100)} %`
      : "";
  const motor = "motor" in proceso ? String(proceso.motor) : "";
  return { texto: `${metodo}${confianza}`, detalle: motor };
}
