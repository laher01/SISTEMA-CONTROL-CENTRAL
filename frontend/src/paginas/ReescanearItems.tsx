import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { enviarJson, urlArchivo, useDatos } from "../api";

type Preview = {
  facturas: number;
  por_tipo: Record<string, number>;
  con_lineas: number;
  sin_lineas: number;
  por_formato: Record<string, number>;
  lote_maximo: number;
  nota: string;
};
type Trabajo = {
  id: string;
  estado: string;
  total_documentos: number;
  procesados: number;
  lineas_nuevas: number;
  requieren_revision: number;
  errores: number;
  progreso: number;
  documento_actual_id: string | null;
  solicitado_por_rol: string;
  created_at: string;
  finalizado_at: string | null;
};
type FacturaVista = {
  documento_id: string;
  tipo_documento: string;
  comprobante: string;
  fecha_emision: string | null;
  emisor: string;
  ruta_jerarquica: string[];
};
type ItemVista = {
  linea_id: string;
  producto_id: string;
  descripcion: string;
  descripcion_original: string;
  unidad: string;
  categoria: string;
  categoria_sugerida: string;
  categoria_confirmada: boolean;
  factura: FacturaVista;
};
type Resultado = {
  trabajo: Trabajo;
  documento_actual: FacturaVista | null;
  ultima_factura: FacturaVista | null;
  items: ItemVista[];
  limite_items_visibles: number;
};
type Pendiente = {
  documento_id: string;
  nombre_original: string;
  tipo_documento: string;
  expediente_id: string | null;
  comprobante: string | null;
  fecha_emision: string | null;
  emisor: string | null;
};
type Categoria = { id: string; nombre: string; activa: boolean };
type Edicion = { categoria: string; descripcion: string };

const RUTA_PREVIEW = "/api/v1/contabilidad-items/reescaneo/preview";
const RUTA_TRABAJOS = "/api/v1/contabilidad-items/reescaneo/trabajos";
const RUTA_LINEAS = "/api/v1/contabilidad-items/lineas";

