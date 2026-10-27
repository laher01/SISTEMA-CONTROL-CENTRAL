import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { conParametros, eliminar, enviarJson, obtener, urlArchivo, urlPdfExpediente, urlZipExpediente, useDatos } from "../api";
import { Estado, Paginacion } from "../componentes";
import FiltroJerarquia from "../componentes/FiltroJerarquia";
import { formatearMonto } from "../formato";
import {
  ETIQUETA_ESTADO_DOCUMENTO,
  ETIQUETA_TIPO_DOCUMENTO,
  formatearFecha,
} from "../formato";
import {
  ESTADOS_DOCUMENTO,
  TIPOS_DOCUMENTO,
  type Documento,
  type SesionActual,
  type EstadoDocumento,
  type TipoDocumento,
} from "../tipos";

const POR_PAGINA = 50;
type ResultadoLote = {
  considerados: number;
  relacionados: number;
  revision_requerida: number;
  fallidos: number;
};

export default function Documentos({ sesion }: { sesion: SesionActual }) {
  const [parametros, setParametros] = useSearchParams();
  const responsableId = parametros.get("responsable_id") ?? "";
  const usuarioId = parametros.get("usuario_id") ?? "";
  const gestorId = parametros.get("gestor_id") ?? "";
  const estado = parametros.get("estado") ?? "";
  const tipoEmpresa = parametros.get("tipo_empresa") ?? "";
  const dia = parametros.get("dia") ?? "";
  const fechaEmision = parametros.get("fecha_emision") ?? "";
  const correlativoBusqueda = parametros.get("serie_correlativo") ?? "";
  const tipo = parametros.get("tipo_documento") ?? "";
  const emisor = parametros.get("emisor_ruc") ?? "";
  const receptor = parametros.get("receptor_ruc") ?? "";
  const desde = parametros.get("fecha_desde") ?? "";
  const hasta = parametros.get("fecha_hasta") ?? "";
  const mes = parametros.get("mes") ?? "";
  const pagina = Number(parametros.get("pagina") ?? "0");

  const ruta = conParametros("/api/v1/documentos", {
    estado,
    responsable_id: responsableId,
    usuario_id: usuarioId,
    gestor_id: gestorId,
    tipo_empresa: tipoEmpresa,
    dia,
    fecha_emision: fechaEmision,
    mes,
    serie_correlativo: correlativoBusqueda,
    tipo_documento: tipo,
    emisor_ruc: emisor.length === 11 ? emisor : undefined,
    receptor_ruc: receptor.length === 11 ? receptor : undefined,
    empresa_emisora: emisor.length === 11 ? undefined : emisor,
    empresa_receptora: receptor.length === 11 ? undefined : receptor,
    fecha_desde: desde,
    fecha_hasta: hasta,
    limit: String(POR_PAGINA),
    offset: String(pagina * POR_PAGINA),
  });
  const { datos, error, cargando, recargar } = useDatos<Documento[]>(ruta);
  const { datos: capacidades } = useDatos<{ puede_retirar: boolean; puede_restaurar: boolean }>(
    "/api/v1/documentos/capacidades",
  );
  const { datos: resumen } = useDatos<{
    total_documentos: number;
    total_expedientes: number;
    total_pen: string;
    total_usd: string;
  }>(conParametros("/api/v1/documentos/resumen", {
    estado,
    responsable_id: responsableId,
    usuario_id: usuarioId,
    gestor_id: gestorId,
    tipo_empresa: tipoEmpresa,
    dia,
    fecha_emision: fechaEmision,
    mes,
    serie_correlativo: correlativoBusqueda,
    tipo_documento: tipo,
    emisor_ruc: emisor.length === 11 ? emisor : undefined,
    receptor_ruc: receptor.length === 11 ? receptor : undefined,
    fecha_desde: desde,
    fecha_hasta: hasta,
  }));
  const [reprocesando, setReprocesando] = useState(false);
  const [resultadoLote, setResultadoLote] = useState<ResultadoLote>();
  const [errorLote, setErrorLote] = useState("");
  const [seleccionados, setSeleccionados] = useState<string[]>([]);
  const [eliminandoLote, setEliminandoLote] = useState(false);
  const [resultadoEliminacion, setResultadoEliminacion] = useState("");
  const [errorEliminacion, setErrorEliminacion] = useState("");
  const [retirados, setRetirados] = useState<Documento[] | null>(null);
  const [errorRetirados, setErrorRetirados] = useState("");
  const [cargandoRetirados, setCargandoRetirados] = useState(false);
  const [restaurandoId, setRestaurandoId] = useState("");

  const consultarRetirados = async () => {
    setCargandoRetirados(true);
    setErrorRetirados("");
    try {
      setRetirados(await obtener<Documento[]>("/api/v1/documentos/retirados?limit=100"));
    } catch (error) {
      setErrorRetirados(error instanceof Error ? error.message : String(error));
    } finally {
      setCargandoRetirados(false);
    }
  };

  const restaurarRetirado = async (documento: Documento) => {
    if (!window.confirm(`¿Restaurar ${documento.nombre_original}? Se verificará el archivo original.`)) return;
    setRestaurandoId(documento.id);
    setErrorRetirados("");
    try {
      await enviarJson<Documento>(`/api/v1/documentos/${documento.id}/restaurar`, "POST");
      await consultarRetirados();
      recargar();
    } catch (error) {
      setErrorRetirados(error instanceof Error ? error.message : String(error));
    } finally {
      setRestaurandoId("");
    }
  };

  const visibles = datos ?? [];
  const seleccionVisible = visibles.filter((documento) => seleccionados.includes(documento.id));
  const todosSeleccionados = visibles.length > 0 && seleccionVisible.length === visibles.length;

  const alternarDocumento = (id: string, marcado: boolean) => {
    setSeleccionados((actual) =>
      marcado ? [...new Set([...actual, id])] : actual.filter((x) => x !== id),
    );
  };

  const eliminarSeleccionados = async () => {
    const elegidos = seleccionVisible;
    if (!elegidos.length || eliminandoLote) return;
    try {
      const vista = await enviarJson<{
        aptos: number;
        resultados: { estado: string }[];
      }>(
        "/api/v1/documentos/previsualizar-retirada",
        "POST",
        { documentos_ids: elegidos.map((d) => d.id) },
      );
      if (vista.aptos !== elegidos.length) {
        const requiereMisd = vista.resultados.filter(
          (fila) => fila.estado === "REQUIERE_MISD",
        ).length;
        setErrorEliminacion(
          requiereMisd > 0
            ? `${requiereMisd} documento(s) requieren aprobación MISD antes del retiro.`
            : "La selección contiene documentos no disponibles. Actualice la bandeja.",
        );
        return;
      }
    } catch (error) {
      setErrorEliminacion(error instanceof Error ? error.message : String(error));
      return;
    }
    const confirmado = window.confirm(
      `¿Retirar ${elegidos.length} documento(s) de esta página? ` +
      "Se registrará una auditoría por cada archivo. Los originales no se borran físicamente.",
    );
    if (!confirmado) return;
    setEliminandoLote(true);
    setErrorEliminacion("");
    setResultadoEliminacion("");
    const retirados: string[] = [];
    const fallos: string[] = [];
    try {
      const resultado = await enviarJson<{
        retirados: number;
        resultados: { id: string; estado: string; codigo?: string }[];
      }>("/api/v1/documentos/retirar-lote", "POST", {
        documentos_ids: elegidos.map((d) => d.id),
      });
      for (const fila of resultado.resultados) {
        if (fila.estado === "RETIRADO") retirados.push(fila.id);
        else {
          const documento = elegidos.find((d) => d.id === fila.id);
          fallos.push(`${documento?.nombre_original ?? fila.id}: error ${fila.codigo ?? "desconocido"}`);
        }
      }
    } catch (error) {
      setErrorEliminacion(error instanceof Error ? error.message : String(error));
      setEliminandoLote(false);
      return;
    }
    setSeleccionados((actual) => actual.filter((id) => !retirados.includes(id)));
    setResultadoEliminacion(`${retirados.length} documento(s) retirado(s) de ${elegidos.length}.`);
    if (fallos.length) setErrorEliminacion(fallos.join(" | "));
    setEliminandoLote(false);
    recargar();
  };

  const reprocesarYCompletar = async () => {
    setReprocesando(true);
    setErrorLote("");
    try {
      const resultado = await enviarJson<ResultadoLote>(
        "/api/v1/documentos/procesar-pendientes?limit=100&forzar=true&completar_partes=true",
        "POST",
      );
      setResultadoLote(resultado);
      recargar();
    } catch (e) {
      setErrorLote(e instanceof Error ? e.message : String(e));
    } finally {
      setReprocesando(false);
    }
  };

  const cambiar = (clave: string, valor: string) => {
    setSeleccionados([]);
    const siguiente = new URLSearchParams(parametros);
    if (valor) siguiente.set(clave, valor);
    else siguiente.delete(clave);
    if (clave === "mes" && valor) siguiente.delete("fecha_emision");
    if (clave === "fecha_emision" && valor) siguiente.delete("mes");
    if (clave === "usuario_id") siguiente.delete("gestor_id");
    if (clave === "responsable_id") { siguiente.delete("usuario_id"); siguiente.delete("gestor_id"); }
    if (clave !== "pagina") siguiente.delete("pagina");
    setParametros(siguiente);
  };

  const limpiar = () => {
    setSeleccionados([]);
    setParametros({});
  };

  return (
    <>
      <div className="encabezado-pagina">
        <div>
          <h2>Documentos</h2>
          <p className="tenue">
            Bandeja central para revisar, filtrar, reprocesar y retirar documentos sin perder trazabilidad.
          </p>
        </div>
        <div className="acciones-documento">
          <button onClick={reprocesarYCompletar} disabled={reprocesando}>
            {reprocesando ? "Reprocesando…" : "Reprocesar y completar datos"}
          </button>
          <Link className="boton-enlace" to="/subir">Subir documentos</Link>
        </div>
      </div>

      {resultadoLote && (
        <p className="resumen-carga">
          {resultadoLote.considerados} revisados · {resultadoLote.relacionados} relacionados ·{" "}
          {resultadoLote.revision_requerida} requieren revisión · {resultadoLote.fallidos} fallidos
        </p>
      )}
      {errorLote && <p className="error">{errorLote}</p>}
      <div className="acciones-documento">
        <strong>{seleccionVisible.length} seleccionados en esta página</strong>
        <button
          className="peligro"
          disabled={!capacidades?.puede_retirar || !seleccionVisible.length || eliminandoLote}
          onClick={eliminarSeleccionados}
        >
          {eliminandoLote ? "Retirando documentos…" : "Eliminar seleccionados"}
        </button>
        <button
          className="secundario"
          disabled={!seleccionados.length || eliminandoLote}
          onClick={() => setSeleccionados([])}
        >Limpiar selección</button>
      </div>
      {capacidades?.puede_restaurar && <section aria-label="Documentos retirados">
        <button
          className="secundario"
          type="button"
          disabled={cargandoRetirados}
          onClick={() => {
            if (retirados !== null) setRetirados(null);
            else void consultarRetirados();
          }}
        >
          {cargandoRetirados ? "Consultando…" : retirados === null ? "Ver retirados" : "Ocultar retirados"}
        </button>
        {errorRetirados && <p role="alert" className="error">{errorRetirados}</p>}
        {retirados !== null && (
          <div className="panel-configuracion">
            <h3>Documentos retirados (hasta 100)</h3>
            <p>El original se conserva hasta que se autorice su eliminación definitiva.</p>
            {retirados.length === 0 && <p>No hay documentos retirados en su ámbito.</p>}
            {retirados.map((documento) => (
              <div key={documento.id} className="acciones-documento">
                <span>{documento.nombre_original}</span>
                <button
                  type="button"
                  className="secundario"
                  disabled={restaurandoId !== ""}
                  onClick={() => void restaurarRetirado(documento)}
                >
                  {restaurandoId === documento.id ? "Restaurando…" : "Restaurar"}
                </button>
              </div>
            ))}
          </div>
        )}
      </section>}
      {resultadoEliminacion && <p role="status">{resultadoEliminacion}</p>}
      {errorEliminacion && <p role="alert" className="error">{errorEliminacion}</p>}

      <div className="filtros filtros-documentos">
        <FiltroJerarquia sesion={sesion} responsableId={responsableId} usuarioId={usuarioId} gestorId={gestorId} cambiar={cambiar} />
        <select aria-label="Tipo de empresa" value={tipoEmpresa} onChange={(e) => cambiar("tipo_empresa", e.target.value)}>
          <option value="">Todas las empresas</option>
          <option value="A">Tipo A</option>
          <option value="B">Tipo B</option>
        </select>
        <input aria-label="Serie y correlativo" placeholder="Ej. EG07-2269" value={correlativoBusqueda} maxLength={60} onChange={(e) => cambiar("serie_correlativo", e.target.value.toUpperCase())} />
        <label className="filtro-fecha">Fecha documento <input type="date" value={fechaEmision} onChange={(e) => cambiar("fecha_emision", e.target.value)} /></label>
        <label className="filtro-fecha">Mes de emisión <input aria-label="Mes de emisión" type="month" value={mes} onChange={(e) => cambiar("mes", e.target.value)} /></label>
        <label className="filtro-fecha">Día de carga <input type="date" value={dia} onChange={(e) => cambiar("dia", e.target.value)} /></label>
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
          aria-label="Empresa emisora o proveedora"
          placeholder="Proveedor: RUC o razón social"
          value={emisor}
          maxLength={100}
          onChange={(e) => cambiar("emisor_ruc", e.target.value)}
        />
        <input
          aria-label="Empresa receptora o cliente"
          placeholder="Cliente: RUC o razón social"
          value={receptor}
          maxLength={100}
          onChange={(e) => cambiar("receptor_ruc", e.target.value)}
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

      <section className="panel-configuracion">
        <strong>Total del filtro completo (todas las páginas)</strong>
        <p>{resumen?.total_documentos ?? "…"} documentos · {resumen?.total_expedientes ?? "…"} expedientes distintos · {formatearMonto("PEN", resumen?.total_pen ?? "0")} · {formatearMonto("USD", resumen?.total_usd ?? "0")}</p>
      </section>
      <Estado cargando={cargando} error={error} vacio={datos?.length === 0}>
        <div className="tabla-responsive">
          <table>
            <thead>
              <tr>
                <th>
                  <input
                    type="checkbox"
                    aria-label="Seleccionar todos los documentos de esta página"
                    checked={todosSeleccionados}
                    disabled={eliminandoLote || !visibles.length}
                    onChange={(e) => setSeleccionados(
                      e.target.checked ? visibles.map((doc) => doc.id) : [],
                    )}
                  />
                </th>
                {!responsableId && <th>Responsable</th>}
                {!usuarioId && <th>Usuario</th>}
                {!gestorId && <th>Gestor</th>}
                <th>Estado</th>
                <th>Archivo</th>
                <th>Tipo</th>
                <th>Fecha documento</th>
                 <th>Fecha de carga</th>
                <th>Lectura</th>
                <th>Emisor</th>
                <th>Receptor</th>
                <th>Expediente</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {datos?.map((documento) => (
                <FilaDocumento key={documento.id} documento={documento}
                  seleccionado={seleccionados.includes(documento.id)}
                  alSeleccionar={(marcado) => alternarDocumento(documento.id, marcado)}
                  seleccionBloqueada={eliminandoLote}
                  alCambiar={recargar} mostrarResponsable={!responsableId} mostrarUsuario={!usuarioId} mostrarGestor={!gestorId} />
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
  seleccionado,
  alSeleccionar,
  seleccionBloqueada,
  mostrarResponsable,
  mostrarUsuario,
  mostrarGestor,
}: {
  documento: Documento;
  alCambiar: () => void;
  seleccionado: boolean;
  alSeleccionar: (marcado: boolean) => void;
  seleccionBloqueada: boolean;
  mostrarResponsable: boolean;
  mostrarUsuario: boolean;
  mostrarGestor: boolean;
}) {
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState("");
  const lectura = resumenLectura(documento);
  const importes = resumenImportesConfirmados(documento);
  const partes = resumenPartes(documento);

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
        <input type="checkbox" aria-label={`Seleccionar ${documento.nombre_original}`}
          checked={seleccionado} disabled={seleccionBloqueada}
          onChange={(e) => alSeleccionar(e.target.checked)} />
      </td>
      {mostrarResponsable && <td>{documento.responsable_nombre ?? "Sin asignar"}<small className="bloque tenue">{documento.responsable_codigo}</small></td>}
      {mostrarUsuario && <td>{documento.usuario_nombre ?? "Sin asignar"}<small className="bloque tenue">{documento.usuario_codigo}</small></td>}
      {mostrarGestor && <td>{documento.gestor_nombre ?? "Sin asignar"}<small className="bloque tenue">{documento.gestor_codigo}</small></td>}
      <td>
        <span className={`estado-documento estado-${documento.estado.toLowerCase()}`}>
          {ETIQUETA_ESTADO_DOCUMENTO[documento.estado as EstadoDocumento]}
        </span>
      </td>
      <td>
        <a href={urlArchivo(documento.id)} target="_blank" rel="noreferrer">
          {documento.nombre_original}
        </a>
        {documento.serie_documento && documento.correlativo_documento && (
          <small className="bloque tenue">{documento.serie_documento}-{documento.correlativo_documento}</small>
        )}
        {error && <small className="error bloque">{error}</small>}
      </td>
      <td>
        {documento.tipo_documento
          ? ETIQUETA_TIPO_DOCUMENTO[documento.tipo_documento as TipoDocumento]
          : "Sin clasificar"}
      </td>
      <td>{documento.fecha_documento ? formatearFecha(documento.fecha_documento) : "Pendiente de identificar"}</td>
       <td>{formatearFecha(documento.created_at)}</td>
      <td>
        {lectura ? (
          <span title={lectura.detalle}>{lectura.texto}</span>
        ) : (
          <span className="tenue">Sin lectura</span>
        )}
        {importes && <small className="bloque tenue">{importes}</small>}
      </td>
      <td>
        <ParteDocumento razonSocial={partes.emisor.razonSocial} ruc={partes.emisor.ruc} />
      </td>
      <td>
        <ParteDocumento razonSocial={partes.receptor.razonSocial} ruc={partes.receptor.ruc} />
      </td>
      <td>
        {documento.expediente_id ? (
          <><Link to={`/expedientes/${documento.expediente_id}`}>Ver expediente</Link>{" · "}<a href={urlZipExpediente(documento.expediente_id)}>ZIP</a>{" · "}<a href={urlPdfExpediente(documento.expediente_id)}>PDF</a></>
        ) : (
          <Link to={`/pendientes?estado=${documento.estado}`}>Revisar</Link>
        )}
      </td>
      <td>
        <div className="acciones-documento">
          <button disabled={ocupado} onClick={reprocesar}>Reprocesar</button>
          <button className="peligro" disabled={ocupado} onClick={retirar}>Eliminar</button>
        </div>
      </td>
    </tr>
  );
}

function resumenImportesConfirmados(documento: Documento): string | undefined {
  const datos = documento.datos_extraidos;
  const confirmacion = datos?.extraccion_confirmada;
  if (!confirmacion || typeof confirmacion !== "object" || !("campos" in confirmacion)) return undefined;
  const campos = confirmacion.campos;
  const total = leerValorCampo(campos, "importe_total");
  const moneda = documento.moneda || leerValorCampo(campos, "moneda");
  if (!total || (moneda !== "PEN" && moneda !== "USD")) return undefined;
  const detalle = [
    ["Subtotal", "subtotal"],
    ["IGV", "igv"],
    ["Descuentos", "descuentos"],
    ["A pagar", "importe_a_pagar"],
  ].flatMap(([etiqueta, clave]) => {
    const valor = clave ? leerValorCampo(campos, clave) : undefined;
    return valor ? [`${etiqueta}: ${formatearMonto(moneda, valor)}`] : [];
  });
  return [`Total confirmado: ${formatearMonto(moneda, total)}`, ...detalle].join(" · ");
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


function ParteDocumento({
  razonSocial,
  ruc,
}: {
  razonSocial?: string;
  ruc?: string;
}) {
  if (!razonSocial && !ruc) return <span className="tenue">Sin identificar</span>;
  return (
    <div>
      <strong>{razonSocial || "Razón social no extraída"}</strong>
      {ruc && <small className="bloque tenue">RUC {ruc}</small>}
    </div>
  );
}

function resumenPartes(documento: Documento): {
  emisor: { razonSocial?: string; ruc?: string };
  receptor: { razonSocial?: string; ruc?: string };
} {
  const datos = documento.datos_extraidos;
  if (!datos || typeof datos !== "object") {
    return { emisor: {}, receptor: {} };
  }

  const emisorXml = leerParteDirecta(datos.emisor);
  const receptorXml = leerParteDirecta(datos.receptor);

  const proceso = datos.procesamiento_documental;
  const extraccion =
    proceso && typeof proceso === "object" && "extraccion_estructurada" in proceso
      ? proceso.extraccion_estructurada
      : undefined;
  const campos =
    extraccion && typeof extraccion === "object" && "campos" in extraccion
      ? extraccion.campos
      : undefined;

  const confirmada = datos.extraccion_confirmada;
  const camposConfirmados =
    confirmada && typeof confirmada === "object" && "campos" in confirmada
      ? confirmada.campos
      : undefined;

  return {
    emisor: {
      razonSocial:
        (documento.emisor?.razon_social !== documento.emisor?.ruc
          ? documento.emisor?.razon_social
          : undefined) ||
        emisorXml.razonSocial ||
        leerValorCampo(camposConfirmados, "razon_social_emisor") ||
        leerValorCampo(campos, "razon_social_emisor"),
      ruc:
        documento.emisor?.ruc ||
        emisorXml.ruc ||
        leerValorCampo(camposConfirmados, "ruc_emisor") ||
        leerValorCampo(campos, "ruc_emisor"),
    },
    receptor: {
      razonSocial:
        (documento.receptor?.razon_social !== documento.receptor?.ruc
          ? documento.receptor?.razon_social
          : undefined) ||
        receptorXml.razonSocial ||
        leerValorCampo(camposConfirmados, "razon_social_receptor") ||
        leerValorCampo(campos, "razon_social_receptor"),
      ruc:
        documento.receptor?.ruc ||
        receptorXml.ruc ||
        leerValorCampo(camposConfirmados, "ruc_receptor") ||
        leerValorCampo(campos, "ruc_receptor"),
    },
  };
}

function leerParteDirecta(valor: unknown): { razonSocial?: string; ruc?: string } {
  if (!valor || typeof valor !== "object") return {};
  const parte = valor as Record<string, unknown>;
  return {
    razonSocial:
      typeof parte.razon_social === "string" && parte.razon_social.trim()
        ? parte.razon_social.trim()
        : undefined,
    ruc:
      typeof parte.ruc === "string" && parte.ruc.trim()
        ? parte.ruc.trim()
        : undefined,
  };
}

function leerValorCampo(campos: unknown, nombre: string): string | undefined {
  if (!campos || typeof campos !== "object") return undefined;
  const campo = (campos as Record<string, unknown>)[nombre];
  if (typeof campo === "string") return campo.trim() || undefined;
  if (!campo || typeof campo !== "object") return undefined;
  const valor = (campo as Record<string, unknown>).valor;
  return typeof valor === "string" && valor.trim() ? valor.trim() : undefined;
}
