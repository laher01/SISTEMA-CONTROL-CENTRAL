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
type ResultadoLote = {
  considerados: number;
  relacionados: number;
  revision_requerida: number;
  fallidos: number;
};
type SeleccionSugerida = { expediente: Expediente; tipo?: TipoDocumento };
type CampoExtraido = {
  nombre: string;
  valor: string;
  confianza: number;
  fuente: string;
  evidencia: string;
};

const CAMPOS_FISCALES = [
  "serie", "correlativo", "ruc_emisor", "ruc_receptor",
  "fecha_emision", "moneda", "importe_total",
] as const;

const ETIQUETAS_CAMPOS: Record<string, string> = {
  serie: "Serie",
  correlativo: "Correlativo",
  ruc_emisor: "RUC emisor",
  ruc_receptor: "RUC receptor",
  razon_social_emisor: "Razón social emisor",
  razon_social_receptor: "Razón social receptor",
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
  const [procesandoLote, setProcesandoLote] = useState(false);
  const [resultadoLote, setResultadoLote] = useState<ResultadoLote>();
  const [errorLote, setErrorLote] = useState("");

  const procesarAutomaticamente = async () => {
    setProcesandoLote(true);
    setErrorLote("");
    try {
      const resultado = await enviarJson<ResultadoLote>(
        "/api/v1/documentos/procesar-pendientes?limit=50",
        "POST",
      );
      setResultadoLote(resultado);
      recargar();
    } catch (e) {
      setErrorLote(e instanceof Error ? e.message : String(e));
    } finally {
      setProcesandoLote(false);
    }
  };

  const cambiar = (siguienteEstado: string, siguientePagina: number) =>
    setParametros({ estado: siguienteEstado, pagina: String(siguientePagina) });

  return (
    <>
      <h2>Documentos pendientes</h2>
      <p className="tenue">
        Aquí aparecen únicamente los archivos que necesitan revisión porque faltan datos o la
        confianza automática no fue suficiente.
      </p>
      <div className="filtros">
        <select value={estado} onChange={(e) => cambiar(e.target.value, 0)}>
          {ESTADOS_PENDIENTES.map((e) => (
            <option key={e} value={e}>
              {ETIQUETA_ESTADO_DOCUMENTO[e]}
            </option>
          ))}
        </select>
        <button onClick={procesarAutomaticamente} disabled={procesandoLote}>
          {procesandoLote ? "Procesando en orden…" : "Procesar pendientes automáticamente"}
        </button>
      </div>
      {resultadoLote && (
        <p className="resumen-carga">
          {resultadoLote.considerados} revisados · {resultadoLote.relacionados} relacionados ·{" "}
          {resultadoLote.revision_requerida} requieren revisión · {resultadoLote.fallidos} fallidos
        </p>
      )}
      {errorLote && <p className="error">{errorLote}</p>}
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
        <Procesar documento={documento} alSeleccionar={setSeleccion} alCompletar={alVincular} />
      </td>
      <td>
        {(documento.tipo_documento !== "RHE" && obtenerTipoSugerido(documento) !== "RHE") ? <Vincular
          key={`${documento.id}:${seleccion?.expediente.id ?? "manual"}:${seleccion?.tipo ?? ""}`}
          documento={documento}
          seleccion={seleccion}
          alVincular={alVincular}
        /> : <span className="tenue">El RHE crea su propio expediente.</span>}
      </td>
    </tr>
  );
}

