import { useMemo } from "react";

import { enviarJson, useDatos } from "../api";
import type { PermisoConfigurado } from "../tipos";

const ROLES = ["GERENTE", "SECRETARIA", "USUARIO"] as const;
const PERMISO = "ELIMINAR_REGISTROS";

export default function Configuracion() {
  const { datos, error, cargando, recargar } = useDatos<PermisoConfigurado[]>(
    "/api/v1/configuracion/permisos",
  );

  const estado = useMemo(() => {
    const mapa = new Map<string, boolean>();
    for (const permiso of datos ?? []) {
      if (permiso.permiso === PERMISO) mapa.set(permiso.rol, permiso.habilitado);
    }
    return mapa;
  }, [datos]);

  return (
    <>
      <h2>Configuración</h2>
      <p className="tenue">
        Administración controla permisos adicionales. Administrador y Gestor conservan
        el permiso de eliminación por defecto; los demás roles lo tienen desactivado
        salvo autorización expresa.
      </p>
      {cargando && <p>Cargando…</p>}
      {error && <p className="error">{error}</p>}

      <section className="panel-configuracion">
        <h3>Eliminar registros</h3>
        <table>
          <thead><tr><th>Rol</th><th>Permiso</th></tr></thead>
          <tbody>
            <tr><td>ADMINISTRADOR</td><td>Activo por defecto</td></tr>
            <tr><td>GESTOR</td><td>Activo para sus propios registros</td></tr>
            {ROLES.map((rol) => (
              <tr key={rol}>
                <td>{rol}</td>
                <td>
                  <label>
                    <input
                      type="checkbox"
                      checked={estado.get(rol) ?? false}
                      onChange={async (e) => {
                        await enviarJson<PermisoConfigurado>(
                          "/api/v1/configuracion/permisos",
                          "PUT",
                          {
                            rol,
                            permiso: PERMISO,
                            habilitado: e.target.checked,
                          },
                        );
                        recargar();
                      }}
                    />
                    Habilitar eliminación lógica
                  </label>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
