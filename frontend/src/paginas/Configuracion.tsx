import { useMemo, useState, type FormEvent } from "react";

import { eliminar, enviarJson, useDatos } from "../api";
import type {
  ConfiguracionAcceso as ConfiguracionAccesoTipo,
  CorreoAutorizado,
  PermisoConfigurado,
  RolMiembro,
  SesionActual,
  SolicitudAcceso,
} from "../tipos";

const ROLES = ["GERENTE", "SECRETARIA", "USUARIO"] as const;
const PERMISO = "ELIMINAR_REGISTROS";

export default function Configuracion({ sesion }: { sesion: SesionActual }) {
  const [seccion, setSeccion] = useState<"permisos" | "acceso">("permisos");
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
      <div className="acciones">
        <button onClick={() => setSeccion("permisos")}>Permisos operativos</button>
        {sesion.rol === "SUPERADMIN" && (
          <button onClick={() => setSeccion("acceso")}>Configuración de acceso</button>
        )}
      </div>

      {seccion === "permisos" && (
        <>
          <p className="tenue">
            Administración controla permisos adicionales. SUPERADMIN hereda las capacidades
            administrativas; la seguridad global se gestiona aparte.
          </p>
          {cargando && <p>Cargando…</p>}
          {error && <p className="error">{error}</p>}
          <section className="panel-configuracion">
            <h3>Eliminar registros</h3>
            <table>
              <thead><tr><th>Rol</th><th>Permiso</th></tr></thead>
              <tbody>
                <tr><td>SUPERADMIN</td><td>Activo por defecto</td></tr>
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
                              { rol, permiso: PERMISO, habilitado: e.target.checked },
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
      )}

      {seccion === "acceso" && sesion.rol === "SUPERADMIN" && <ConfiguracionAccesoPanel />}
    </>
  );
}

