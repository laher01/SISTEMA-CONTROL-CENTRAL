import { useState, type FormEvent } from "react";

import { eliminar, enviarJson, useDatos } from "../api";
import { Estado } from "../componentes";
import OperacionesInfraestructura from "./OperacionesInfraestructura";

type Entorno = "development" | "staging" | "canary" | "production";
interface Nodo {
  id: string;
  codigo: string;
  nombre: string;
  hostname: string;
  endpoint_privado: string;
  proveedor: string;
  region: string;
  sistema_operativo: string;
  entorno: Entorno;
  activo: boolean;
  estado: string;
  version_instalada: string | null;
  ultima_conexion: string | null;
  cpu_porcentaje: number | null;
  ram_porcentaje: number | null;
  disco_porcentaje: number | null;
  cpu_nucleos: number | null;
  ram_bytes: number | null;
  disco_bytes: number | null;
  servicios: Record<string, string>;
  metricas_vigentes: boolean;
  tenants: string[];
  alertas: string[];
}
interface Resumen {
  total: number;
  activos: number;
  inactivos: number;
  nodos: Nodo[];
  limite_nodos: number;
}
interface Version {
  id: string;
  version: string;
  entorno: string;
  commit_git: string;
  imagen_docker: string;
  digest: string;
  validacion: string;
  aprobacion: string;
}
interface Evento {
  id: string;
  fecha: string;
  accion: string;
  actor_cuenta_id: string;
  resultado: string;
  correlacion_id: string;
}
const BASE = "/api/v1/infraestructura";
const fecha = (valor: string | null) => valor ? new Date(valor).toLocaleString("es-PE") : "Sin reporte";
const porcentaje = (valor: number | null) => valor === null ? "Sin datos" : `${valor.toFixed(1)} %`;

