import { useRef, useState } from "react";
import "./ExpedienteManual.css";
import { validarCamposManuales } from "./validacionExpedienteManual";
import { Link, useSearchParams } from "react-router-dom";

import { ErrorApi, conParametros, eliminar, enviarJson, obtener, urlArchivo, useDatos } from "../api";
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
  type SesionActual,
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
type OrigenDocumental = Pick<Documento,
  "gestor_nombre" | "gestor_codigo" | "usuario_nombre" | "usuario_codigo" |
  "responsable_nombre" | "responsable_codigo"
>;

type ProvisionalGRE = OrigenDocumental & {
  documento_id: string;
  factura: string;
  emisor_ruc: string;
  receptor_ruc: string;
  cliente_autorizado: boolean;
};
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
  razon_social_emisor: "Razón social emisor",
  razon_social_receptor: "Razón social receptor",
  fecha_emision: "Fecha de emisión",
  moneda: "Moneda",
  importe_total: "Importe total",
  serie_factura: "Serie de la factura referenciada",
  correlativo_factura: "Correlativo de la factura referenciada",
  emisor_factura_ruc: "RUC emisor de la factura",
  subtotal: "Subtotal (opcional)",
  igv: "IGV (opcional)",
  numero_operacion: "N.º de operación",
};

export default function Pendientes({ rol }: { rol: SesionActual["rol"] }) {
  const mostrarOrigen = ["ADMINISTRADOR", "GERENTE", "SECRETARIA", "RESPONSABLE"].includes(rol);
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
  const { datos: capacidades } = useDatos<{ puede_retirar: boolean }>(
    "/api/v1/documentos/capacidades",
  );
  const { datos: provisionales, recargar: recargarProvisionales } = useDatos<ProvisionalGRE[]>(
    "/api/v1/documentos/provisionales-gre?limit=2000",
  );
  const [reindexando, setReindexando] = useState(false);
  const [resultadoReindice, setResultadoReindice] = useState("");
  const reindexarGuias = async () => {
    setReindexando(true);
    try {
      const resultado = await enviarJson<{
        considerados: number; provisionales_creados: number; guias_relacionadas: number
      }>("/api/v1/documentos/reindexar-gre-pendientes?limit=2000", "POST");
      setResultadoReindice(
        `${resultado.considerados} GRE revisadas sin OCR · ${resultado.provisionales_creados} expedientes provisionales · ${resultado.guias_relacionadas} relacionadas`
      );
      recargar();
      recargarProvisionales();
    } catch (e) {
      setResultadoReindice(e instanceof Error ? e.message : String(e));
    } finally {
      setReindexando(false);
    }
  };
  const [procesandoLote, setProcesandoLote] = useState(false);
  const [resultadoLote, setResultadoLote] = useState<ResultadoLote>();
  const [errorLote, setErrorLote] = useState("");
  const [seleccionados, setSeleccionados] = useState<string[]>([]);
  const [eliminandoSeleccionados, setEliminandoSeleccionados] = useState(false);
  const [resultadoEliminacion, setResultadoEliminacion] = useState("");
  const [errorEliminacion, setErrorEliminacion] = useState("");

  const eliminarSeleccionados = async () => {
    const visibles = (datos ?? []).filter((d) => seleccionados.includes(d.id));
    if (!visibles.length || eliminandoSeleccionados) return;
    try {
      const vista = await enviarJson<{
        total: number;
        aptos: number;
        resultados: { id: string; estado: string }[];
      }>("/api/v1/documentos/previsualizar-retirada", "POST", {
        documentos_ids: visibles.map((d) => d.id),
      });
      if (vista.aptos !== visibles.length) {
        const requiereMisd = vista.resultados.filter(
          (fila) => fila.estado === "REQUIERE_MISD",
        ).length;
        setErrorEliminacion(
          requiereMisd > 0
            ? `${requiereMisd} documento(s) requieren aprobación MISD antes de eliminarse.`
            : `Solo ${vista.aptos} de ${visibles.length} documentos tienen autorización para eliminarse. Actualice la bandeja.`,
        );
        return;
      }
    } catch (error) {
      setErrorEliminacion(error instanceof Error ? error.message : String(error));
      return;
    }
    const nombres = visibles.slice(0, 20)
      .map((documento) => `• ${documento.nombre_original}`).join("\n");
    const mas = visibles.length > 20 ? `\n…y ${visibles.length - 20} más` : "";
    if (!window.confirm([
      `Eliminar definitivamente ${visibles.length} documentos?`,
      nombres,
      mas,
      "Se borrarán sus archivos físicos y no se podrán restaurar.",
    ].filter(Boolean).join("\n"))) return;
    setEliminandoSeleccionados(true);
    setErrorEliminacion("");
    setResultadoEliminacion("");
    const eliminados: string[] = [];
    const errores: string[] = [];
    try {
      const resultado = await enviarJson<{
        eliminados: number;
        resultados: { id: string; estado: string; codigo?: string }[];
      }>("/api/v1/documentos/retirar-lote", "POST", {
        documentos_ids: visibles.map((d) => d.id),
      });
      for (const fila of resultado.resultados) {
        if (fila.estado.startsWith("ELIMINADO")) eliminados.push(fila.id);
        else {
          const documento = visibles.find((d) => d.id === fila.id);
          errores.push(`${documento?.nombre_original ?? fila.id}: error ${fila.codigo ?? "desconocido"}`);
        }
      }
    } catch (error) {
      setErrorEliminacion(error instanceof Error ? error.message : String(error));
      setEliminandoSeleccionados(false);
      return;
    }
    setSeleccionados((actual) => actual.filter((id) => !eliminados.includes(id)));
    setResultadoEliminacion(`${eliminados.length} de ${visibles.length} documentos eliminados.`);
    setErrorEliminacion(errores.join(" | "));
    setEliminandoSeleccionados(false);
    recargar();
    recargarProvisionales();
  };

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
      recargarProvisionales();
    } catch (e) {
      setErrorLote(e instanceof Error ? e.message : String(e));
    } finally {
      setProcesandoLote(false);
    }
  };

  const cambiar = (siguienteEstado: string, siguientePagina: number) => {
    setSeleccionados([]);
    setParametros({ estado: siguienteEstado, pagina: String(siguientePagina) });
  };

  return (
    <>
      <h2>Documentos pendientes</h2>
      {provisionales && provisionales.length > 0 && (
        <section>
          <h3>Expedientes provisionales — esperando factura ({provisionales.length})</h3>
          <p className="tenue">Ya identificados por la GRE remitente. Sin monto ni producción hasta recibir la factura y validar al cliente.</p>
          <table>
            <thead>
              <tr><th>Factura referenciada</th><th>RUC emisor</th><th>RUC receptor</th><th>Validación del cliente</th>{mostrarOrigen && <th>Ruta de origen</th>}<th>Guía</th></tr>
            </thead>
            <tbody>
              {provisionales.map((p) => (
                <tr key={p.documento_id}>
                  <td>{p.factura}</td>
                  <td>{p.emisor_ruc}</td>
                  <td>{p.receptor_ruc}</td>
                  <td>
                    {p.cliente_autorizado
                      ? <span>Autorizado · pendiente de factura</span>
                      : <strong style={{ color: "#b91c1c" }}>NO VÁLIDO — CLIENTE NO AUTORIZADO</strong>}
                  </td>
                  {mostrarOrigen && <td><RutaOrigen origen={p} /></td>}
                  <td><a href={urlArchivo(p.documento_id)} target="_blank" rel="noreferrer">Ver GRE</a></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
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
        <button onClick={reindexarGuias} disabled={reindexando}>
          {reindexando ? "Conciliando…" : "Conciliar hasta 2.000 GRE anteriores (sin OCR)"}
        </button>
        <button onClick={procesarAutomaticamente} disabled={procesandoLote}>
          {procesandoLote ? "Procesando en orden…" : "Procesar pendientes automáticamente"}
        </button>
      </div>
      {resultadoReindice && <p className="resumen-carga">{resultadoReindice}</p>}
      {resultadoLote && (
        <p className="resumen-carga">
          {resultadoLote.considerados} revisados · {resultadoLote.relacionados} relacionados ·{" "}
          {resultadoLote.revision_requerida} requieren revisión · {resultadoLote.fallidos} fallidos
        </p>
      )}
      {errorLote && <p className="error">{errorLote}</p>}
      <div className="acciones-documento">
        <strong>{(datos ?? []).filter((d) => seleccionados.includes(d.id)).length} pendientes seleccionados</strong>
        <button className="peligro" disabled={!capacidades?.puede_retirar || eliminandoSeleccionados || !(datos ?? []).some((d) => seleccionados.includes(d.id))} onClick={() => void eliminarSeleccionados()}>
          {eliminandoSeleccionados ? "Eliminando…" : "Eliminar seleccionados"}
        </button>
        <button className="secundario" disabled={eliminandoSeleccionados || !seleccionados.length} onClick={() => setSeleccionados([])}>Limpiar selección</button>
      </div>
      {resultadoEliminacion && <p role="status">{resultadoEliminacion}</p>}
      {errorEliminacion && <p role="alert" className="error">{errorEliminacion}</p>}
      <Estado cargando={cargando} error={error} vacio={datos?.length === 0}>
        <table>
          <thead>
            <tr>
              <th><input type="checkbox" aria-label="Seleccionar pendientes visibles" checked={(datos?.length ?? 0) > 0 && (datos ?? []).every((d) => seleccionados.includes(d.id))} onChange={(e) => setSeleccionados(e.target.checked ? (datos ?? []).map((d) => d.id) : [])} /></th>
              <th>Archivo</th>
              {mostrarOrigen && <th>Ruta de origen</th>}
              <th>Subido</th>
              <th>Lectura</th>
              <th>Vincular</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {datos?.map((d) => <FilaPendiente key={d.id} documento={d} mostrarOrigen={mostrarOrigen} alVincular={() => { recargar(); recargarProvisionales(); }} puedeRetirar={capacidades?.puede_retirar ?? false} seleccionado={seleccionados.includes(d.id)} alSeleccionar={(activo) => setSeleccionados((actual) => activo ? [...new Set([...actual, d.id])] : actual.filter((id) => id !== d.id))} />)}
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

function RutaOrigen({ origen }: { origen: OrigenDocumental }) {
  const niveles = [
    ["Gestor", origen.gestor_nombre, origen.gestor_codigo],
    ["Usuario", origen.usuario_nombre, origen.usuario_codigo],
    ["Responsable", origen.responsable_nombre, origen.responsable_codigo],
  ];
  return niveles.map(([nivel, nombre, codigo]) => (
    <span key={nivel} className="bloque">
      <strong>{nivel}</strong>{" "}{[nombre, codigo].filter(Boolean).join(" · ") || "Sin asignar"}
    </span>
  ));
}

function FilaPendiente({
  documento,
  mostrarOrigen,
  alVincular,
  seleccionado,
  alSeleccionar,
  puedeRetirar,
}: {
  documento: Documento;
  mostrarOrigen: boolean;
  alVincular: () => void;
  seleccionado: boolean;
  alSeleccionar: (activo: boolean) => void;
  puedeRetirar: boolean;
}) {
  const [seleccion, setSeleccion] = useState<SeleccionSugerida>();
  const [eliminando, setEliminando] = useState(false);
  const [errorEliminar, setErrorEliminar] = useState("");
  const retirar = async () => {
    if (!window.confirm(
      "¿Eliminar definitivamente este documento de FACT CENTRAL? Se borrará el archivo físico y no se podrá restaurar."
    )) return;
    setEliminando(true);
    setErrorEliminar("");
    try {
      const resultado = (await eliminar("/api/v1/documentos/" + documento.id)) as {
        estado?: string;
      };
      if (resultado.estado === "pendiente") {
        setErrorEliminar("Registro eliminado; el archivo físico quedó pendiente de borrado.");
      }
      alVincular();
    } catch (error) {
      setErrorEliminar(error instanceof Error ? error.message : String(error));
    } finally {
      setEliminando(false);
    }
  };
  return (
    <tr>
      <td><input type="checkbox" aria-label={`Seleccionar ${documento.nombre_original}`} checked={seleccionado} onChange={(e) => alSeleccionar(e.target.checked)} /></td>
      <td>
        <a href={urlArchivo(documento.id)} target="_blank" rel="noreferrer">
          {documento.nombre_original}
        </a>
      </td>
      {mostrarOrigen && <td><RutaOrigen origen={documento} /></td>}
      <td>{formatearFecha(documento.created_at)}</td>
      <td>
        <Procesar documento={documento} alSeleccionar={setSeleccion} alCompletar={alVincular} />
      </td>
      <td>
        <Vincular
          key={`${documento.id}:${seleccion?.expediente.id ?? "manual"}:${seleccion?.tipo ?? ""}`}
          documento={documento}
          seleccion={seleccion}
          alVincular={alVincular}
        />
      </td>
      <td>
        {puedeRetirar && <button className="peligro" onClick={retirar} disabled={eliminando}>
          {eliminando ? "Eliminando…" : "Eliminar"}
        </button>}
        {documento.tipo_documento === "VCHR" && <Link className="boton secundario" to={`/pagos-documentales/${documento.id}`}>Pago agrupado</Link>}
        {errorEliminar && <small role="alert" className="error bloque">{errorEliminar}</small>}
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
        <ConfirmarCampos
            documento={resultado}
            campos={lectura.campos}
            confirmado={lectura.confirmada}
            tipoSugerido={lectura.tipoSugerido}
            alConfirmar={setResultado}
            alCrear={alCompletar}
          />
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
      <ConfirmarCampos
        documento={resultado}
        campos={[]}
        confirmado={Boolean(resultado.datos_extraidos?.extraccion_confirmada)}
        alConfirmar={setResultado}
        alCrear={alCompletar}
      />
      <button onClick={procesar} disabled={procesando}>
        {procesando ? "Procesando…" : "Extraer texto"}
      </button>
      {error && <span className="error">{error}</span>}
    </div>
  );
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
  documento,
  campos,
  confirmado,
  tipoSugerido,
  alConfirmar,
  alCrear,
}: {
  documento: Documento;
  campos: CampoExtraido[];
  confirmado: boolean;
  tipoSugerido?: TipoDocumento;
  alConfirmar: (documento: Documento) => void;
  alCrear: () => void;
}) {
  const documentoId = documento.id;
  const dialogo = useRef<HTMLDialogElement>(null);
  const [valores, setValores] = useState<Record<string, string>>({});
  const [mostrarManual, setMostrarManual] = useState(false);
  const [modificado, setModificado] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [creando, setCreando] = useState(false);
  const esGuia = documento.tipo_documento === "GRR" || tipoSugerido === "GRR";
  const [tipoComprobante, setTipoComprobante] = useState<"FACT" | "RHE" | "GRR">("FACT");
  const [requiereGuia, setRequiereGuia] = useState(true);
  const [error, setError] = useState("");
  const [duplicado, setDuplicado] = useState<Expediente | null>(null);
  const errores = validarCamposManuales(tipoComprobante === "RHE" ? { ...valores, subtotal: "", igv: "" } : valores, tipoComprobante);
  const ocupado = guardando || creando;
  const listo = confirmado && !modificado;
  const valido = Object.keys(errores).length === 0;

  const abrir = () => {
    const previa = documento.datos_extraidos?.extraccion_confirmada;
    const confirmados: Record<string, string> = previa && typeof previa === "object" && "campos" in previa
      && previa.campos && typeof previa.campos === "object"
      ? Object.fromEntries(Object.entries(previa.campos).map(([nombre, valor]) => [nombre, String(valor)]))
      : {};
    const iniciales: Record<string, string> = { moneda: "PEN", ...Object.fromEntries(campos.map((campo) => [campo.nombre, campo.valor])), ...confirmados };
    setValores(iniciales);
    const tipo = esGuia ? "GRR" : tipoSugerido === "RHE" ? "RHE" : "FACT";
    setTipoComprobante(tipo);
    setRequiereGuia(tipo === "FACT");
    setModificado(Object.entries(iniciales).some(([nombre, valor]) => valor.trim() && confirmados[nombre] !== valor));
    setError("");
    setDuplicado(null);
    setMostrarManual(true);
    dialogo.current?.showModal();
    if (esGuia) {
      void obtener<Record<string, string | null>>(`/api/v1/documentos/${documentoId}/referencia-gre`)
        .then((ref) => setValores((actual) => {
          const siguientes = { ...actual };
          for (const [nombre, valor] of Object.entries(ref)) {
            const campo = nombre === "receptor_ruc" ? "ruc_receptor" : nombre;
            if (valor && (campo !== "ruc_receptor" || !siguientes[campo])) siguientes[campo] = siguientes[campo] || valor;
          }
          return siguientes;
        }))
        .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)));
    }
  };
  const editar = (nombre: string, valor: string) => {
    setValores((actual) => ({ ...actual, [nombre]: nombre.startsWith("serie") ? valor.toUpperCase() : valor }));
    setModificado(true);
    setDuplicado(null);
  };
  const guardar = async () => {
    if (!valido || ocupado) return;
    setGuardando(true);
    setError("");
    const permitidos = ["serie", "correlativo", "ruc_emisor", "ruc_receptor", "fecha_emision", "moneda", "importe_total", "razon_social_emisor", "razon_social_receptor", "subtotal", "igv", "descuentos", "importe_a_pagar", "numero_operacion"];
    const payload = Object.fromEntries(Object.entries(valores).flatMap(([nombre, valor]) =>
      permitidos.includes(nombre) && valor.trim() && !(tipoComprobante === "RHE" && ["subtotal", "igv"].includes(nombre)) ? [[nombre, valor.trim()]] : [],
    ));
    try {
      const actualizado = await enviarJson<Documento>(
        `/api/v1/documentos/${documentoId}/extraccion-confirmada`,
        "PUT",
        payload,
      );
      alConfirmar(actualizado);
      setModificado(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setGuardando(false);
    }
  };
  const crearExpediente = async () => {
    if ((!listo && tipoComprobante !== "GRR") || !valido || ocupado) return;
    setCreando(true);
    setError("");
    setDuplicado(null);
    try {
      if (tipoComprobante === "GRR") {
        await enviarJson(`/api/v1/documentos/${documentoId}/referencia-gre`, "POST", {
          serie_guia: valores.serie,
          correlativo_guia: valores.correlativo,
          serie_factura: valores.serie_factura,
          correlativo_factura: valores.correlativo_factura,
          emisor_factura_ruc: valores.emisor_factura_ruc,
          receptor_ruc: valores.ruc_receptor,
        });
      } else await enviarJson(
        `/api/v1/documentos/${documentoId}/crear-expediente`,
        "POST",
        {
          tipo_comprobante: tipoComprobante,
          razon_social_emisor: valores.razon_social_emisor?.trim() || undefined,
          razon_social_receptor: valores.razon_social_receptor?.trim() || undefined,
          requiere_guia: tipoComprobante === "FACT" && requiereGuia,
        },
      );
      dialogo.current?.close();
      alCrear();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      if (e instanceof ErrorApi && e.status === 409 && e.detalle && typeof e.detalle === "object") {
        const detalle = e.detalle as { duplicado?: boolean; expediente_id?: string };
        if (detalle.duplicado && detalle.expediente_id) {
          try {
            setDuplicado(await obtener<Expediente>(`/api/v1/expedientes/${detalle.expediente_id}`));
          } catch {
            // No mostrar información de expedientes fuera del ámbito autorizado.
          }
        }
      }
    } finally {
      setCreando(false);
    }
  };

  const campo = (nombre: string, ancho = false) => {
    const extraido = campos.find((item) => item.nombre === nombre);
    const etiqueta = tipoComprobante === "GRR" && nombre === "serie" ? "Serie de la guía" : tipoComprobante === "GRR" && nombre === "correlativo" ? "Correlativo de la guía" : ETIQUETAS_CAMPOS[nombre] ?? nombre;
    const id = `manual-${documentoId}-${nombre}`;
    return (
      <div className={`manual-expediente-campo${ancho ? " ancho" : ""}`}>
        <label htmlFor={id}>{etiqueta}</label>
        {nombre === "moneda" ? (
          <select id={id} value={valores[nombre] ?? ""} onChange={(e) => editar(nombre, e.target.value)} aria-invalid={Boolean(errores[nombre])}>
            <option value="">Seleccione moneda</option>
            <option value="PEN">PEN — Soles</option>
            <option value="USD">USD — Dólares</option>
          </select>
        ) : (
          <input id={id} value={valores[nombre] ?? ""}
            type={nombre === "fecha_emision" ? "date" : "text"}
            inputMode={nombre.includes("ruc") || nombre.startsWith("correlativo") ? "numeric" : ["importe_total", "subtotal", "igv"].includes(nombre) ? "decimal" : undefined}
            maxLength={nombre.includes("ruc") ? 11 : nombre.startsWith("serie") ? 4 : nombre === "correlativo_factura" ? 8 : nombre === "correlativo" ? 32 : nombre.startsWith("razon_social") ? 300 : undefined}
            onChange={(e) => editar(nombre, e.target.value)}
            aria-invalid={Boolean(errores[nombre])}
            aria-describedby={errores[nombre] ? id + "-error" : undefined}
          />
        )}
        {errores[nombre] && <small className="error" id={id + "-error"}>{errores[nombre]}</small>}
        {extraido && <details><summary>{Math.round(extraido.confianza * 100)} % · {extraido.fuente || "Lectura"}</summary>{extraido.evidencia}</details>}
      </div>
    );
  };
  return (
    <div>
      <button type="button" onClick={abrir}>Crear expediente manualmente</button>
      <dialog ref={dialogo} className="manual-expediente-dialog" aria-labelledby={`manual-titulo-${documentoId}`}
        onClose={() => setMostrarManual(false)} onCancel={(e) => { if (ocupado) e.preventDefault(); }}>
        {mostrarManual && <>
          <header className="manual-expediente-cabecera">
            <div><h2 id={`manual-titulo-${documentoId}`}>Creación manual de expediente</h2>
              <p className="tenue">Revise el comprobante original, confirme los datos y cree el expediente.</p></div>
            <button type="button" className="secundario" disabled={ocupado} onClick={() => dialogo.current?.close()}>Cerrar</button>
          </header>
          <div className="manual-expediente-cuerpo">
            <section className="manual-expediente-archivo">
              <h3>Documento original</h3>
              <p><a href={urlArchivo(documentoId)} target="_blank" rel="noreferrer">{documento.nombre_original} · Abrir original</a></p>
              {documento.nombre_original.toLowerCase().endsWith(".pdf") && <iframe className="manual-expediente-preview" title="Vista previa del PDF original" src={urlArchivo(documentoId)} />}
              <h3>Ruta de origen</h3>
              <div className="manual-expediente-ruta"><RutaOrigen origen={documento} /></div>
            </section>
            <section className="manual-expediente-formulario">
              <div role="status" className="manual-expediente-aviso">{campos.length} datos sugeridos · {listo ? "Confirmados" : "Pendientes de confirmar"}{!valido && ` · ${Object.keys(errores).length} campos por revisar`}</div>
              <fieldset disabled={ocupado} className="manual-expediente-grupo">
                <legend>Identificación del comprobante</legend>
                <div className="manual-expediente-campos">
                  <div className="manual-expediente-campo ancho"><label htmlFor={`manual-tipo-${documentoId}`}>Tipo de comprobante</label>
                    <select id={`manual-tipo-${documentoId}`} value={tipoComprobante} onChange={(e) => {
                      const tipo = e.target.value as "FACT" | "RHE" | "GRR";
                      setTipoComprobante(tipo); setRequiereGuia(tipo === "FACT"); setDuplicado(null);
                      setModificado(true);
                    }}>{esGuia ? <option value="GRR">GRE remitente</option> : <><option value="FACT">Factura</option><option value="RHE">Recibo por honorarios</option></>}</select>
                  </div>
                  {campo("serie")}{campo("correlativo")}{tipoComprobante !== "GRR" && <>{campo("fecha_emision")}{campo("moneda")}</>}
                </div>
              </fieldset>
              {tipoComprobante === "GRR" && <fieldset disabled={ocupado} className="manual-expediente-grupo">
                <legend>Factura referenciada (no es el número de la guía)</legend>
                <p className="tenue">Confirme los datos impresos en Documentos relacionados. Si la referencia no se lee, ingrésela desde el original.</p>
                <div className="manual-expediente-campos">{campo("serie_factura")}{campo("correlativo_factura")}{campo("emisor_factura_ruc", true)}{campo("ruc_receptor", true)}</div>
              </fieldset>}
              {tipoComprobante !== "GRR" && <fieldset disabled={ocupado} className="manual-expediente-grupo">
                <legend>Emisor y receptor</legend>
                <div className="manual-expediente-campos">
                  {campo("ruc_emisor")}{campo("razon_social_emisor", true)}
                  {campo("ruc_receptor")}{campo("razon_social_receptor", true)}
                </div>
              </fieldset>}
              {tipoComprobante === "GRR" ? <div className="manual-expediente-aviso"><strong>Esperando factura · S/ 0.00 contabilizable</strong><p>La fecha y el importe fiscales se obtendrán de la factura cuando llegue.</p></div> : <fieldset disabled={ocupado} className="manual-expediente-grupo">
                <legend>Importes y requisitos</legend>
                <div className="manual-expediente-campos">
                  {tipoComprobante === "FACT" && <>{campo("subtotal")}{campo("igv")}</>}
                  {campo("importe_total", true)}
                  {tipoComprobante === "FACT" && <label className="manual-expediente-campo ancho"><span><input type="checkbox" checked={requiereGuia} onChange={(e) => setRequiereGuia(e.target.checked)} /> Requiere guía de remisión</span></label>}
                </div>
              </fieldset>}
              {error && <p role="alert" className="error manual-expediente-aviso">{error}</p>}
              {duplicado && <div role="alert" className="manual-expediente-aviso">
                <strong>Ya existe un expediente con esta identidad fiscal. No se creó otro.</strong>
                <div className="manual-expediente-comparacion">
                  <table><thead><tr><th>Campo</th><th>Confirmado</th><th>Existente</th></tr></thead><tbody>
                    <tr><td>Serie y número</td><td>{valores.serie}-{valores.correlativo}</td><td>{duplicado.serie}-{duplicado.correlativo}</td></tr>
                    <tr><td>RUC emisor</td><td>{valores.ruc_emisor}</td><td>{duplicado.emisor.ruc}</td></tr>
                    <tr><td>RUC receptor</td><td>{valores.ruc_receptor}</td><td>{duplicado.receptor.ruc}</td></tr>
                    <tr><td>Fecha</td><td>{valores.fecha_emision}</td><td>{duplicado.fecha_emision}</td></tr>
                    <tr><td>Moneda</td><td>{valores.moneda}</td><td>{duplicado.moneda}</td></tr>
                    <tr><td>Importe</td><td>{valores.importe_total}</td><td>{duplicado.importe_total}</td></tr>
                  </tbody></table>
                </div>
                <Link to={`/expedientes/${duplicado.id}`}>Revisar expediente existente</Link>
                <p>Para vincular, cierre esta ventana y use la búsqueda de expedientes de la bandeja.</p>
              </div>}
            </section>
          </div>
          <footer className="manual-expediente-pie">
            <button type="button" className="secundario" disabled={ocupado} onClick={() => dialogo.current?.close()}>Cancelar</button>
            {tipoComprobante !== "GRR" && <button type="button" disabled={ocupado || !valido} onClick={() => void guardar()}>{guardando ? "Guardando…" : listo ? "Actualizar confirmación" : "Confirmar datos"}</button>}
            <button type="button" disabled={ocupado || (tipoComprobante !== "GRR" && !listo) || !valido || Boolean(duplicado)} onClick={() => void crearExpediente()}>{creando ? "Guardando…" : tipoComprobante === "GRR" ? "Crear expediente provisional" : "Crear expediente"}</button>
          </footer>
        </>}
      </dialog>
    </div>
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
