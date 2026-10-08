import { useMemo, useState, type FormEvent } from "react";

import { eliminar, enviarJson, useDatos } from "../api";
import type {
  ConfiguracionAcceso as ConfiguracionAccesoTipo,
  CorreoAutorizado,
  CuentaAccesoAdmin,
  Empresa,
  MantenimientoAdministrador,
  MantenimientoResultado,
  MantenimientoVistaPrevia,
  PermisoConfigurado,
  RolMiembro,
  SesionAccesoAdmin,
  SesionActual,
  SolicitudAcceso,
} from "../tipos";

const ROLES = ["GERENTE", "SECRETARIA", "USUARIO"] as const;
const PERMISO = "ELIMINAR_REGISTROS";

export default function Configuracion({ sesion }: { sesion: SesionActual }) {
  const [seccion, setSeccion] = useState<
    "permisos" | "acceso" | "empresas" | "mantenimiento"
  >("permisos");
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
          <>
            <button onClick={() => setSeccion("acceso")}>Configuración de acceso</button>
            <button onClick={() => setSeccion("empresas")}>Empresas registradas</button>
            <button onClick={() => setSeccion("mantenimiento")}>Mantenimiento</button>
          </>
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
      {seccion === "empresas" && sesion.rol === "SUPERADMIN" && <EmpresasRegistradasPanel />}
      {seccion === "mantenimiento" && sesion.rol === "SUPERADMIN" && <MantenimientoPanel />}
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


const TIPOS_MANTENIMIENTO = [
  ["documentos", "Documentos"],
  ["expedientes", "Expedientes"],
  ["pagos", "Pagos programados"],
  ["adelantos", "Adelantos"],
  ["planes", "Planes de liquidación"],
  ["cuentas_pago", "Cuentas de pago"],
] as const;

function MantenimientoPanel() {
  const administradores = useDatos<MantenimientoAdministrador[]>(
    "/api/v1/configuracion/mantenimiento/administradores",
  );
  const [cuentas, setCuentas] = useState<string[]>([]);
  const [historicos, setHistoricos] = useState(false);
  const [tipos, setTipos] = useState<string[]>([
    "documentos",
    "expedientes",
    "pagos",
    "adelantos",
    "planes",
    "cuentas_pago",
  ]);
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [vista, setVista] = useState<MantenimientoVistaPrevia | null>(null);
  const [confirmacion, setConfirmacion] = useState("");
  const [mensaje, setMensaje] = useState("");

  const payload = () => ({
    cuenta_ids: cuentas,
    incluir_sin_trazabilidad: historicos,
    tipos,
    fecha_desde: desde || null,
    fecha_hasta: hasta || null,
  });

  const previsualizar = async () => {
    setMensaje("");
    try {
      const datos = await enviarJson<MantenimientoVistaPrevia>(
        "/api/v1/configuracion/mantenimiento/vista-previa",
        "POST",
        payload(),
      );
      setVista(datos);
    } catch (err) {
      setVista(null);
      setMensaje(err instanceof Error ? err.message : String(err));
    }
  };

  const ejecutar = async () => {
    setMensaje("");
    try {
      const resultado = await enviarJson<MantenimientoResultado>(
        "/api/v1/configuracion/mantenimiento/limpiar",
        "POST",
        { ...payload(), confirmacion },
      );
      setMensaje(
        "Limpieza completada: " +
          Object.entries(resultado.eliminados)
            .map(([tipo, total]) => `${tipo}: ${total}`)
            .join(" · ") +
          ` · archivos: ${resultado.archivos_eliminados}`,
      );
      setVista(null);
      setConfirmacion("");
      administradores.recargar();
    } catch (err) {
      setMensaje(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <section className="panel-configuracion">
      <h3>Mantenimiento · Zona crítica</h3>
      <p className="tenue">
        Exclusivo de SUPERADMIN. Selecciona primero el administrador responsable,
        los tipos de registros y el rango de fechas. La auditoría de la limpieza se conserva.
      </p>

      {administradores.error && <p className="error">{administradores.error}</p>}
      {mensaje && <p className="resumen-carga">{mensaje}</p>}

      <h4>1. Administradores</h4>
      <table>
        <thead>
          <tr>
            <th>Seleccionar</th><th>Administrador</th><th>Rol</th><th>Registros</th>
          </tr>
        </thead>
        <tbody>
          {(administradores.datos ?? []).map((admin) => {
            const esHistorico = admin.cuenta_id === null;
            const seleccionado = esHistorico
              ? historicos
              : cuentas.includes(admin.cuenta_id as string);
            return (
              <tr key={admin.cuenta_id ?? "historico"}>
                <td>
                  <input
                    type="checkbox"
                    checked={seleccionado}
                    onChange={(e) => {
                      if (esHistorico) {
                        setHistoricos(e.target.checked);
                      } else if (e.target.checked) {
                        setCuentas((actual) => [...actual, admin.cuenta_id as string]);
                      } else {
                        setCuentas((actual) =>
                          actual.filter((id) => id !== admin.cuenta_id),
                        );
                      }
                    }}
                  />
                </td>
                <td>{admin.login}</td>
                <td>{admin.rol}</td>
                <td>
                  {Object.entries(admin.registros)
                    .map(([tipo, total]) => `${tipo}: ${total}`)
                    .join(" · ")}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <h4>2. Qué se eliminará</h4>
      <div className="acciones">
        {TIPOS_MANTENIMIENTO.map(([valor, etiqueta]) => (
          <label key={valor}>
            <input
              type="checkbox"
              checked={tipos.includes(valor)}
              onChange={(e) =>
                setTipos((actual) =>
                  e.target.checked
                    ? [...actual, valor]
                    : actual.filter((tipo) => tipo !== valor),
                )
              }
            />
            {etiqueta}
          </label>
        ))}
      </div>

      <div className="acciones">
        <label>
          Desde
          <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
        </label>
        <label>
          Hasta
          <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
        </label>
        <button onClick={() => void previsualizar()}>Previsualizar limpieza</button>
      </div>

      {vista && (
        <>
          <h4>3. Vista previa</h4>
          <table>
            <thead><tr><th>Tipo</th><th>Total seleccionado</th></tr></thead>
            <tbody>
              {Object.entries(vista.totales).map(([tipo, total]) => (
                <tr key={tipo}><td>{tipo}</td><td>{total}</td></tr>
              ))}
            </tbody>
          </table>

          <p className="tenue">
            Para ejecutar escribe exactamente: <strong>ELIMINAR-DATOS-OPERATIVOS</strong>
          </p>
          <div className="acciones">
            <input
              value={confirmacion}
              onChange={(e) => setConfirmacion(e.target.value)}
              placeholder="ELIMINAR-DATOS-OPERATIVOS"
            />
            <button
              disabled={confirmacion !== "ELIMINAR-DATOS-OPERATIVOS"}
              onClick={() => void ejecutar()}
            >
              Eliminar registros seleccionados
            </button>
          </div>
        </>
      )}
    </section>
  );
}


function EmpresasRegistradasPanel() {
  const { datos, error, cargando, recargar } = useDatos<Empresa[]>("/api/v1/empresas");
  const [seleccionadas, setSeleccionadas] = useState<string[]>([]);
  const [buscar, setBuscar] = useState("");
  const [mensaje, setMensaje] = useState("");

  const filtradas = useMemo(() => {
    const termino = buscar.trim().toLowerCase();
    if (!termino) return datos ?? [];
    return (datos ?? []).filter(
      (empresa) =>
        empresa.ruc.includes(termino) ||
        empresa.razon_social.toLowerCase().includes(termino),
    );
  }, [buscar, datos]);

  const todasSeleccionadas =
    filtradas.length > 0 &&
    filtradas.every((empresa) => seleccionadas.includes(empresa.id));

  const alternarTodas = (valor: boolean) => {
    if (valor) {
      setSeleccionadas((actual) => [
        ...new Set([...actual, ...filtradas.map((empresa) => empresa.id)]),
      ]);
    } else {
      const visibles = new Set(filtradas.map((empresa) => empresa.id));
      setSeleccionadas((actual) => actual.filter((id) => !visibles.has(id)));
    }
  };

  const eliminarSeleccionadas = async () => {
    if (seleccionadas.length === 0) return;
    const confirmar = window.confirm(
      `¿Eliminar ${seleccionadas.length} empresa(s) seleccionada(s)? ` +
        "Solo desaparecerán del padrón activo. Si un RUC vuelve a aparecer en un comprobante, " +
        "la empresa se reactivará automáticamente.",
    );
    if (!confirmar) return;

    setMensaje("");
    try {
      const resultado = await enviarJson<{ eliminadas: number }>(
        "/api/v1/empresas/eliminar-seleccion",
        "POST",
        { empresa_ids: seleccionadas },
      );
      setMensaje(`Empresas retiradas del padrón activo: ${resultado.eliminadas}`);
      setSeleccionadas([]);
      recargar();
    } catch (err) {
      setMensaje(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <section className="panel-configuracion">
      <h3>Empresas registradas</h3>
      <p className="tenue">
        Las emisoras y receptoras detectadas quedan registradas aunque provengan de pruebas.
        No forman parte de la limpieza general. Solo SUPERADMIN puede retirarlas manualmente
        desde esta pantalla.
      </p>

      <div className="acciones">
        <input
          type="search"
          placeholder="Buscar por RUC o razón social"
          value={buscar}
          onChange={(e) => setBuscar(e.target.value)}
        />
        <button
          disabled={seleccionadas.length === 0}
          onClick={() => void eliminarSeleccionadas()}
        >
          Eliminar seleccionadas ({seleccionadas.length})
        </button>
      </div>

      {cargando && <p>Cargando…</p>}
      {error && <p className="error">{error}</p>}
      {mensaje && <p>{mensaje}</p>}

      <table>
        <thead>
          <tr>
            <th>
              <input
                type="checkbox"
                aria-label="Seleccionar todas las empresas visibles"
                checked={todasSeleccionadas}
                onChange={(e) => alternarTodas(e.target.checked)}
              />
            </th>
            <th>RUC</th>
            <th>Razón social</th>
            <th>Autorizada</th>
            <th>Agente de retención</th>
          </tr>
        </thead>
        <tbody>
          {filtradas.map((empresa) => (
            <tr key={empresa.id}>
              <td>
                <input
                  type="checkbox"
                  aria-label={`Seleccionar ${empresa.ruc}`}
                  checked={seleccionadas.includes(empresa.id)}
                  onChange={(e) =>
                    setSeleccionadas((actual) =>
                      e.target.checked
                        ? [...actual, empresa.id]
                        : actual.filter((id) => id !== empresa.id),
                    )
                  }
                />
              </td>
              <td>{empresa.ruc}</td>
              <td>{empresa.razon_social}</td>
              <td>{empresa.autorizada ? "Sí" : "No"}</td>
              <td>{empresa.agente_retencion ? "Sí" : "No"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
