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
    "permisos" | "acceso" | "empresas" | "mantenimiento" | "administraciones"
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
            <button onClick={() => setSeccion("administraciones")}>Administradores</button>
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
            <h3>Catálogo de roles y responsabilidades</h3>
            <p className="tenue">Este catálogo muestra capacidades actuales y objetivos pendientes; el control efectivo depende siempre del backend.</p>
            <table><thead><tr><th>Rol</th><th>Ámbito de acceso</th><th>Estado técnico</th></tr></thead><tbody>
              <tr><td>SUPERADMIN</td><td>Inventario global SaaS; operación según sesión de tenant</td><td>Implementado parcialmente</td></tr>
              <tr><td>ADMINISTRADOR</td><td>Su propia Administración</td><td>Implementado</td></tr>
              <tr><td>GERENTE</td><td>Presupuestos y cobros del tenant</td><td>Falta restringir detalle subordinado</td></tr>
              <tr><td>SECRETARIA</td><td>Control documental transversal del tenant</td><td>Implementado parcialmente</td></tr>
              <tr><td>RESPONSABLE</td><td>Sus Usuarios y sus pedidos</td><td>Pendiente de implementar</td></tr>
              <tr><td>USUARIO</td><td>Sus Gestores y operaciones</td><td>Implementado parcialmente</td></tr>
              <tr><td>GESTOR</td><td>Sus documentos y asignaciones</td><td>Acceso independiente implementado</td></tr>
            </tbody></table>
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

      {seccion === "administraciones" && sesion.rol === "SUPERADMIN" && <AdministracionesPanel />}
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


interface AdministracionGlobal {
  id: string;
  nombre: string;
  administradores: number;
  gerentes: number;
  secretarias: number;
  usuarios: number;
  gestores: number;
  cuentas_activas: number;
  estado_suscripcion: string;
  codigo: string;
  origen: string;
  estado: string;
}

function AdministracionesPanel() {
  const { datos, error, cargando, recargar } = useDatos<AdministracionGlobal[]>(
    "/api/v1/configuracion/administraciones",
  );
  const [texto, setTexto] = useState("");
  const [nombreAdministrador, setNombreAdministrador] = useState("Luis Arevalo Herrera");
  const [nombreEspacio, setNombreEspacio] = useState("Administración Luis Arévalo Herrera");
  const [subdominio, setSubdominio] = useState("");
  const [nuevaCuenta, setNuevaCuenta] = useState<{ codigo: string; login: string; clave_temporal: string } | null>(null);
  const [mensaje, setMensaje] = useState("");
  const crear = async (evento: FormEvent) => {
    evento.preventDefault();
    setMensaje("");
    if (!window.confirm(`¿Crear una Administración independiente para ${nombreAdministrador}?`)) return;
    try {
      const r = await enviarJson<{ codigo: string; login: string; clave_temporal: string }>(
        "/api/v1/configuracion/administraciones", "POST", {
          nombre_administrador: nombreAdministrador,
          nombre_espacio: nombreEspacio,
          subdominio: subdominio.trim().toLowerCase() || null,
          origen: "SUPERADMIN",
        },
      );
      setNuevaCuenta(r);
      recargar();
    } catch (error) {
      setMensaje(error instanceof Error ? error.message : String(error));
    }
  };
  const visibles = (datos ?? []).filter((a) =>
    a.nombre.toLowerCase().includes(texto.toLowerCase()) || a.id.includes(texto),
  );
  return (
    <section className="panel-configuracion">
      <h3>Administradores / Administraciones SaaS</h3>
      <form onSubmit={(e) => void crear(e)} className="filtros">
        <label>Nombre del Administrador
          <input required value={nombreAdministrador} onChange={(e) => setNombreAdministrador(e.target.value)} />
        </label>
        <label>Nombre del espacio
          <input required value={nombreEspacio} onChange={(e) => setNombreEspacio(e.target.value)} />
        </label>
        <label>Subdominio (opcional)
          <input value={subdominio} onChange={(e) => setSubdominio(e.target.value.toLowerCase())} placeholder="nexomar" pattern="[a-z][a-z0-9-]{1,61}[a-z0-9]" />
        </label>
        <button type="submit">Crear Administración independiente</button>
      </form>
      {mensaje && <p role="alert">{mensaje}</p>}
      {nuevaCuenta && <div className="panel-configuracion">
        <h4>Credenciales temporales — guárdalas ahora</h4>
        <p>Código: <strong>{nuevaCuenta.codigo}</strong></p>
        <p>Usuario: <strong>{nuevaCuenta.login}</strong></p>
        <p>Contraseña temporal: <strong>{nuevaCuenta.clave_temporal}</strong></p>
        <p className="tenue">La contraseña no volverá a mostrarse. Se exigirá cambiarla al ingresar.</p>
      </div>}
      <p className="tenue">
        Exclusivo de SUPERADMIN. Cada Administración conserva su propio espacio y datos.
        Las cuentas activas son credenciales habilitadas, no sesiones conectadas actualmente.
        El estado comercial de suscripción todavía no está implementado.
      </p>
      <div className="acciones">
        <input value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Buscar Administración o UUID" />
        <button onClick={() => recargar()}>Actualizar</button>
      </div>
      {cargando && <p>Cargando Administraciones…</p>}
      {error && <p role="alert">{error}</p>}
      <p>Total de Administraciones registradas: <strong>{datos?.length ?? 0}</strong></p>
      <table>
        <thead><tr><th>Administración</th><th>Código</th><th>Subdominio</th><th>Origen</th><th>Estado</th><th>Identificador</th><th>Administradores</th><th>Gerentes</th><th>Secretaría</th><th>Usuarios</th><th>Gestores</th><th>Cuentas habilitadas</th></tr></thead>
        <tbody>{visibles.map((a) => (
          <tr key={a.id}>
            <td>{a.nombre}</td><td>{a.codigo || "Legado"}</td><td>{a.subdominio || "Sin asignar"}</td><td>{a.origen}</td><td>{a.estado}</td><td>{a.id}</td><td>{a.administradores}</td>
            <td>{a.gerentes}</td><td>{a.secretarias}</td><td>{a.usuarios}</td>
            <td>{a.gestores}</td><td>{a.cuentas_activas}</td>
          </tr>
        ))}</tbody>
      </table>
      <p className="tenue">
        La edición, suspensión, creación y eliminación de Administraciones requiere
        incorporar estados de tenant, respaldo y auditoría. No se permite borrar
        información de otros espacios desde esta vista.
      </p>
    </section>
  );
}
