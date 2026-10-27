import { useState } from "react";
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
type ProvisionalGRE = {
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
  const [retirandoSeleccionados, setRetirandoSeleccionados] = useState(false);
  const [resultadoRetirada, setResultadoRetirada] = useState("");
  const [errorRetirada, setErrorRetirada] = useState("");

  const retirarSeleccionados = async () => {
    const visibles = (datos ?? []).filter((d) => seleccionados.includes(d.id));
    if (!visibles.length || retirandoSeleccionados) return;
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
        setErrorRetirada(
          requiereMisd > 0
            ? `${requiereMisd} documento(s) requieren aprobación MISD antes del retiro.`
            : `Solo ${vista.aptos} de ${visibles.length} documentos tienen autorización para retirarse. Actualice la bandeja.`,
        );
        return;
      }
    } catch (error) {
      setErrorRetirada(error instanceof Error ? error.message : String(error));
      return;
    }
    if (!window.confirm(`¿Retirar ${visibles.length} documentos pendientes? Los originales se conservarán.`)) return;
    setRetirandoSeleccionados(true);
    setErrorRetirada("");
    setResultadoRetirada("");
    const retirados: string[] = [];
    const errores: string[] = [];
    try {
      const resultado = await enviarJson<{
        retirados: number;
        resultados: { id: string; estado: string; codigo?: string }[];
      }>("/api/v1/documentos/retirar-lote", "POST", {
        documentos_ids: visibles.map((d) => d.id),
      });
      for (const fila of resultado.resultados) {
        if (fila.estado === "RETIRADO") retirados.push(fila.id);
        else {
          const documento = visibles.find((d) => d.id === fila.id);
          errores.push(`${documento?.nombre_original ?? fila.id}: error ${fila.codigo ?? "desconocido"}`);
        }
      }
    } catch (error) {
      setErrorRetirada(error instanceof Error ? error.message : String(error));
      setRetirandoSeleccionados(false);
      return;
    }
    setSeleccionados((actual) => actual.filter((id) => !retirados.includes(id)));
    setResultadoRetirada(`${retirados.length} de ${visibles.length} documentos retirados.`);
    setErrorRetirada(errores.join(" | "));
    setRetirandoSeleccionados(false);
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
              <tr><th>Factura referenciada</th><th>RUC emisor</th><th>RUC receptor</th><th>Validación del cliente</th><th>Guía</th></tr>
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
        <button className="peligro" disabled={!capacidades?.puede_retirar || retirandoSeleccionados || !(datos ?? []).some((d) => seleccionados.includes(d.id))} onClick={() => void retirarSeleccionados()}>
          {retirandoSeleccionados ? "Retirando…" : "Eliminar seleccionados"}
        </button>
        <button className="secundario" disabled={retirandoSeleccionados || !seleccionados.length} onClick={() => setSeleccionados([])}>Limpiar selección</button>
      </div>
      {resultadoRetirada && <p role="status">{resultadoRetirada}</p>}
      {errorRetirada && <p role="alert" className="error">{errorRetirada}</p>}
      <Estado cargando={cargando} error={error} vacio={datos?.length === 0}>
        <table>
          <thead>
            <tr>
              <th><input type="checkbox" aria-label="Seleccionar pendientes visibles" checked={(datos?.length ?? 0) > 0 && (datos ?? []).every((d) => seleccionados.includes(d.id))} onChange={(e) => setSeleccionados(e.target.checked ? (datos ?? []).map((d) => d.id) : [])} /></th>
              <th>Archivo</th>
              <th>Subido</th>
              <th>Lectura</th>
              <th>Vincular</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {datos?.map((d) => <FilaPendiente key={d.id} documento={d} alVincular={recargar} puedeRetirar={capacidades?.puede_retirar ?? false} seleccionado={seleccionados.includes(d.id)} alSeleccionar={(activo) => setSeleccionados((actual) => activo ? [...new Set([...actual, d.id])] : actual.filter((id) => id !== d.id))} />)}
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
  seleccionado,
  alSeleccionar,
  puedeRetirar,
}: {
  documento: Documento;
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
      "¿Retirar este documento de FACT CENTRAL? Quedará auditado y se conservará el original."
    )) return;
    setEliminando(true);
    setErrorEliminar("");
    try {
      await eliminar("/api/v1/documentos/" + documento.id);
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
            documentoId={documento.id}
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
        documentoId={documento.id}
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
  const [valores, setValores] = useState<Record<string, string>>({
    moneda: "PEN",
    ...Object.fromEntries(campos.map((campo) => [campo.nombre, campo.valor])),
  });
  const [mostrarManual, setMostrarManual] = useState(false);
  const nombresCampos = [
    "serie", "correlativo", "ruc_emisor", "ruc_receptor",
    "fecha_emision", "moneda", "importe_total",
    "razon_social_emisor", "razon_social_receptor",
  ];
  const [guardando, setGuardando] = useState(false);
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
  const [duplicado, setDuplicado] = useState<Expediente | null>(null);
  const guardar = async () => {
    setGuardando(true);
    setError("");
    try {
      const actualizado = await enviarJson<Documento>(
        `/api/v1/documentos/${documentoId}/extraccion-confirmada`,
        "PUT",
        valores,
      );
      alConfirmar(actualizado);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setGuardando(false);
    }
  };
  const crearExpediente = async () => {
    setCreando(true);
    setError("");
    setDuplicado(null);
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
      if (e instanceof ErrorApi && e.status === 409 && e.detalle && typeof e.detalle === "object") {
        const detalle = e.detalle as { duplicado?: boolean; expediente_id?: string };
        if (detalle.duplicado && detalle.expediente_id) {
          try {
            const existente = await obtener<Expediente>(
              `/api/v1/expedientes/${detalle.expediente_id}`,
            );
            setDuplicado(existente);
          } catch {
            // El backend controla el ámbito: no mostrar información no autorizada.
          }
        }
      }
    } finally {
      setCreando(false);
    }
  };
  return (
    <div>
      <button type="button" onClick={() => setMostrarManual((actual) => !actual)}>
        {mostrarManual ? "Cerrar creación manual" : "Crear expediente manualmente"}
      </button>
      {mostrarManual && (
      <div className="crear-expediente-asistido">
      <p>Datos sugeridos ({campos.length}){confirmado ? " · Confirmados" : ""}</p>
      <p>Confirme los datos del comprobante antes de crear el expediente. Si ya existe la misma identidad fiscal, el sistema debe rechazar la duplicación.</p>
      <dl className="campos-extraidos">
        {nombresCampos.map((nombre) => {
          const campo = campos.find((item) => item.nombre === nombre);
          return (
          <div key={nombre}>
            <dt>{ETIQUETAS_CAMPOS[nombre] ?? nombre}</dt>
            <dd>
              <input
                aria-label={ETIQUETAS_CAMPOS[nombre] ?? nombre}
                value={valores[nombre] ?? ""}
                type={nombre === "fecha_emision" ? "date" : "text"}
                onChange={(e) => setValores({ ...valores, [nombre]: e.target.value })}
              />
              {campo && (
                <>
                  <span> {Math.round(campo.confianza * 100)} % · {campo.fuente}</span>
                  <small title={campo.evidencia}>Evidencia: {campo.evidencia}</small>
                </>
              )}
            </dd>
          </div>
          );
        })}
      </dl>
      <button disabled={guardando} onClick={guardar}>
        {guardando ? "Guardando…" : confirmado ? "Actualizar confirmación" : "Confirmar campos"}
      </button>
      {confirmado && (
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
      {duplicado && (
        <div role="alert">
          <strong>Ya existe un expediente con esta identidad fiscal. No se creó otro.</strong>
          <table>
            <thead><tr><th>Campo</th><th>Confirmación manual</th><th>Expediente existente</th></tr></thead>
            <tbody>
              <tr><td>Serie</td><td>{valores.serie}</td><td>{duplicado.serie}</td></tr>
              <tr><td>Número</td><td>{valores.correlativo}</td><td>{duplicado.correlativo}</td></tr>
              <tr><td>RUC emisor</td><td>{valores.ruc_emisor}</td><td>{duplicado.emisor.ruc}</td></tr>
              <tr><td>RUC receptor</td><td>{valores.ruc_receptor}</td><td>{duplicado.receptor.ruc}</td></tr>
              <tr><td>Fecha</td><td>{valores.fecha_emision}</td><td>{duplicado.fecha_emision}</td></tr>
              <tr><td>Moneda</td><td>{valores.moneda}</td><td>{duplicado.moneda}</td></tr>
              <tr><td>Importe</td><td>{valores.importe_total}</td><td>{duplicado.importe_total}</td></tr>
            </tbody>
          </table>
          <Link to={`/expedientes/${duplicado.id}`}>Revisar expediente existente</Link>
          <p>La comparación es informativa. No se autoriza crear otro expediente ni contabilizar dos veces.</p>
        </div>
      )}
      </div>
      )}
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
