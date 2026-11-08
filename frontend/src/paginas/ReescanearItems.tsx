import { useRef, useState } from "react";
import { enviarJson, useDatos } from "../api";

type Preview = { facturas: number; con_lineas: number; sin_lineas: number; por_formato: Record<string, number>; lote_maximo: number; nota: string };
type Trabajo = { id: string; estado: string; total_documentos: number; procesados: number; lineas_nuevas: number; requieren_revision: number; errores: number; progreso: number; created_at: string; finalizado_at: string | null };

const RUTA_PREVIEW = "/api/v1/contabilidad-items/reescaneo/preview";
const RUTA_TRABAJOS = "/api/v1/contabilidad-items/reescaneo/trabajos";

export default function ReescanearItems() {
  const preview = useDatos<Preview>(RUTA_PREVIEW);
  const trabajos = useDatos<Trabajo[]>(RUTA_TRABAJOS);
  const [trabajo, setTrabajo] = useState<Trabajo | null>(null);
  const [trabajando, setTrabajando] = useState(false);
  const [pausar, setPausar] = useState(false);
  const [mensaje, setMensaje] = useState("");
  const pausarRef = useRef(false);
  const activo = trabajo?.estado === "EN_PROCESO" ? trabajo : trabajos.datos?.find((item) => item.estado === "EN_PROCESO");

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
        if (pausarRef.current) break;
      }
      trabajos.recargar();
      preview.recargar();
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
    const seleccionado = trabajo?.estado === "EN_PROCESO" ? trabajo : activo;
    if (!seleccionado) return;
    pausarRef.current = true;
    setPausar(true);
    try {
      const resultado = await enviarJson<Trabajo>(`${RUTA_TRABAJOS}/${seleccionado.id}/cancelar`, "POST");
      setTrabajo(resultado);
      trabajos.recargar();
      setMensaje("Trabajo cancelado. El progreso ya guardado se conserva.");
    } catch (fallo) {
      setMensaje(fallo instanceof Error ? fallo.message : String(fallo));
    }
  }

  return (
    <section aria-label="Reescanear ítems de facturas">
      <h2>Reescanear ítems</h2>
      <p>El proceso revisa las facturas activas del tenant en tandas pequeñas y conserva líneas, categorías confirmadas, expedientes y originales. Se guarda el avance para continuar si se cierra esta página. Extrae XML UBL y PDF/imágenes cuando existe una regla validada; actualmente, la regla PDF cubre un formato específico. Los demás documentos quedan para revisión manual.</p>
      {preview.error && <p role="alert">No se pudo calcular la vista previa: {preview.error}</p>}
      {preview.cargando && <p>Contando facturas y líneas…</p>}
      {preview.datos && <>
        <div role="group" aria-label="Alcance del reescaneo">
          <p><strong>Facturas activas:</strong> {preview.datos.facturas} · <strong>Con líneas:</strong> {preview.datos.con_lineas} · <strong>Sin líneas:</strong> {preview.datos.sin_lineas}</p>
          <p><strong>Por formato:</strong> XML {preview.datos.por_formato.XML ?? 0}, PDF {preview.datos.por_formato.PDF ?? 0}, imágenes {preview.datos.por_formato.IMAGEN ?? 0}, otros {preview.datos.por_formato.OTRO ?? 0}.</p>
          <p>{preview.datos.nota}</p>
        </div>
        <button type="button" disabled={trabajando || preview.datos.facturas === 0 || Boolean(activo)} onClick={() => void iniciar()}>Iniciar reescaneo de todas las facturas</button>
      </>}
      {activo && !trabajando && <button type="button" onClick={() => void procesarHastaPausa(activo)}>Continuar trabajo guardado</button>}
      {trabajando && <button type="button" onClick={detenerAlFinalDelLote}>Pausar al terminar esta factura</button>}
      {activo && <button type="button" disabled={trabajando && !pausar} onClick={() => void cancelar()}>Cancelar trabajo</button>}
      {mensaje && <p role="status">{mensaje}</p>}
      {(trabajo ?? activo) && <section aria-live="polite" aria-label="Progreso del reescaneo">
        <h3>Progreso: {(trabajo ?? activo)?.progreso}%</h3>
        <progress max={100} value={(trabajo ?? activo)?.progreso ?? 0} />
        <p>{(trabajo ?? activo)?.procesados} de {(trabajo ?? activo)?.total_documentos} facturas · {(trabajo ?? activo)?.lineas_nuevas} líneas agregadas · {(trabajo ?? activo)?.requieren_revision} para revisión · {(trabajo ?? activo)?.errores} errores</p>
        <p>Estado: {(trabajo ?? activo)?.estado}</p>
      </section>}
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