function Procesar({
  documento,
  alSeleccionar,
  alCompletar,
}: {
  documento: Documento;
  alSeleccionar: (seleccion: SeleccionSugerida) => void;
  alCompletar: () => void;
}) {
  const [resultado, setResultado] = useState<Documento>(documento);
  const [procesando, setProcesando] = useState(false);
  const [error, setError] = useState("");
  const [relaciones, setRelaciones] = useState<RelacionSugerida[]>([]);
  const lectura = obtenerLectura(resultado);
  const motivosAutomaticos = obtenerMotivosAutomaticos(resultado);

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
        {motivosAutomaticos.length > 0 && (
          <small className="error">Revisión: {motivosAutomaticos.join("; ")}</small>
        )}
        {lectura.texto && (
          <details>
            <summary>Ver texto extraído</summary>
            <pre className="texto-extraido">{lectura.texto}</pre>
          </details>
        )}
        {(lectura.campos.length > 0 || lectura.tipoSugerido === "RHE") && (
          <ConfirmarCampos
            documentoId={documento.id}
            campos={lectura.campos}
            confirmado={lectura.confirmada}
            tipoSugerido={lectura.tipoSugerido}
            alConfirmar={setResultado}
            alCrear={alCompletar}
          />
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
        {lectura.tipoSugerido === "RHE" && <small className="tenue">El recibo por honorarios constituye su propio expediente. No lo relaciones con facturas sugeridas por importe o RUC: completa sus datos fiscales y utiliza «Crear o asociar expediente».</small>}
        {relaciones.length > 0 && lectura.tipoSugerido !== "RHE" && (
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

function obtenerTipoSugerido(documento: Documento): TipoDocumento | undefined {
  const proceso = documento.datos_extraidos?.procesamiento_documental;
  const sugerencia = proceso && typeof proceso === "object" && "clasificacion_sugerida" in proceso
    ? proceso.clasificacion_sugerida : null;
  return sugerencia && typeof sugerencia === "object" && "tipo" in sugerencia
    && TIPOS_DOCUMENTO.includes(sugerencia.tipo as TipoDocumento)
    ? sugerencia.tipo as TipoDocumento : undefined;
}

function obtenerMotivosAutomaticos(documento: Documento): string[] {
  const automatizacion = documento.datos_extraidos?.automatizacion_documental;
  if (!automatizacion || typeof automatizacion !== "object" || !("motivos" in automatizacion)) {
    return [];
  }
  return Array.isArray(automatizacion.motivos)
    ? automatizacion.motivos.map((motivo) => String(motivo))
    : [];
}

function obtenerLectura(documento: Documento): {
  metodo: string;
  confianza?: number;
  tipoSugerido?: TipoDocumento;
  requiereOcr: boolean;
  texto: string;
  campos: CampoExtraido[];
  confirmada: boolean;
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
    confirmada: Boolean(documento.datos_extraidos?.extraccion_confirmada),
  };
}

function ConfirmarCampos({
  documentoId,
  campos,
  confirmado,
  tipoSugerido,
  alConfirmar,
  alCrear,
}: {
  documentoId: string;
  campos: CampoExtraido[];
  confirmado: boolean;
  tipoSugerido?: TipoDocumento;
  alConfirmar: (documento: Documento) => void;
  alCrear: () => void;
}) {
  const [valores, setValores] = useState<Record<string, string>>(
    Object.fromEntries(campos.map((campo) => [campo.nombre, campo.valor])),
  );
  const [guardando, setGuardando] = useState(false);
  const [hayCambios, setHayCambios] = useState(false);
  const [creando, setCreando] = useState(false);
  const [tipoComprobante, setTipoComprobante] = useState<"FACT" | "RHE">(
    tipoSugerido === "RHE" ? "RHE" : "FACT",
  );
  const [razonEmisor, setRazonEmisor] = useState(
    campos.find((campo) => campo.nombre === "razon_social_emisor")?.valor ?? "",
  );
  const [razonReceptor, setRazonReceptor] = useState(
    campos.find((campo) => campo.nombre === "razon_social_receptor")?.valor ?? "",
  );
  const [requiereGuia, setRequiereGuia] = useState(tipoSugerido !== "RHE");
  const [error, setError] = useState("");
  const guardar = async () => {
    setGuardando(true);
    setError("");
    try {
      const actualizado = await enviarJson<Documento>(
        `/api/v1/documentos/${documentoId}/extraccion-confirmada`,
        "PUT",
        Object.fromEntries(Object.entries(valores).filter(([, valor]) => valor.trim() !== "")),
      );
      alConfirmar(actualizado);
      setHayCambios(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setGuardando(false);
    }
  };
  const crearExpediente = async () => {
    setCreando(true);
    setError("");
    try {
      await enviarJson(
        `/api/v1/documentos/${documentoId}/crear-expediente`,
        "POST",
        {
          tipo_comprobante: tipoComprobante,
          razon_social_emisor: razonEmisor.trim() || undefined,
          razon_social_receptor: razonReceptor.trim() || undefined,
          requiere_guia: tipoComprobante === "FACT" && requiereGuia,
        },
      );
      alCrear();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setCreando(false);
    }
  };
  return (
    <details open={tipoSugerido === "RHE" ? true : undefined}>
      <summary>
        Datos sugeridos ({campos.length}){confirmado ? " · Confirmados" : ""}
      </summary>
      <dl className="campos-extraidos">
        {[...CAMPOS_FISCALES, "razon_social_emisor", "razon_social_receptor"].map((nombre) => {
          const campo = campos.find((dato) => dato.nombre === nombre);
          return <div key={nombre}>
            <dt>{ETIQUETAS_CAMPOS[nombre] ?? nombre}</dt>
            <dd>
              <input
                aria-label={ETIQUETAS_CAMPOS[nombre] ?? nombre}
                type={nombre === "fecha_emision" ? "date" : nombre === "importe_total" ? "number" : "text"}
                step={nombre === "importe_total" ? "0.01" : undefined}
                value={valores[nombre] ?? ""}
                placeholder={campo ? undefined : "Completar desde el comprobante"}
                onChange={(e) => { setValores({ ...valores, [nombre]: e.target.value }); setHayCambios(true); }}
              />
              {campo && <>
                <span> {Math.round(campo.confianza * 100)} % · {campo.fuente}</span>
                <small title={campo.evidencia}>Evidencia: {campo.evidencia}</small>
              </>}
            </dd>
          </div>;
        })}
      </dl>
      {tipoSugerido === "RHE" && <p className="tenue">Comprueba los datos contra el recibo original. Un RHE genera su expediente independiente, sin obligación de guía de remisión.</p>}
      {hayCambios && <small className="tenue">Guarda primero las correcciones fiscales para crear el expediente.</small>}
      <button disabled={guardando} onClick={guardar}>
        {guardando ? "Guardando…" : confirmado ? "Actualizar confirmación" : "Confirmar campos"}
      </button>
      {confirmado && !hayCambios && (
        <div className="crear-expediente-asistido">
          <select
            aria-label="Tipo de comprobante"
            value={tipoComprobante}
            onChange={(e) => {
              const tipo = e.target.value as "FACT" | "RHE";
              setTipoComprobante(tipo);
              setRequiereGuia(tipo === "FACT");
            }}
          >
            <option value="FACT">Factura</option>
            <option value="RHE">Recibo por honorarios</option>
          </select>
          <input
            placeholder="Razón social emisor (opcional)"
            value={razonEmisor}
            onChange={(e) => setRazonEmisor(e.target.value)}
          />
          <input
            placeholder="Razón social receptor (opcional)"
            value={razonReceptor}
            onChange={(e) => setRazonReceptor(e.target.value)}
          />
          {tipoComprobante === "FACT" && (
            <label>
              <input
                type="checkbox"
                checked={requiereGuia}
                onChange={(e) => setRequiereGuia(e.target.checked)}
              />{" "}
              Requiere guía
            </label>
          )}
          <button disabled={creando} onClick={crearExpediente}>
            {creando ? "Creando…" : "Crear o asociar expediente"}
          </button>
        </div>
      )}
      {error && <span className="error">{error}</span>}
    </details>
  );
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
