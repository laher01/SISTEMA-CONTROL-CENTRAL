import { useDatos } from "../api";

interface UsuarioResponsable {
  id: string;
  codigo: string;
  nombre: string;
  rol: string;
  activo: boolean;
}

export default function MiEquipoResponsable() {
  const { datos, error, cargando, recargar } = useDatos<UsuarioResponsable[]>(
    "/api/v1/miembros/mis-usuarios",
  );
  return (
    <>
      <h2>Mis Usuarios</h2>
      <p className="tenue">
        Solo se muestran Usuarios asignados a tu responsabilidad dentro de esta Administración.
        Los presupuestos y liquidaciones jerárquicas se habilitarán en la siguiente etapa.
      </p>
      <button onClick={() => recargar()}>Actualizar</button>
      {cargando && <p>Cargando…</p>}
      {error && <p role="alert">{error}</p>}
      <table>
        <thead><tr><th>Código</th><th>Nombre</th><th>Estado</th></tr></thead>
        <tbody>{(datos ?? []).map((u) => (
          <tr key={u.id}><td>{u.codigo}</td><td>{u.nombre}</td><td>{u.activo ? "Activo" : "Inactivo"}</td></tr>
        ))}</tbody>
      </table>
    </>
  );
}