export default function Infraestructura() {
  const resumen = useDatos<Resumen>(`${BASE}/dashboard`);
  const versiones = useDatos<Version[]>(`${BASE}/versiones`);
  const eventos = useDatos<Evento[]>(`${BASE}/eventos`);
  const administraciones = useDatos<{ id: string; nombre: string }[]>("/api/v1/configuracion/administraciones");
  const [seleccion, setSeleccion] = useState<Nodo | null>(null);
  const [error, setError] = useState("");
  const [mensaje, setMensaje] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [credencial, setCredencial] = useState<{ codigo: string; token: string } | null>(null);

  const recargar = () => {
    resumen.recargar(); versiones.recargar(); eventos.recargar();
  };
  const operar = async (accion: () => Promise<unknown>, exito: string) => {
    setError(""); setMensaje(""); setOcupado(true);
    try { await accion(); setMensaje(exito); recargar(); }
    catch (e) { setError(e instanceof Error ? e.message : "No se pudo completar la operación"); }
    finally { setOcupado(false); }
  };
  const guardarNodo = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const datos = {
      ...Object.fromEntries(form.entries()),
      cpu_nucleos: seleccion?.cpu_nucleos ?? null,
      ram_bytes: seleccion?.ram_bytes ?? null,
      disco_bytes: seleccion?.disco_bytes ?? null,
    };
    await operar(async () => {
      await enviarJson(seleccion ? `${BASE}/nodos/${seleccion.id}` : `${BASE}/nodos`, seleccion ? "PUT" : "POST", datos);
      setSeleccion(null);
    }, "Nodo guardado. Las métricas aparecerán cuando el agente envíe su primer reporte.");
  };
  const registrarVersion = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await operar(() => enviarJson(`${BASE}/versiones`, "POST", {
      ...Object.fromEntries(form.entries()),
      construida_at: new Date(String(form.get("construida_at"))).toISOString(),
      migracion_reversible: form.has("migracion_reversible"),
    }), "Versión registrada como pendiente de validación y aprobación.");
  };

  return <>
    <div className="acciones"><h2>Infraestructura</h2><button disabled={ocupado} onClick={recargar}>Actualizar</button></div>
    <p className="tenue">Inventario global de SUPERADMIN. Las ubicaciones de tenants no trasladan sus datos.</p>
    {error && <p className="error" role="alert">{error}</p>}
    {mensaje && <p role="status">{mensaje}</p>}
    <Estado cargando={resumen.cargando} error={resumen.error}>
      {resumen.datos && <>
        <div className="infra-indicadores">
          <div><strong>{resumen.datos.total}</strong><span>Servidores registrados</span></div>
          <div><strong>{resumen.datos.activos}</strong><span>Activos en inventario</span></div>
          <div><strong>{resumen.datos.inactivos}</strong><span>Desactivados</span></div>
        </div>
        {resumen.datos.total > resumen.datos.limite_nodos && <p>Se muestran los primeros {resumen.datos.limite_nodos} nodos.</p>}
        {!resumen.datos.nodos.length && <p>No hay servidores registrados.</p>}
        <div className="infra-tabla"><table><thead><tr>
          <th>Nodo y entorno</th><th>Estado</th><th>CPU / RAM / disco</th><th>Servicios</th>
          <th>Versión y conexión</th><th>Tenants</th><th>Acciones</th>
        </tr></thead><tbody>{resumen.datos.nodos.map(n => <tr key={n.id}>
          <td><strong>{n.codigo}</strong><br />{n.nombre}<br /><small>{n.entorno} · {n.proveedor} · {n.region}</small></td>
          <td>{n.estado}{n.alertas.map(a => <p className="error" key={a}>{a.replaceAll("_", " ")}</p>)}</td>
          <td>{porcentaje(n.cpu_porcentaje)} / {porcentaje(n.ram_porcentaje)} / {porcentaje(n.disco_porcentaje)}
            {!n.metricas_vigentes && <p className="tenue">Métricas sin confirmar o antiguas</p>}
            <small>{n.cpu_nucleos ?? "—"} núcleos · RAM {n.ram_bytes ? `${(n.ram_bytes / 1024**3).toFixed(1)} GiB` : "sin capacidad registrada"}</small>
          </td>
          <td>{Object.entries(n.servicios).map(([servicio, estado]) => <p key={servicio}>{servicio}: {estado}</p>)}</td>
          <td>{n.version_instalada ?? "Sin versión reportada"}<br /><small>{fecha(n.ultima_conexion)}</small></td>
          <td>{n.tenants.length} administraciones</td>
          <td><div className="acciones">
            <button disabled={ocupado || !n.activo} onClick={() => setSeleccion(n)}>Editar</button>
            <button disabled={ocupado || !n.activo} onClick={() => void operar(async () => {
              const dato = await enviarJson<{token: string}>(`${BASE}/nodos/${n.id}/credencial`, "POST");
              setCredencial({codigo: n.codigo, token: dato.token});
            }, "Credencial rotada; la anterior dejó de funcionar.")}>Rotar credencial</button>
            <button disabled={ocupado || !n.activo} onClick={() => void operar(() => eliminar(`${BASE}/nodos/${n.id}`), "Nodo desactivado y credencial revocada.")}>Desactivar</button>
          </div></td>
        </tr>)}</tbody></table></div>
      </>}
    </Estado>
    {credencial && <section className="panel-configuracion">
      <h3>Credencial de agente: {credencial.codigo}</h3>
      <p>Se entrega una sola vez. Guárdala en el archivo de entorno privado del agente.</p>
      <label>Token<input readOnly type="password" value={credencial.token} autoComplete="off" /></label>
      <button onClick={() => void operar(() => navigator.clipboard.writeText(credencial.token), "Credencial copiada.")}>Copiar</button>
      <button onClick={() => setCredencial(null)}>Ocultar y descartar</button>
    </section>}
    <section className="panel-configuracion"><h3>{seleccion ? `Editar ${seleccion.codigo}` : "Registrar servidor"}</h3>
      <form className="infra-formulario" key={seleccion?.id ?? "nuevo"} onSubmit={guardarNodo}>
        {([
          ["codigo", "Identificador", 60], ["nombre", "Nombre", 200], ["hostname", "Hostname", 253],
          ["endpoint_privado", "Endpoint privado (http/https)", 500], ["proveedor", "Proveedor", 80],
          ["region", "Región", 80], ["sistema_operativo", "Sistema operativo", 100],
        ] as const).map(([campo, etiqueta, max]) => <label key={campo}>{etiqueta}
          <input name={campo} required maxLength={max} defaultValue={seleccion?.[campo] ?? ""} />
        </label>)}
        <label>Entorno<select name="entorno" defaultValue={seleccion?.entorno ?? "staging"}>
          {["development", "staging", "canary", "production"].map(e => <option key={e}>{e}</option>)}
        </select></label>
        <button disabled={ocupado}>Guardar nodo</button>
        {seleccion && <button type="button" onClick={() => setSeleccion(null)}>Cancelar edición</button>}
      </form>
    </section>
    <section className="panel-configuracion"><h3>Ubicación de administraciones</h3>
      {administraciones.error && <p className="error">{administraciones.error}</p>}
      <form className="infra-formulario" onSubmit={event => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        void operar(() => enviarJson(`${BASE}/asociaciones`, "POST", Object.fromEntries(form.entries())), "Ubicación registrada. No se trasladaron datos.");
      }}>
        <label>Administración<select name="tenant_id" required><option value="">Seleccionar</option>
          {administraciones.datos?.map(a => <option key={a.id} value={a.id}>{a.nombre}</option>)}
        </select></label>
        <label>Nodo<select name="nodo_id" required><option value="">Seleccionar</option>
          {resumen.datos?.nodos.filter(n => n.activo).map(n => <option key={n.id} value={n.id}>{n.codigo}</option>)}
        </select></label><button disabled={ocupado}>Registrar ubicación</button>
      </form>
    </section>
    <section className="panel-configuracion"><h3>Versiones</h3>
      <Estado cargando={versiones.cargando} error={versiones.error}>
        <div className="infra-tabla"><table><thead><tr><th>Versión / entorno</th><th>Commit e imagen</th><th>Validación / aprobación</th></tr></thead>
          <tbody>{versiones.datos?.map(v => <tr key={v.id}><td>{v.version} · {v.entorno}</td>
            <td><code>{v.commit_git}</code><br /><code>{v.imagen_docker}@{v.digest}</code></td>
            <td>{v.validacion} / {v.aprobacion}</td></tr>)}</tbody></table></div>
      </Estado>
      <details><summary>Registrar una versión construida</summary>
        <form className="infra-formulario" onSubmit={registrarVersion}>
          {([ ["version", "Versión semántica"], ["commit_git", "Commit completo"],
            ["imagen_docker", "Imagen backend sin etiqueta"], ["digest", "Digest backend sha256"],
            ["imagen_frontend", "Imagen frontend sin etiqueta"], ["digest_frontend", "Digest frontend sha256"],
            ["migracion_desde", "Migración anterior"], ["migracion_hasta", "Migración nueva"] ] as const).map(([campo, etiqueta]) =>
            <label key={campo}>{etiqueta}<input required name={campo} /></label>)}
          <label>Fecha de construcción<input required type="datetime-local" name="construida_at" /></label>
          <label>Entorno<select name="entorno">{["staging", "development", "canary", "production"].map(e => <option key={e}>{e}</option>)}</select></label>
          <label><input type="checkbox" name="migracion_reversible" />Migración reversible comprobada</label>
          <button disabled={ocupado}>Registrar versión pendiente</button>
        </form>
      </details>
    </section>
    <section className="panel-configuracion"><h3>Historial de infraestructura</h3>
      <Estado cargando={eventos.cargando} error={eventos.error}>
        <div className="infra-tabla"><table><thead><tr><th>Fecha</th><th>Acción</th><th>Actor</th><th>Resultado</th></tr></thead>
          <tbody>{eventos.datos?.map(e => <tr key={e.id}><td>{fecha(e.fecha)}</td><td title={e.correlacion_id}>{e.accion}</td><td>{e.actor_cuenta_id}</td><td>{e.resultado}</td></tr>)}</tbody></table></div>
      </Estado>
    </section>
    <OperacionesInfraestructura />
  </>;
}
