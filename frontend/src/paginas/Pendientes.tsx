import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { conParametros, enviarJson, obtener, urlArchivo, useDatos } from "../api";
import { Estado, Paginacion } from "../componentes";
import {
  ETIQUETA_ESTADO_DOCUMENTO,
  ETIQUETA_TIPO_DOCUMENTO,
  formatearFecha,
  formatearMonto,
  numeroComprobante,
} from "../formato";
import {
  TIPOS_DOCUMENTO,
  type Documento,
  type Expediente,
  type RelacionSugerida,
  type TipoDocumento,
} from "../tipos";

const POR_PAGINA = 50;
const ESTADOS_PENDIENTES = ["PENDIENTE_CLASIFICACION", "PENDIENTE_RELACION"] as const;
type SeleccionSugerida = { expediente: Expediente; tipo?: TipoDocumento };
type CampoExtraido = {
  nombre: string;
  valor: string;
  confianza: number;
  fuente: string;
  evidencia: string;
};

const ETIQUETAS_CAMPOS: Record<string, string> = {
  serie: "Serie",
  correlativo: "Correlativo",
  ruc_emisor: "RUC emisor",
  ruc_receptor: "RUC receptor",
  fecha_emision: "Fecha de emisión",
  moneda: "Moneda",
  importe_total: "Importe total",
  numero_operacion: "N.º de operación",
};

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
              <th>Lectura</th>
              <th>Vincular</th>
            </tr>
          </thead>
          <tbody>
            {datos?.map((d) => <FilaPendiente key={d.id} documento={d} alVincular={recargar} />)}
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

function FilaPendiente({
  documento,
  alVincular,
}: {
  documento: Documento;
  alVincular: () => void;
}) {
  const [seleccion, setSeleccion] = useState<SeleccionSugerida>();
  return (
    <tr>
      <td>
        <a href={urlArchivo(documento.id)} target="_blank" rel="noreferrer">
          {documento.nombre_original}
        </a>
      </td>
      <td>{formatearFecha(documento.created_at)}</td>
      <td>
        <Procesar documento={documento} alSeleccionar={setSeleccion} />
      </td>
      <td>
        <Vincular
          key={`${documento.id}:${seleccion?.expediente.id ?? "manual"}:${seleccion?.tipo ?? ""}`}
          documento={documento}
          seleccion={seleccion}
          alVincular={alVincular}
        />
      </td>
    </tr>
  );
}

function Procesar({
  documento,
  alSeleccionar,
}: {
  documento: Documento;
  alSeleccionar: (seleccion: SeleccionSugerida) => void;
}) {
  const [resultado, setResultado] = useState<Documento>(documento);
  const [procesando, setProcesando] = useState(false);
  const [error, setError] = useState("");
  const [relaciones, setRelaciones] = useState<RelacionSugerida[]>([]);
  const lectura = obtenerLectura(resultado);

  const buscarRelaciones = async () => {
    const candidatas = await obtener<RelacionSugerida[]>(
      `/api/v1/documentos/${documento.id}/relaciones-sugeridas`,
    );
    setRelaciones(candidatas);
  };

  const procesar = async () => {
    setProcesando(true);
    setError("");
    try {
      const actualizado = await enviarJson<Documento>(
        `/api/v1/documentos/${documento.id}/procesar`,
        "POST",
      );
      setResultado(actualizado);
      await buscarRelaciones();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setProcesando(false);
    }
  };

  if (lectura) {
    return (
      <div className="formulario-linea">
        <span>
          {lectura.metodo}
          {lectura.confianza !== undefined
            ? ` · ${Math.round(lectura.confianza * 100)} %`
            : ""}
          {lectura.tipoSugerido ? ` · Sugiere ${ETIQUETA_TIPO_DOCUMENTO[lectura.tipoSugerido]}` : ""}
          {lectura.requiereOcr ? " · Requiere OCR" : ""}
        </span>
        {lectura.texto && (
          <details>
            <summary>Ver texto extraído</summary>
            <pre className="texto-extraido">{lectura.texto}</pre>
          </details>
        )}
        {lectura.campos.length > 0 && (
          <details>
            <summary>Ver datos sugeridos ({lectura.campos.length})</summary>
            <dl className="campos-extraidos">
              {lectura.campos.map((campo) => (
                <div key={campo.nombre}>
                  <dt>{ETIQUETAS_CAMPOS[campo.nombre] ?? campo.nombre}</dt>
                  <dd>
                    <strong>{campo.valor}</strong> · {Math.round(campo.confianza * 100)} % · {campo.fuente}
                    <small title={campo.evidencia}>Evidencia: {campo.evidencia}</small>
                  </dd>
                </div>
              ))}
            </dl>
            <p className="tenue">Son sugerencias y requieren confirmación antes de vincular.</p>
          </details>
        )}
        <button onClick={procesar} disabled={procesando}>
          {procesando ? "Procesando…" : "Reprocesar"}
        </button>
        <button
          onClick={() => buscarRelaciones().catch((e: unknown) => setError(String(e)))}
          disabled={procesando}
        >
          Buscar expedientes
        </button>
        {relaciones.length > 0 && (
          <ul>
            {relaciones.map((relacion) => (
              <li key={relacion.expediente.id}>
                <Link to={`/expedientes/${relacion.expediente.id}`}>
                  {numeroComprobante(
                    relacion.expediente.serie,
                    relacion.expediente.correlativo,
                  )}
                </Link>{" "}
                · {Math.round(relacion.puntaje * 100)} % · {relacion.evidencias.join("; ")}
                <button
                  onClick={() =>
                    alSeleccionar({
                      expediente: relacion.expediente,
                      tipo: lectura.tipoSugerido,
                    })
                  }
                >
                  Usar candidato
                </button>
              </li>
            ))}
          </ul>
        )}
        {error && <span className="error">{error}</span>}
      </div>
    );
  }
  return (
    <div className="formulario-linea">
      <button onClick={procesar} disabled={procesando}>
        {procesando ? "Procesando…" : "Extraer texto"}
      </button>
      {error && <span className="error">{error}</span>}
    </div>
  );
}

