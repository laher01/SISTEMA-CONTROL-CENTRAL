import { useMemo, useState, type FormEvent } from "react";

import { eliminar, enviarJson, useDatos } from "../api";
import type {
  ConfiguracionAcceso as ConfiguracionAccesoTipo,
  CorreoAutorizado,
  CuentaAccesoAdmin,
  PermisoConfigurado,
  RolMiembro,
  SesionAccesoAdmin,
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
  const {
    datos: cuentas,
    recargar: recargarCuentas,
  } = useDatos<CuentaAccesoAdmin[]>("/api/v1/configuracion/acceso/cuentas");
  const {
    datos: sesiones,
    recargar: recargarSesiones,
  } = useDatos<SesionAccesoAdmin[]>("/api/v1/configuracion/acceso/sesiones");

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
        duracion_sesion_horas:
          cambios.duracion_sesion_horas ?? config.duracion_sesion_horas,
        intentos_fallidos_max:
          cambios.intentos_fallidos_max ?? config.intentos_fallidos_max,
        bloqueo_minutos: cambios.bloqueo_minutos ?? config.bloqueo_minutos,
        clave_min_longitud: cambios.clave_min_longitud ?? config.clave_min_longitud,
        clave_requiere_letra:
          cambios.clave_requiere_letra ?? config.clave_requiere_letra,
        clave_requiere_numero:
          cambios.clave_requiere_numero ?? config.clave_requiere_numero,
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
          <div className="acciones">
            <label>
              Sesión (horas)
              <input
                type="number"
                min={1}
                max={168}
                value={config.duracion_sesion_horas}
                onChange={(e) =>
                  void guardar({ duracion_sesion_horas: Number(e.target.value) })
                }
              />
            </label>
            <label>
              Intentos fallidos
              <input
                type="number"
                min={1}
                max={20}
                value={config.intentos_fallidos_max}
                onChange={(e) =>
                  void guardar({ intentos_fallidos_max: Number(e.target.value) })
                }
              />
            </label>
            <label>
              Bloqueo (minutos)
              <input
                type="number"
                min={1}
                max={1440}
                value={config.bloqueo_minutos}
                onChange={(e) => void guardar({ bloqueo_minutos: Number(e.target.value) })}
              />
            </label>
            <label>
              Longitud mínima de clave
              <input
                type="number"
                min={8}
                max={128}
                value={config.clave_min_longitud}
                onChange={(e) =>
                  void guardar({ clave_min_longitud: Number(e.target.value) })
                }
              />
            </label>
          </div>
          <label>
            <input
              type="checkbox"
              checked={config.clave_requiere_letra}
              onChange={(e) => void guardar({ clave_requiere_letra: e.target.checked })}
            />
            La clave debe incluir letras
          </label>
          <label>
            <input
              type="checkbox"
              checked={config.clave_requiere_numero}
              onChange={(e) => void guardar({ clave_requiere_numero: e.target.checked })}
            />
            La clave debe incluir números
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
                          { aprobar: true, rol: null },
                        );
                        if (respuesta.clave_temporal) {
                          setMensaje(`Cuenta creada. Clave temporal: ${String(respuesta.clave_temporal)}`);
                        }
                        recargarSolicitudes();
                      }}
                    >
                      Aprobar según autorización
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

      <h4>Cuentas de acceso</h4>
      <table>
        <thead>
          <tr>
            <th>Login</th><th>Correo</th><th>Activo</th><th>Bloqueo</th><th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {(cuentas ?? []).map((cuenta) => (
            <tr key={cuenta.id}>
              <td>{cuenta.login}</td>
              <td>{cuenta.email ?? "—"}</td>
              <td>{cuenta.activo ? "Sí" : "No"}</td>
              <td>
                {cuenta.bloqueado_hasta
                  ? new Date(cuenta.bloqueado_hasta).toLocaleString()
                  : "—"}
              </td>
              <td>
                <button
                  onClick={async () => {
                    await enviarJson<CuentaAccesoAdmin>(
                      `/api/v1/configuracion/acceso/cuentas/${cuenta.id}`,
                      "PATCH",
                      { activo: !cuenta.activo },
                    );
                    recargarCuentas();
                  }}
                >
                  {cuenta.activo ? "Desactivar" : "Activar"}
                </button>
                <button
                  onClick={async () => {
                    const respuesta = await enviarJson<{ clave_temporal: string }>(
                      `/api/v1/configuracion/acceso/cuentas/${cuenta.id}/restablecer-clave`,
                      "POST",
                    );
                    setMensaje(
                      `Clave temporal para ${cuenta.login}: ${respuesta.clave_temporal}`,
                    );
                    recargarCuentas();
                  }}
                >
                  Restablecer clave
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h4>Sesiones</h4>
      <table>
        <thead>
          <tr><th>Login</th><th>Rol</th><th>Última actividad</th><th>Estado</th><th></th></tr>
        </thead>
        <tbody>
          {(sesiones ?? []).map((sesion) => (
            <tr key={sesion.id}>
              <td>{sesion.login}</td>
              <td>{sesion.rol_activo}</td>
              <td>{new Date(sesion.ultima_actividad).toLocaleString()}</td>
              <td>{sesion.revocada_at ? "Revocada" : "Activa"}</td>
              <td>
                {!sesion.revocada_at && (
                  <button
                    onClick={async () => {
                      await eliminar(`/api/v1/configuracion/acceso/sesiones/${sesion.id}`);
                      recargarSesiones();
                    }}
                  >
                    Cerrar sesión
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
