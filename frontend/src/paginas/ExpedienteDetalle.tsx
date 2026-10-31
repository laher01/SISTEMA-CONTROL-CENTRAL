import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { eliminar, enviarFormulario, enviarJson, urlArchivo, urlPdfExpediente, urlZipExpediente, useDatos } from "../api";
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

export default function ExpedienteDetalle({ sesion }: { sesion: { rol: string } }) {
  const { id = "" } = useParams();
  const navegar = useNavigate();
  const { datos, error, cargando, recargar } = useDatos<Detalle>(`/api/v1/expedientes/${id}`);
  const { datos: capacidades } = useDatos<{ puede_retirar: boolean; puede_eliminar_definitivamente: boolean }>("/api/v1/documentos/capacidades");
  const { datos: solicitudes, recargar: recargarSolicitudes } = useDatos<SolicitudMISD[]>("/api/v1/misd/solicitudes");
  const [ocupado, setOcupado] = useState(false);
  const [mensajeAccion, setMensajeAccion] = useState("");
  const [errorAccion, setErrorAccion] = useState("");
  const solicitudActual = solicitudes?.find((solicitud) => solicitud.expediente_id === id);

  const eliminarDocumento = async (documento: Documento) => {
    if (!capacidades?.puede_eliminar_definitivamente || ocupado) return;
    const esUltimo = (datos?.documentos.length ?? 0) === 1;
    const confirmacion = window.confirm(
      `¿Eliminar definitivamente “${documento.nombre_original}”? Se borrará su archivo físico y se limpiarán sus vínculos y datos contables.${esUltimo ? " Es el último documento activo: también se eliminará el expediente." : " El expediente se conservará porque tiene otros documentos activos."} Esta acción no se puede deshacer.`,
    );
    if (!confirmacion) return;
    setOcupado(true);
    setErrorAccion("");
    setMensajeAccion("");
    try {
      const resultado = await eliminar(`/api/v1/documentos/${documento.id}`) as { estado?: string };
      if (resultado.estado === "pendiente") {
        setMensajeAccion("Documento eliminado; el archivo físico quedó pendiente en la cola de limpieza.");
      }
      if (esUltimo) {
        if (resultado.estado === "pendiente") window.alert("El expediente fue eliminado. El archivo físico quedó pendiente en la cola de limpieza.");
        navegar("/expedientes", { replace: true });
        return;
      }
      if (resultado.estado !== "pendiente") setMensajeAccion("Documento eliminado; el expediente conserva sus otros documentos.");
      recargar();
    } catch (e) {
      setErrorAccion(e instanceof Error ? e.message : String(e));
    } finally {
      setOcupado(false);
    }
  };

  const eliminarExpediente = async () => {
    if (!capacidades?.puede_eliminar_definitivamente || !datos || ocupado) return;
    const confirmacion = window.confirm(
      `¿Eliminar definitivamente el expediente ${datos.serie}-${datos.correlativo}? Se eliminarán ${datos.documentos.length} documento(s), archivos, vínculos y datos contables del expediente. No se puede deshacer.`,
    );
    if (!confirmacion) return;
    setOcupado(true);
    setErrorAccion("");
    try {
      const resultado = await eliminar(`/api/v1/expedientes/${datos.id}`) as { archivos_pendientes?: number };
      if ((resultado.archivos_pendientes ?? 0) > 0) {
        window.alert(`Expediente eliminado. ${resultado.archivos_pendientes} archivo(s) quedaron pendientes en la cola de limpieza física.`);
      }
      navegar("/expedientes", { replace: true });
    } catch (e) {
      setErrorAccion(e instanceof Error ? e.message : String(e));
    } finally {
      setOcupado(false);
    }
  };

  const solicitarRetiroMISD = async () => {
    if (!capacidades?.puede_retirar || sesion.rol !== "RESPONSABLE" || ocupado || !datos) return;
    const motivo = window.prompt("Motivo para solicitar a Administración la eliminación del expediente (mínimo 8 caracteres):");
    if (motivo === null) return;
    if (motivo.trim().length < 8) {
      setErrorAccion("Escribe un motivo de al menos 8 caracteres.");
      return;
    }
    if (!window.confirm("Se enviará una solicitud MISD a Administración. El expediente no se eliminará hasta que aprueben la solicitud y tú ejecutes el retiro. ¿Continuar?")) return;
    setOcupado(true);
    setErrorAccion("");
    setMensajeAccion("");
    try {
      await enviarJson("/api/v1/misd/solicitudes", "POST", { expediente_id: datos.id, motivo: motivo.trim() });
      setMensajeAccion("Solicitud enviada. Administración debe aprobarla antes de que puedas ejecutar el retiro.");
      recargarSolicitudes();
    } catch (e) {
      setErrorAccion(e instanceof Error ? e.message : String(e));
      recargarSolicitudes();
    } finally {
      setOcupado(false);
    }
  };

  const ejecutarRetiroMISD = async () => {
    if (!solicitudActual || sesion.rol !== "RESPONSABLE" || solicitudActual.estado !== "APROBADA" || ocupado) return;
    if (!window.confirm("Administración aprobó la solicitud. ¿Ejecutar ahora el retiro definitivo del expediente y todos sus documentos?")) return;
    setOcupado(true);
    setErrorAccion("");
    try {
      const resultado = await enviarJson<{ archivos_pendientes?: number }>(`/api/v1/misd/solicitudes/${solicitudActual.id}/ejecutar`, "POST");
      if ((resultado.archivos_pendientes ?? 0) > 0) {
        window.alert(`Retiro ejecutado. ${resultado.archivos_pendientes} archivo(s) quedaron pendientes en la cola de limpieza física.`);
      }
      navegar("/expedientes", { replace: true });
    } catch (e) {
      setErrorAccion(e instanceof Error ? e.message : String(e));
      recargarSolicitudes();
    } finally {
      setOcupado(false);
    }
  };

  return (
    <Estado cargando={cargando} error={error} vacio={!datos}>
      {datos && (
        <>
          <h2>
            {datos.tipo_comprobante === "RHE"
              ? numeroExpediente(datos.tipo_comprobante, datos.serie, datos.correlativo_original ?? datos.correlativo)
              : "FACT " + numeroExpediente(datos.tipo_comprobante, datos.serie, datos.correlativo_original ?? datos.correlativo)}{" "}
            <Semaforo estado={datos.estado} />
          </h2>
          {sesion.rol === "RESPONSABLE" && capacidades?.puede_retirar && (
            <section className="panel-configuracion" aria-label="Solicitud MISD de eliminación">
              <h3>Eliminación por aprobación MISD</h3>
              {solicitudActual ? (
                <p>Estado de la solicitud: <strong>{solicitudActual.estado}</strong>. <Link to="/aprobaciones-misd">Ver mis solicitudes MISD</Link></p>
              ) : <p>No hay una solicitud MISD para este expediente.</p>}
              {solicitudActual?.estado === "PENDIENTE" && <p>Administración debe aprobar o rechazar la solicitud.</p>}
              {solicitudActual?.estado === "APROBADA" && <button type="button" className="peligro" disabled={ocupado} onClick={() => void ejecutarRetiroMISD()}>Ejecutar retiro aprobado</button>}
              {(!solicitudActual || solicitudActual.estado === "RECHAZADA") && <button type="button" className="peligro" disabled={ocupado} onClick={() => void solicitarRetiroMISD()}>Solicitar eliminación a Administración</button>}
            </section>
          )}
          {sesion.rol === "ADMINISTRADOR" && solicitudActual && (
            <section className="panel-configuracion" aria-label="Estado de solicitud MISD">
              Solicitud MISD de Responsable: <strong>{solicitudActual.estado}</strong>. <Link to="/aprobaciones-misd">Abrir aprobaciones MISD</Link>
            </section>
          )}
          {capacidades?.puede_eliminar_definitivamente && <p><button type="button" className="peligro" disabled={ocupado} onClick={() => void eliminarExpediente()}>Eliminar expediente completo</button></p>}
          {mensajeAccion && <p role="status">{mensajeAccion}</p>}
          {errorAccion && <p role="alert" className="error">{errorAccion}</p>}
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

          {(datos.responsable_nombre || datos.usuario_nombre || datos.gestor_nombre) && (
            <section aria-label="Ruta de responsabilidad">
              <h3>Ruta de responsabilidad</h3>
              <dl className="ficha">
                <dt>Responsable</dt><dd>{datos.responsable_nombre ?? "Sin asignar"}</dd>
                <dt>Usuario</dt><dd>{datos.usuario_nombre ?? "Sin asignar"}</dd>
                <dt>Gestor</dt><dd>{datos.gestor_nombre ?? "Sin asignar"}</dd>
                <dt>Cliente</dt><dd>{datos.receptor.razon_social}</dd>
                <dt>Tipo proveedor</dt><dd>{datos.emisor.clasificacion_proveedor ?? "Sin clasificar"}</dd>
              </dl>
            </section>
          )}

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
          <TablaDocumentos documentos={datos.documentos} puedeEliminar={capacidades?.puede_eliminar_definitivamente ?? false} ocupado={ocupado} alEliminar={(documento) => void eliminarDocumento(documento)} />
          {sesion.rol === "GESTOR" && (
            <AgregarDocumento expedienteId={datos.id} sugerido={datos.faltantes[0]} alSubir={recargar} />
          )}
        </>
      )}
    </Estado>
  );
}

function TablaDocumentos({ documentos, puedeEliminar, ocupado, alEliminar }: { documentos: Documento[]; puedeEliminar: boolean; ocupado: boolean; alEliminar: (documento: Documento) => void }) {
  if (documentos.length === 0) return <p className="tenue">Sin documentos.</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>Tipo</th>
          <th>Archivo</th>
          <th>Tamaño</th>
          <th>Subido</th>
          {puedeEliminar && <th>Acciones</th>}
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
            {puedeEliminar && <td><button type="button" className="peligro" disabled={ocupado} onClick={() => alEliminar(d)}>Eliminar documento</button></td>}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

interface SolicitudMISD {
  id: string;
  expediente_id: string;
  estado: string;
  rol_solicitante: string;
  es_solicitante: boolean;
  motivo: string;
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