function obtenerLectura(documento: Documento): {
  metodo: string;
  confianza?: number;
  tipoSugerido?: TipoDocumento;
  requiereOcr: boolean;
  texto: string;
  campos: CampoExtraido[];
} | null {
  const proceso = documento.datos_extraidos?.procesamiento_documental;
  if (!proceso || typeof proceso !== "object") return null;
  const sugerencia = "clasificacion_sugerida" in proceso ? proceso.clasificacion_sugerida : null;
  const tipo =
    sugerencia &&
    typeof sugerencia === "object" &&
    "tipo" in sugerencia &&
    TIPOS_DOCUMENTO.includes(sugerencia.tipo as TipoDocumento)
      ? (sugerencia.tipo as TipoDocumento)
      : undefined;
  return {
    metodo: "metodo" in proceso ? String(proceso.metodo) : "Procesado",
    confianza:
      "confianza" in proceso && typeof proceso.confianza === "number"
        ? proceso.confianza
        : undefined,
    tipoSugerido: tipo,
    requiereOcr: "requiere_ocr" in proceso && proceso.requiere_ocr === true,
    texto: "texto" in proceso ? String(proceso.texto) : "",
    campos: obtenerCampos(proceso),
  };
}

function obtenerCampos(proceso: object): CampoExtraido[] {
  if (!("extraccion_estructurada" in proceso)) return [];
  const extraccion = proceso.extraccion_estructurada;
  if (!extraccion || typeof extraccion !== "object" || !("campos" in extraccion)) return [];
  const campos = extraccion.campos;
  if (!campos || typeof campos !== "object") return [];
  return Object.entries(campos).flatMap(([nombre, dato]) => {
    if (!dato || typeof dato !== "object" || !("valor" in dato)) return [];
    return [{
      nombre,
      valor: String(dato.valor),
      confianza: "confianza" in dato && typeof dato.confianza === "number" ? dato.confianza : 0,
      fuente: "fuente" in dato ? String(dato.fuente) : "",
      evidencia: "evidencia" in dato ? String(dato.evidencia) : "",
    }];
  });
}

function Vincular({
  documento,
  seleccion,
  alVincular,
}: {
  documento: Documento;
  seleccion?: SeleccionSugerida;
  alVincular: () => void;
}) {
  const [tipo, setTipo] = useState<TipoDocumento>(
    seleccion?.tipo ?? documento.tipo_documento ?? "VCHR",
  );
  const [buscar, setBuscar] = useState(
    seleccion ? numeroComprobante(seleccion.expediente.serie, seleccion.expediente.correlativo) : "",
  );
  const [expedienteId, setExpedienteId] = useState(seleccion?.expediente.id ?? "");
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