function ConfiguracionAccesoPanel() {
  const { datos: config, error, cargando, recargar } = useDatos<ConfiguracionAccesoTipo>(
    "/api/v1/configuracion/acceso",
  );
  const {
    datos: correos,
    recargar: recargarCorreos,
  } = useDatos<CorreoAutorizado[]>("/api/v1/configuracion/acceso/correos");
  const {
    datos: solicitudes,
    recargar: recargarSolicitudes,
  } = useDatos<SolicitudAcceso[]>("/api/v1/configuracion/acceso/solicitudes");

  const [email, setEmail] = useState("");
  const [rol, setRol] = useState<RolMiembro>("USUARIO");
  const [mensaje, setMensaje] = useState("");

  const guardar = async (cambios: Partial<ConfiguracionAccesoTipo>) => {
    if (!config) return;
    setMensaje("");
    try {
      await enviarJson<ConfiguracionAccesoTipo>("/api/v1/configuracion/acceso", "PUT", {
        registro_publico: cambios.registro_publico ?? config.registro_publico,
        requiere_aprobacion: cambios.requiere_aprobacion ?? config.requiere_aprobacion,
        solo_correos_autorizados:
          cambios.solo_correos_autorizados ?? config.solo_correos_autorizados,
        requiere_email_verificado:
          cambios.requiere_email_verificado ?? config.requiere_email_verificado,
        acceso_cloudflare_activo:
          cambios.acceso_cloudflare_activo ?? config.acceso_cloudflare_activo,
      });
      recargar();
    } catch (err) {
      setMensaje(err instanceof Error ? err.message : String(err));
    }
  };

  const agregarCorreo = async (e: FormEvent) => {
    e.preventDefault();
    setMensaje("");
    try {
      await enviarJson<CorreoAutorizado>("/api/v1/configuracion/acceso/correos", "POST", {
        email,
        rol_sugerido: rol,
      });
      setEmail("");
      recargarCorreos();
    } catch (err) {
      setMensaje(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <section className="panel-configuracion">
      <h3>Configuración de acceso</h3>
      <p className="tenue">
        Exclusivo de SUPERADMIN. Aquí se controla quién puede solicitar acceso y qué
        protección externa está vigente.
      </p>
      {cargando && <p>Cargando…</p>}
      {error && <p className="error">{error}</p>}
      {mensaje && <p className="error">{mensaje}</p>}

      {config && (
        <div className="config-grid">
          <label>
            <input
              type="checkbox"
              checked={config.registro_publico}
              onChange={(e) => void guardar({ registro_publico: e.target.checked })}
            />
            Permitir “Solicitar acceso” desde el login
          </label>
          <label>
            <input
              type="checkbox"
              checked={config.requiere_aprobacion}
              onChange={(e) => void guardar({ requiere_aprobacion: e.target.checked })}
            />
            Requerir aprobación del SUPERADMIN
          </label>
          <label>
            <input
              type="checkbox"
              checked={config.solo_correos_autorizados}
              onChange={(e) => void guardar({ solo_correos_autorizados: e.target.checked })}
            />
            Solo permitir correos previamente autorizados
          </label>
          <label title={!config.proveedor_email_configurado ? "Falta proveedor de email" : ""}>
            <input
              type="checkbox"
              disabled={!config.proveedor_email_configurado}
              checked={config.requiere_email_verificado}
              onChange={(e) => void guardar({ requiere_email_verificado: e.target.checked })}
            />
            Exigir correo verificado
          </label>
          <p className="tenue">
            Proveedor de email: {config.proveedor_email_configurado ? "configurado" : "pendiente"} ·
            Cloudflare Access: {config.acceso_cloudflare_activo ? "activo" : "desactivado"}
          </p>
        </div>
      )}

      <h4>Correos autorizados</h4>
      <form onSubmit={agregarCorreo} className="acciones">
        <input
          type="email"
          placeholder="correo@empresa.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <select value={rol} onChange={(e) => setRol(e.target.value as RolMiembro)}>
          <option value="USUARIO">USUARIO</option>
          <option value="GERENTE">GERENTE</option>
          <option value="SECRETARIA">SECRETARIA</option>
          <option value="ADMINISTRADOR">ADMINISTRADOR</option>
        </select>
        <button type="submit">Autorizar correo</button>
      </form>
      <table>
        <thead><tr><th>Correo</th><th>Rol sugerido</th><th></th></tr></thead>
        <tbody>
          {(correos ?? []).map((correo) => (
            <tr key={correo.id}>
              <td>{correo.email}</td>
              <td>{correo.rol_sugerido ?? "—"}</td>
              <td>
                <button
                  onClick={async () => {
                    await eliminar(`/api/v1/configuracion/acceso/correos/${correo.id}`);
                    recargarCorreos();
                  }}
                >
                  Revocar
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h4>Solicitudes de acceso</h4>
      <table>
        <thead><tr><th>Nombre</th><th>Correo</th><th>Código</th><th>Estado</th><th>Acciones</th></tr></thead>
        <tbody>
          {(solicitudes ?? []).map((solicitud) => (
            <tr key={solicitud.id}>
              <td>{solicitud.nombre}</td>
              <td>{solicitud.email}</td>
              <td>{solicitud.codigo_solicitado}</td>
              <td>{solicitud.estado}</td>
              <td>
                {solicitud.estado === "PENDIENTE" && (
                  <>
                    <button
                      onClick={async () => {
                        const respuesta = await enviarJson<Record<string, unknown>>(
                          `/api/v1/configuracion/acceso/solicitudes/${solicitud.id}/resolver`,
                          "POST",
                          { aprobar: true, rol: "USUARIO" },
                        );
                        if (respuesta.clave_temporal) {
                          setMensaje(`Cuenta creada. Clave temporal: ${String(respuesta.clave_temporal)}`);
                        }
                        recargarSolicitudes();
                      }}
                    >
                      Aprobar como Usuario
                    </button>
                    <button
                      onClick={async () => {
                        await enviarJson<Record<string, unknown>>(
                          `/api/v1/configuracion/acceso/solicitudes/${solicitud.id}/resolver`,
                          "POST",
                          { aprobar: false },
                        );
                        recargarSolicitudes();
                      }}
                    >
                      Rechazar
                    </button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
