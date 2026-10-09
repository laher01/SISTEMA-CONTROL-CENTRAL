import { useRef, useState, type FormEvent } from "react";

import { enviarJson, useDatos } from "../api";
import { Estado } from "../componentes";

const BASE = "/api/v1/infraestructura";
interface Operacion {
  id: string; nodo_id: string; tipo: string; estado: string; creada_at: string;
  grupo_id: string | null; orden: number; resultado: { codigo_error?: string } | null;
}
interface Backup {
  id: string; nodo_id: string; estado: string; objeto: string; sha256: string;
  fecha: string; bytes: number; retencion_dias: number; restauracion_verificada_at: string | null;
}
interface Version { id: string; version: string; entorno: string; aprobacion: string }

export default function OperacionesInfraestructura() {
  const operaciones = useDatos<{ habilitadas: boolean; produccion_habilitada: boolean; operaciones: Operacion[] }>(`${BASE}/operaciones`);
  const backups = useDatos<Backup[]>(`${BASE}/backups`);
  const nodos = useDatos<{ id: string; codigo: string; activo: boolean; entorno: string }[]>(`${BASE}/nodos`);
  const versiones = useDatos<Version[]>(`${BASE}/versiones`);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState("");
  const [mensaje, setMensaje] = useState("");
  const solicitud = useRef<{ contenido: string; id: string } | null>(null);
  const recargar = () => { operaciones.recargar(); backups.recargar(); versiones.recargar(); nodos.recargar(); };
  const operar = async (accion: () => Promise<unknown>, exito: string) => {
    setError(""); setMensaje(""); setOcupado(true);
    try { await accion(); setMensaje(exito); recargar(); }
    catch(e) { setError(e instanceof Error ? e.message : "Operación no completada"); }
    finally { setOcupado(false); }
  };
  const solicitar = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const tipo = String(form.get("tipo"));
    const datos = {
      nodo_id: form.get("nodo_id"),
      ...(tipo !== "backups" ? { version_id: form.get("version_id"), backup_id: form.get("backup_id") || null } : {}),
    };
    const contenido = JSON.stringify({tipo, datos});
    if (solicitud.current?.contenido !== contenido) solicitud.current = {contenido, id: crypto.randomUUID()};
    const id = solicitud.current.id;
    void operar(async () => {
      await enviarJson(`${BASE}/${tipo}`, "POST", {...datos, solicitud_id: id});
      solicitud.current = null;
    }, "Solicitud registrada. El agente debe ejecutar y verificar la operación para completarla.");
  };
  return <section className="panel-configuracion">
    <div className="acciones"><h3>Despliegues y recuperación</h3><button disabled={ocupado} onClick={recargar}>Actualizar operaciones</button></div>
    {error && <p className="error" role="alert">{error}</p>}
    {mensaje && <p role="status">{mensaje}</p>}
    <Estado cargando={operaciones.cargando} error={operaciones.error}>
      {!operaciones.datos?.habilitadas && <p className="tenue">La ejecución está deshabilitada. Se habilita después de validar el agente en staging.</p>}
      {!operaciones.datos?.produccion_habilitada && <p className="tenue">Las operaciones productivas están bloqueadas.</p>}
      <div className="infra-tabla"><table><thead><tr><th>Fecha</th><th>Operación</th><th>Nodo</th><th>Estado</th><th>Resultado</th></tr></thead>
        <tbody>{operaciones.datos?.operaciones.map(o => <tr key={o.id}>
          <td>{new Date(o.creada_at).toLocaleString("es-PE")}</td><td>{o.tipo}{o.grupo_id && ` · lote, paso ${o.orden + 1}`}</td>
          <td>{nodos.datos?.find(n => n.id === o.nodo_id)?.codigo ?? o.nodo_id}</td><td>{o.estado}</td><td>{o.resultado?.codigo_error ?? "—"}</td>
        </tr>)}</tbody></table></div>
    </Estado>
    <details><summary>Solicitar una operación autorizada</summary>
      <form className="infra-formulario" onSubmit={solicitar}>
        <label>Operación<select name="tipo"><option value="despliegues">Despliegue</option><option value="backups">Backup cifrado</option><option value="rollback-imagen">Rollback de imágenes</option></select></label>
        <label>Nodo<select name="nodo_id" required><option value="">Seleccionar</option>{nodos.datos?.filter(n => n.activo).map(n => <option key={n.id} value={n.id}>{n.codigo} · {n.entorno}</option>)}</select></label>
        <label>Versión (para imágenes)<select name="version_id"><option value="">Seleccionar</option>{versiones.datos?.filter(v => v.aprobacion === "APROBADA").map(v => <option key={v.id} value={v.id}>{v.version} · {v.entorno}</option>)}</select></label>
        <label>Backup para migración<select name="backup_id"><option value="">Sin backup</option>{backups.datos?.filter(b => b.restauracion_verificada_at).map(b => <option key={b.id} value={b.id}>{b.objeto}</option>)}</select></label>
        <button disabled={ocupado || !operaciones.datos?.habilitadas}>Registrar solicitud</button>
      </form>
      <p className="tenue">El rollback de imágenes no restaura datos ni revierte migraciones. Las incompatibilidades se bloquean.</p>
    </details>
    <details><summary>Aprobar una versión después de revisar CI</summary>
      <form className="infra-formulario" onSubmit={event => {
        event.preventDefault(); const form = new FormData(event.currentTarget);
        void operar(() => enviarJson(`${BASE}/versiones/${form.get("version_id")}/aprobar`, "POST", {evidencia_ci: form.get("evidencia_ci")}), "Aprobación del SUPERADMIN registrada con su evidencia.");
      }}>
        <label>Versión<select name="version_id" required><option value="">Seleccionar</option>{versiones.datos?.map(v => <option key={v.id} value={v.id}>{v.version} · {v.entorno}</option>)}</select></label>
        <label>Enlace de GitHub Actions revisado<input type="url" name="evidencia_ci" required /></label>
        <button disabled={ocupado}>Registrar revisión y aprobación</button>
      </form>
    </details>
    <h4>Inventario de backups cifrados</h4>
    <Estado cargando={backups.cargando} error={backups.error}>
      <div className="infra-tabla"><table><thead><tr><th>Archivo</th><th>Fecha</th><th>Integridad</th><th>Retención</th><th>Restauración aislada</th></tr></thead>
        <tbody>{backups.datos?.map(b => <tr key={b.id}><td>{b.objeto}</td><td>{new Date(b.fecha).toLocaleString("es-PE")}</td><td title={b.sha256}>{b.estado} · {b.bytes} bytes</td><td>{b.retencion_dias} días</td><td>{b.restauracion_verificada_at ? new Date(b.restauracion_verificada_at).toLocaleString("es-PE") : "Sin verificar"}</td></tr>)}</tbody></table></div>
    </Estado>
    <details><summary>Registrar una restauración aislada ya comprobada</summary>
      <p>Ejecuta primero el procedimiento de restauración aislada del agente y conserva la evidencia de su resultado.</p>
      <form className="infra-formulario" onSubmit={event => {
        event.preventDefault(); const form = new FormData(event.currentTarget);
        void operar(() => enviarJson(`${BASE}/backups/${form.get("backup_id")}/restauracion-verificada`, "POST", {evidencia: form.get("evidencia"), entorno: form.get("entorno")}), "Verificación de restauración declarada y auditada.");
      }}>
        <label>Backup<select name="backup_id" required><option value="">Seleccionar</option>{backups.datos?.map(b => <option key={b.id} value={b.id}>{b.objeto}</option>)}</select></label>
        <label>Evidencia<input name="evidencia" type="url" required minLength={10} /></label>
        <label>Entorno aislado<select name="entorno"><option>staging</option><option>development</option></select></label>
        <label><input type="checkbox" required />He comprobado la restauración aislada</label><button disabled={ocupado}>Registrar evidencia</button>
      </form>
    </details>
  </section>;
}
