import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { conParametros, eliminar, enviarJson, urlArchivo, urlPdfExpediente, urlZipExpediente, useDatos } from "../api";
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
  const { datos: capacidades } = useDatos<{ puede_retirar: boolean; puede_eliminar_definitivamente: boolean }>(
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
        resultados: { id: string; estado: string }[];
      }>(
        "/api/v1/documentos/previsualizar-retirada",
        "POST",
        { documentos_ids: elegidos.map((d) => d.id) },
      );
      const estadoPorId = new Map(vista.resultados.map((fila) => [fila.id, fila.estado]));
      const requierenMisd = elegidos.filter(
        (documento) => estadoPorId.get(documento.id) === "REQUIERE_MISD",
      );

      if (requierenMisd.length > 0) {
        const expedientesConBloqueo = new Set(
          elegidos
            .filter((documento) => {
              const estado = estadoPorId.get(documento.id);
              return estado !== "REQUIERE_MISD" && estado !== "APTO_ELIMINACION";
            })
            .map((documento) => documento.expediente_id)
            .filter((id): id is string => Boolean(id)),
        );
        const expedientesSolicitables = [...new Set(
          requierenMisd
            .map((documento) => documento.expediente_id)
            .filter((id): id is string => Boolean(id))
            .filter((id) => !expedientesConBloqueo.has(id)),
        )];
        const sinExpediente = requierenMisd.filter((documento) => !documento.expediente_id).length;
        const bloqueadosMisd = [...new Set(
          requierenMisd
            .map((documento) => documento.expediente_id)
            .filter((id): id is string => Boolean(id))
            .filter((id) => expedientesConBloqueo.has(id)),
        )].length;

        if (expedientesSolicitables.length === 0) {
          setErrorEliminacion(
            "No se creó ninguna solicitud: los expedientes seleccionados están bloqueados o no tienen expediente asociado.",
          );
          return;
        }

        const motivo = window.prompt(
          "Motivo para las " + expedientesSolicitables.length +
            " solicitudes MISD (mínimo 8 caracteres):",
        );
        if (motivo === null) return;
        if (motivo.trim().length < 8) {
          setErrorEliminacion("Escribe un motivo de al menos 8 caracteres.");
          return;
        }
        const expedientesFuera = elegidos.filter(
          (documento) => !documento.expediente_id ||
            !expedientesSolicitables.includes(documento.expediente_id),
        ).length;
        const confirmado = window.confirm(
          "Se enviará una solicitud MISD por cada uno de los " +
            expedientesSolicitables.length +
            " expedientes. Cada solicitud abarca el expediente completo y todos sus documentos vinculados. " +
            "Esto no borra archivos ahora." +
            (expedientesFuera > 0
              ? " " + expedientesFuera +
                " documento(s) de otros expedientes o bloqueados quedarán sin cambios."
              : "") +
            " ¿Deseas continuar?",
        );
        if (!confirmado) return;

        setEliminandoLote(true);
        setErrorEliminacion("");
        setResultadoEliminacion("");
        const expedientesEnviados = new Set<string>();
        const fallidos: string[] = [];
        let creadas = 0;
        let yaPendientes = 0;
        try {
          for (const expedienteId of expedientesSolicitables) {
            try {
              await enviarJson("/api/v1/misd/solicitudes", "POST", {
                expediente_id: expedienteId,
                motivo: motivo.trim(),
              });
              creadas += 1;
              expedientesEnviados.add(expedienteId);
            } catch (error) {
              const mensaje = error instanceof Error ? error.message : String(error);
              if (mensaje.includes("Ya existe una solicitud pendiente")) {
                yaPendientes += 1;
                expedientesEnviados.add(expedienteId);
              } else {
                fallidos.push(expedienteId + ": " + mensaje);
              }
            }
          }
        } finally {
          setEliminandoLote(false);
        }

        const documentosTramitados = new Set(
          elegidos
            .filter((documento) =>
              documento.expediente_id && expedientesEnviados.has(documento.expediente_id),
            )
            .map((documento) => documento.id),
        );
        setSeleccionados((actual) =>
          actual.filter((id) => !documentosTramitados.has(id)),
        );
        setResultadoEliminacion(
          creadas + " solicitud(es) MISD enviada(s)" +
            (yaPendientes ? " · " + yaPendientes + " ya estaban pendientes" : "") +
            ". Administración debe aprobarlas; después el Responsable solicitante ejecuta el retiro." +
            (expedientesFuera > 0
              ? " " + expedientesFuera + " documento(s) quedaron seleccionados sin cambios."
              : ""),
        );
        if (fallidos.length || sinExpediente || bloqueadosMisd) {
          setErrorEliminacion(
            (fallidos.length
              ? fallidos.length + " solicitud(es) no se pudieron enviar: " +
                fallidos.slice(0, 5).join(" | ")
              : "") +
              (sinExpediente
                ? (fallidos.length ? " · " : "") + sinExpediente +
                  " documento(s) requieren MISD pero no tienen expediente asociado."
                : "") +
              (bloqueadosMisd
                ? (fallidos.length || sinExpediente ? " · " : "") + bloqueadosMisd +
                  " expediente(s) quedaron fuera por tener documentos bloqueados."
                : ""),
          );
        }
        if (expedientesEnviados.size > 0) recargar();
        return;
      }

      if (vista.aptos !== elegidos.length) {
        const bloqueados = vista.resultados.filter(
          (fila) => fila.estado !== "APTO_ELIMINACION",
        ).length;
        setErrorEliminacion(
          bloqueados > 0
            ? bloqueados + " documento(s) no se pueden eliminar ahora por bloqueos o falta de disponibilidad."
            : "La selección contiene documentos no disponibles. Actualice la bandeja.",
        );
        return;
      }
    } catch (error) {
      setErrorEliminacion(error instanceof Error ? error.message : String(error));
      return;
    }
    const nombres = elegidos.slice(0, 20)
      .map((documento) => "• " + documento.nombre_original).join("\n");
    const mas = elegidos.length > 20 ? "\n…y " + (elegidos.length - 20) + " más" : "";
    const confirmado = window.confirm([
      "Eliminar definitivamente " + elegidos.length + " documento(s)?",
      nombres,
      mas,
      "Se quitarán de contabilidad y se borrarán los archivos físicos. No se pueden restaurar.",
    ].filter(Boolean).join("\n"));
    if (!confirmado) return;
    setEliminandoLote(true);
    setErrorEliminacion("");
    setResultadoEliminacion("");
    const eliminados: string[] = [];
    let pendientesFisicos = 0;
    const fallos: string[] = [];
    try {
      const resultado = await enviarJson<{
        eliminados: number;
        resultados: { id: string; estado: string; codigo?: string }[];
      }>("/api/v1/documentos/retirar-lote", "POST", {
        documentos_ids: elegidos.map((d) => d.id),
      });
      for (const fila of resultado.resultados) {
        if (fila.estado === "ELIMINADO" || fila.estado === "ELIMINADO_ARCHIVO_PENDIENTE") {
          eliminados.push(fila.id);
          if (fila.estado === "ELIMINADO_ARCHIVO_PENDIENTE") pendientesFisicos += 1;
        } else {
          const documento = elegidos.find((d) => d.id === fila.id);
          fallos.push((documento?.nombre_original ?? fila.id) + ": error " + (fila.codigo ?? "desconocido"));
        }
      }
    } catch (error) {
      setErrorEliminacion(error instanceof Error ? error.message : String(error));
      setEliminandoLote(false);
      return;
    }
    setSeleccionados((actual) => actual.filter((id) => !eliminados.includes(id)));
    setResultadoEliminacion(
      eliminados.length + " de " + elegidos.length + " eliminados." +
      (pendientesFisicos ? " " + pendientesFisicos + " archivo(s) siguen pendientes de borrado físico." : ""),
    );
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
            Bandeja para revisar registros, filtrar expedientes y resolver correcciones de documentos.
          </p>
        </div>
        <div className="acciones-documento">
          <button onClick={reprocesarYCompletar} disabled={reprocesando}>
            {reprocesando ? "Reprocesando…" : "Reprocesar y completar datos"}
          </button>
          {sesion.rol === "GESTOR" && <Link className="boton-enlace" to="/subir">Subir documentos</Link>}
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
          {eliminandoLote ? "Eliminando documentos…" : "Eliminar seleccionados"}
        </button>
        <button
          className="secundario"
          disabled={!seleccionados.length || eliminandoLote}
          onClick={() => setSeleccionados([])}
        >Limpiar selección</button>
      </div>
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
                  sesion={sesion}
                  alCambiar={recargar} mostrarResponsable={!responsableId} mostrarUsuario={!usuarioId} mostrarGestor={!gestorId} />
              ))}
            </tbody>
          </table>
        </div>
      </Estado>

      <Paginacion
        pagina={pagina}
        hayMas={(datos?.length ?? 0) === POR_PAGINA}
        total={resumen?.total_documentos}
        porPagina={POR_PAGINA}
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
  sesion,
}: {
  documento: Documento;
  sesion: SesionActual;
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
  const [mensajeMisd, setMensajeMisd] = useState("");
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

  const solicitarRetiroMisd = async () => {
    if (!documento.expediente_id || ocupado) return;
    const motivo = window.prompt("Motivo para solicitar el retiro MISD (mínimo 8 caracteres):");
    if (motivo === null) return;
    if (motivo.trim().length < 8) {
      setError("Escribe un motivo de al menos 8 caracteres.");
      return;
    }
    const confirmado = window.confirm(
      "La solicitud retirará el expediente completo y todos sus documentos vinculados. ¿Deseas continuar?",
    );
    if (!confirmado) return;
    setOcupado(true);
    setError("");
    setMensajeMisd("");
    try {
      await enviarJson("/api/v1/misd/solicitudes", "POST", {
        expediente_id: documento.expediente_id,
        motivo: motivo.trim(),
      });
      setMensajeMisd("Solicitud MISD enviada. Consulta su estado en Aprobaciones MISD.");
      alCambiar();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setOcupado(false);
    }
  };

  const eliminarDocumento = async () => {
    const confirmado = window.confirm(
      `¿Eliminar definitivamente "${documento.nombre_original}"? Se quitará de contabilidad y se borrará el archivo físico. No se puede restaurar.`,
    );
    if (!confirmado) return;
    setOcupado(true);
    setError("");
    try {
      const resultado = (await eliminar(`/api/v1/documentos/${documento.id}`)) as {
        estado?: string;
      };
      if (resultado.estado === "pendiente") {
        setError("El registro se eliminó; el borrado físico del archivo está pendiente.");
      }
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
        {mensajeMisd && <small role="status" className="bloque">{mensajeMisd}</small>}
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
          {sesion.rol === "RESPONSABLE" ? (
            <button className="secundario" disabled={ocupado || !documento.expediente_id} onClick={solicitarRetiroMisd}>
              Solicitar aprobación para eliminar expediente
            </button>
          ) : ["ADMINISTRADOR", "GESTOR", "USUARIO"].includes(sesion.rol) ? (
            <button className="peligro" disabled={ocupado} onClick={eliminarDocumento}>
              Eliminar definitivamente
            </button>
          ) : null}
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