export default function ReescanearItems({ rol }: { rol: string }) {
  const preview = useDatos<Preview>(RUTA_PREVIEW);
  const [verPendientes, setVerPendientes] = useState(false);
  const [paginaPendientes, setPaginaPendientes] = useState(0);
  const pendientes = useDatos<Pendiente[]>(verPendientes
    ? `/api/v1/contabilidad-items/reescaneo/sin-lineas?offset=${paginaPendientes * 20}` : null);
  const trabajos = useDatos<Trabajo[]>(RUTA_TRABAJOS);
  const categorias = useDatos<Categoria[]>("/api/v1/contabilidad-items/categorias");
  const [trabajo, setTrabajo] = useState<Trabajo | null>(null);
  const [trabajando, setTrabajando] = useState(false);
  const [pausar, setPausar] = useState(false);
  const [mensaje, setMensaje] = useState("");
  const [ediciones, setEdiciones] = useState<Record<string, Edicion>>({});
  const [guardando, setGuardando] = useState<string | null>(null);
  const pausarRef = useRef(false);
  const activo = trabajo?.estado === "EN_PROCESO" ? trabajo : trabajos.datos?.find((item) => item.estado === "EN_PROCESO");
  const observado = trabajo ?? activo;
  const rutaResultado = observado ? `${RUTA_TRABAJOS}/${observado.id}/resultado` : null;
  const resultado = useDatos<Resultado>(rutaResultado);
  const recargarResultado = resultado.recargar;
  const alcanceTenant = rol === "ADMINISTRADOR" || rol === "SECRETARIA";

  useEffect(() => {
    if (!trabajando || !rutaResultado) return;
    const intervalo = window.setInterval(() => recargarResultado(), 900);
    return () => window.clearInterval(intervalo);
  }, [trabajando, rutaResultado, recargarResultado]);

  async function procesarHastaPausa(inicial: Trabajo) {
    if (trabajando) return;
    setTrabajando(true);
    setPausar(false);
    pausarRef.current = false;
    setMensaje("");
    let actual = inicial;
    setTrabajo(actual);
    try {
      while (actual.estado === "EN_PROCESO") {
        actual = await enviarJson<Trabajo>(`${RUTA_TRABAJOS}/${actual.id}/lote`, "POST", undefined);
        setTrabajo(actual);
        recargarResultado();
        if (pausarRef.current) break;
      }
      trabajos.recargar();
      preview.recargar();
      recargarResultado();
      if (actual.estado !== "EN_PROCESO") setMensaje(`Reescaneo ${actual.estado.toLowerCase().replaceAll("_", " ")}.`);
    } catch (fallo) {
      setMensaje(fallo instanceof Error ? fallo.message : String(fallo));
    } finally {
      setTrabajando(false);
      setPausar(false);
    }
  }

  async function iniciar() {
    if (!preview.datos || preview.datos.facturas === 0) return;
    setMensaje("");
    try {
      const nuevo = await enviarJson<Trabajo>(RUTA_TRABAJOS, "POST");
      setTrabajo(nuevo);
      trabajos.recargar();
      await procesarHastaPausa(nuevo);
    } catch (fallo) {
      setMensaje(fallo instanceof Error ? fallo.message : String(fallo));
    }
  }

  function detenerAlFinalDelLote() {
    pausarRef.current = true;
    setPausar(true);
  }

  async function cancelar() {
    if (!activo) return;
    pausarRef.current = true;
    setPausar(true);
    try {
      const actualizado = await enviarJson<Trabajo>(`${RUTA_TRABAJOS}/${activo.id}/cancelar`, "POST");
      setTrabajo(actualizado);
      trabajos.recargar();
      setMensaje("Trabajo cancelado. Se conserva el avance guardado.");
    } catch (fallo) {
      setMensaje(fallo instanceof Error ? fallo.message : String(fallo));
    }
  }

  function valorEdicion(item: ItemVista): Edicion {
    return ediciones[item.linea_id] ?? {
      categoria: item.categoria_confirmada ? item.categoria : item.categoria_sugerida,
      descripcion: item.descripcion,
    };
  }

  async function guardarItem(item: ItemVista) {
    const edicion = valorEdicion(item);
    setGuardando(item.linea_id);
    setMensaje("");
    try {
      await enviarJson(`${RUTA_LINEAS}/${item.linea_id}/clasificacion`, "PATCH", edicion);
      setMensaje(`Ítem guardado: ${edicion.descripcion}`);
      setEdiciones((actual) => Object.fromEntries(
        Object.entries(actual).filter(([lineaId]) => lineaId !== item.linea_id),
      ) as Record<string, Edicion>);
      categorias.recargar();
      recargarResultado();
    } catch (fallo) {
      setMensaje(fallo instanceof Error ? fallo.message : String(fallo));
    } finally {
      setGuardando(null);
    }
  }

  const vista = resultado.datos;
  const facturaActiva = vista?.documento_actual;
  const facturaReciente = vista?.ultima_factura;
  const trabajoVista = vista?.trabajo ?? observado;

  return (
    <section aria-label="Reescanear ítems de comprobantes">
      <h2>Reescanear ítems</h2>
      <p>El reescaneo revisa facturas y recibos por honorarios del ámbito que tienes autorizado. Guarda cada comprobante por separado; conserva los documentos, los expedientes y las categorías confirmadas manualmente.</p>
      {preview.error && <p role="alert">No se pudo calcular la vista previa: {preview.error}</p>}
      {preview.cargando && <p>Contando comprobantes y líneas…</p>}
      {preview.datos && <>
        <div role="group" aria-label="Alcance del reescaneo">
          <p><strong>Ámbito:</strong> {alcanceTenant ? "Tenant completo" : "Tu cartera según jerarquía"}</p>
          <p><strong>Comprobantes activos:</strong> {preview.datos.facturas} · <strong>Facturas:</strong> {preview.datos.por_tipo.FACT ?? 0} · <strong>Recibos por honorarios:</strong> {preview.datos.por_tipo.RHE ?? 0}</p>
          <p><strong>Con líneas:</strong> {preview.datos.con_lineas} · <strong>Sin líneas:</strong> {preview.datos.sin_lineas}</p>
          <button type="button" aria-expanded={verPendientes} onClick={() => {
            setPaginaPendientes(0);
            setVerPendientes(!verPendientes);
            if (!verPendientes) pendientes.recargar();
          }}>{verPendientes ? "Ocultar comprobantes sin líneas" : `Ver comprobantes sin líneas (${preview.datos.sin_lineas})`}</button>
          <p><strong>Por formato:</strong> XML {preview.datos.por_formato.XML ?? 0}, PDF {preview.datos.por_formato.PDF ?? 0}, imágenes {preview.datos.por_formato.IMAGEN ?? 0}, otros {preview.datos.por_formato.OTRO ?? 0}.</p>
          <p>{preview.datos.nota}</p>
        </div>
        <button type="button" disabled={trabajando || preview.datos.facturas === 0 || Boolean(activo)} onClick={() => void iniciar()}>
          Iniciar reescaneo de {alcanceTenant ? "todos los comprobantes" : "mis comprobantes autorizados"}
        </button>
      </>}
      {verPendientes && <section aria-label="Comprobantes sin líneas">
        <h3>Comprobantes sin líneas</h3>
        <p>Lista actual de comprobantes sin ítems registrados.</p>
        {pendientes.cargando && <p role="status">Cargando comprobantes…</p>}
        {pendientes.error && <p role="alert">{pendientes.error}</p>}
        {pendientes.datos?.length === 0 && <p>No hay comprobantes en esta página.</p>}
        {!!pendientes.datos?.length && <table>
          <thead><tr><th>Comprobante</th><th>Fecha</th><th>Emisor</th><th>Archivo</th><th>Expediente</th></tr></thead>
          <tbody>{pendientes.datos.slice(0, 20).map((fila) => <tr key={fila.documento_id}>
            <td>{fila.tipo_documento} {fila.comprobante ?? "Sin expediente"}</td>
            <td>{fila.fecha_emision ?? "—"}</td><td>{fila.emisor ?? "—"}</td>
            <td><a href={urlArchivo(fila.documento_id)} target="_blank" rel="noreferrer">{fila.nombre_original}</a></td>
            <td>{fila.expediente_id && <Link to={`/expedientes/${fila.expediente_id}`}>Abrir expediente</Link>}</td>
          </tr>)}</tbody>
        </table>}
        <button type="button" disabled={!paginaPendientes || pendientes.cargando} onClick={() => setPaginaPendientes(paginaPendientes - 1)}>Anterior</button>
        <button type="button" disabled={pendientes.cargando || (pendientes.datos?.length ?? 0) <= 20} onClick={() => setPaginaPendientes(paginaPendientes + 1)}>Siguiente</button>
        <button type="button" onClick={() => { pendientes.recargar(); preview.recargar(); }}>Actualizar lista</button>
      </section>}
      {activo && !trabajando && <button type="button" onClick={() => void procesarHastaPausa(activo)}>Continuar trabajo guardado</button>}
      {trabajando && <button type="button" disabled={pausar} onClick={detenerAlFinalDelLote}>Pausar al terminar este comprobante</button>}
      {activo && <button type="button" disabled={trabajando && !pausar} onClick={() => void cancelar()}>Cancelar trabajo</button>}
      {mensaje && <p role="status">{mensaje}</p>}

      {trabajoVista && <section aria-live="polite" aria-label="Progreso del reescaneo">
        <h3>Progreso: {trabajoVista.progreso}%</h3>
        <progress max={100} value={trabajoVista.progreso} />
        <p>{trabajoVista.procesados} de {trabajoVista.total_documentos} comprobantes · {trabajoVista.lineas_nuevas} líneas nuevas · {trabajoVista.requieren_revision} para revisión · {trabajoVista.errores} errores</p>
        <p>Estado: {trabajoVista.estado}</p>
        {facturaActiva && <div role="status" aria-label="Comprobante en proceso">
          <h4>Procesando ahora</h4>
          <p><strong>{facturaActiva.tipo_documento} {facturaActiva.comprobante}</strong>{facturaActiva.fecha_emision ? ` · ${facturaActiva.fecha_emision}` : ""}{facturaActiva.emisor ? ` · ${facturaActiva.emisor}` : ""}</p>
          <p>Ruta jerárquica: {facturaActiva.ruta_jerarquica.join(" › ")}</p>
        </div>}
        {!facturaActiva && facturaReciente && <div aria-label="Último comprobante procesado">
          <h4>Último comprobante procesado</h4>
          <p><strong>{facturaReciente.tipo_documento} {facturaReciente.comprobante}</strong>{facturaReciente.fecha_emision ? ` · ${facturaReciente.fecha_emision}` : ""}{facturaReciente.emisor ? ` · ${facturaReciente.emisor}` : ""}</p>
          <p>Ruta jerárquica: {facturaReciente.ruta_jerarquica.join(" › ")}</p>
        </div>}
      </section>}

      {resultado.error && observado && <p role="alert">No se pudo actualizar la factura actual: {resultado.error}</p>}
      {vista?.items.length ? <section aria-live="polite" aria-label="Ítems encontrados durante el reescaneo">
        <h3>Ítems encontrados ({vista.items.length}{vista.items.length === vista.limite_items_visibles ? "+" : ""})</h3>
        <p>La lista se actualiza mientras avanza cada comprobante. Las descripciones originales quedan intactas; aquí puedes ajustar la descripción del catálogo y confirmar o crear una categoría.</p>
        <div style={{ overflowX: "auto" }}><table>
          <thead><tr><th>Comprobante / jerarquía</th><th>Descripción</th><th>Categoría sugerida</th><th>Elegir o agregar categoría</th><th>Acción</th></tr></thead>
          <tbody>{vista.items.map((item) => {
            const edicion = valorEdicion(item);
            const opciones = new Set((categorias.datos ?? []).filter((categoria) => categoria.activa).map((categoria) => categoria.nombre));
            opciones.add(item.categoria_sugerida);
            return <tr key={item.linea_id}>
              <td><strong>{item.factura.tipo_documento} {item.factura.comprobante}</strong><br />{item.factura.fecha_emision ?? "Fecha no disponible"}<br /><small>{item.factura.ruta_jerarquica.join(" › ")}</small></td>
              <td><label><span className="solo-lectores">Descripción del ítem</span><textarea maxLength={2000} rows={3} value={edicion.descripcion} onChange={(evento) => setEdiciones((actual) => ({ ...actual, [item.linea_id]: { ...edicion, descripcion: evento.target.value } }))} /></label><small>Original: {item.descripcion_original}</small></td>
              <td>{item.categoria_sugerida}{item.categoria_confirmada ? " · confirmada manualmente" : " · sugerencia"}</td>
              <td><input list={`categorias-${item.linea_id}`} aria-label={`Categoría de ${item.descripcion}`} maxLength={80} value={edicion.categoria} onChange={(evento) => setEdiciones((actual) => ({ ...actual, [item.linea_id]: { ...edicion, categoria: evento.target.value } }))} /><datalist id={`categorias-${item.linea_id}`}>{[...opciones].map((nombre) => <option key={nombre} value={nombre} />)}</datalist><small>Selecciona una existente o escribe una nueva.</small></td>
              <td><button type="button" disabled={guardando === item.linea_id || !edicion.categoria.trim() || edicion.descripcion.trim().length < 2} onClick={() => void guardarItem(item)}>{guardando === item.linea_id ? "Guardando…" : "Guardar"}</button></td>
            </tr>;
          })}</tbody>
        </table></div>
      </section> : vista && trabajoVista && trabajoVista.procesados > 0 && <p>No se encontraron líneas extraíbles en los últimos comprobantes procesados; quedaron marcados para revisión.</p>}

      {trabajos.error && <p role="alert">No se pudo cargar el historial: {trabajos.error}</p>}
      {trabajos.datos && trabajos.datos.length > 0 && <>
        <h3>Trabajos recientes</h3>
        <div style={{ overflowX: "auto" }}><table>
          <thead><tr><th>Inicio</th><th>Estado</th><th>Progreso</th><th>Líneas nuevas</th><th>Revisión</th><th>Errores</th></tr></thead>
          <tbody>{trabajos.datos.map((item) => <tr key={item.id}>
            <td>{new Date(item.created_at).toLocaleString()}</td><td>{item.estado}</td>
            <td>{item.procesados}/{item.total_documentos} ({item.progreso}%)</td><td>{item.lineas_nuevas}</td><td>{item.requieren_revision}</td><td>{item.errores}</td>
          </tr>)}</tbody>
        </table></div>
      </>}
    </section>
  );
}
