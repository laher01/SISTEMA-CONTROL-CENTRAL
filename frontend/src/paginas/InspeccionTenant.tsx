import { useState } from "react";
import { useDatos } from "../api";

type Miembro = { id: string; codigo: string; nombre: string; rol: string; activo: boolean; login: string | null; responsable_id: string | null };
type Gestor = { id: string; codigo: string; nombre: string; usuario_id: string | null };
type Inspeccion = {
  solo_lectura: boolean;
  tenant: { id: string; codigo: string | null; nombre: string; estado: string; subdominio: string | null };
  miembros: Miembro[];
  gestores: Gestor[];
  contadores: { empresas: number; expedientes: number; documentos: number };
};

export default function InspeccionTenant({ tenantId, cerrar }: { tenantId: string; cerrar: () => void }) {
  const { datos, cargando, error } = useDatos<Inspeccion>(
    `/api/v1/configuracion/administraciones/${tenantId}/inspeccion`,
  );
  const [rol, setRol] = useState("TODOS");
  const miembros = (datos?.miembros ?? []).filter(m => rol === "TODOS" || m.rol === rol);
  return <section className="panel-configuracion" aria-label="Inspección de Tenant de solo lectura">
    <div className="acciones">
      <h3>Inspección de Tenant · Solo lectura</h3>
      <button type="button" onClick={cerrar}>Cerrar inspección</button>
    </div>
    <p className="tenue">Vista de plataforma sin suplantación de usuarios y sin operaciones de modificación.</p>
    {cargando && <p>Cargando información de la Administración…</p>}
    {error && <p role="alert">{error}</p>}
    {datos && <>
      <h4>{datos.tenant.nombre} · {datos.tenant.codigo ?? "Sin código"}</h4>
      <p>Estado: {datos.tenant.estado} · Subdominio: {datos.tenant.subdominio ?? "No asignado"}</p>
      <div className="resumen-carga">
        <strong>Empresas: {datos.contadores.empresas}</strong>{" · "}
        <strong>Expedientes: {datos.contadores.expedientes}</strong>{" · "}
        <strong>Documentos: {datos.contadores.documentos}</strong>{" · "}
        <strong>Miembros: {datos.miembros.length}</strong>{" · "}
        <strong>Gestores: {datos.gestores.length}</strong>
      </div>
      <label>Filtrar por rol{" "}
        <select value={rol} onChange={e => setRol(e.target.value)}>
          <option value="TODOS">Todos</option>
          {["ADMINISTRADOR", "GERENTE", "SECRETARIA", "RESPONSABLE", "USUARIO"].map(r => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
      </label>
      <div className="tabla-responsive"><table><thead><tr>
        <th>Rol</th><th>Código</th><th>Nombre</th><th>Acceso</th><th>Estado</th><th>Responsable</th>
      </tr></thead><tbody>{miembros.map(m => <tr key={m.id}>
        <td>{m.rol}</td><td>{m.codigo}</td><td>{m.nombre}</td><td>{m.login ?? "—"}</td>
        <td>{m.activo ? "Activo" : "Inactivo"}</td><td>{m.responsable_id ?? "—"}</td>
      </tr>)}</tbody></table></div>
      <h4>Gestores</h4>
      <div className="tabla-responsive"><table><thead><tr>
        <th>Código</th><th>Nombre</th><th>Usuario asignado</th>
      </tr></thead><tbody>{datos.gestores.map(g => <tr key={g.id}>
        <td>{g.codigo}</td><td>{g.nombre}</td>
        <td>{datos.miembros.find(m => m.id === g.usuario_id)?.nombre ?? "Sin asignar"}</td>
      </tr>)}</tbody></table></div>
    </>}
  </section>;
}
