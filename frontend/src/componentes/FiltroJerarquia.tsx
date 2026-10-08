import { useDatos } from "../api";
import type { RegistroOpciones, SesionActual } from "../tipos";

export default function FiltroJerarquia({
  sesion,
  usuarioId,
  gestorId,
  cambiar,
}: {
  sesion: SesionActual;
  usuarioId: string;
  gestorId: string;
  cambiar: (clave: string, valor: string) => void;
}) {
  const { datos } = useDatos<RegistroOpciones>("/api/v1/registros/opciones");
  const administra = ["SUPERADMIN", "ADMINISTRADOR", "GERENTE", "SECRETARIA"].includes(
    sesion.rol,
  );
  const gestores = (datos?.gestores ?? []).filter(
    (g) => !usuarioId || g.usuario_id === usuarioId,
  );
  if (sesion.rol === "GESTOR") return null;
  return (
    <>
      {administra && (
        <select
          aria-label="Filtrar por usuario"
          value={usuarioId}
          onChange={(e) => cambiar("usuario_id", e.target.value)}
        >
          <option value="">Todos los usuarios</option>
          {(datos?.usuarios ?? []).map((u) => (
            <option key={u.id} value={u.id}>{u.codigo} · {u.nombre}</option>
          ))}
        </select>
      )}
      <select
        aria-label="Filtrar por gestor"
        value={gestorId}
        onChange={(e) => cambiar("gestor_id", e.target.value)}
      >
        <option value="">Todos mis gestores visibles</option>
        {gestores.map((g) => (
          <option key={g.id} value={g.id}>{g.codigo} · {g.nombre}</option>
        ))}
      </select>
    </>
  );
}
