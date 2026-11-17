import { useMemo, useState, type FormEvent } from "react";

import { enviarJson, useDatos } from "../api";
import MiEquipoResponsable from "./MiEquipoResponsable";
import type {
  AltaGestor,
  AltaMiembro,
  CredencialTemporal,
  Empresa,
  Gestor,
  Miembro,
  RolMiembro,
  SesionActual,
} from "../tipos";

const ROLES: RolMiembro[] = ["ADMINISTRADOR", "GERENTE", "SECRETARIA", "RESPONSABLE", "USUARIO"];

export default function Organizacion({ sesion }: { sesion: SesionActual }) {
  if (sesion.rol === "SUPERADMIN" || sesion.rol === "ADMINISTRADOR") {
    return <OrganizacionAdmin permiteRevisionEmisores={sesion.rol === "ADMINISTRADOR"} />;
  }
  if (sesion.rol === "RESPONSABLE") return <OrganizacionResponsable />;
  if (sesion.rol === "USUARIO") return <OrganizacionUsuario sesion={sesion} />;
  return <p>No tiene permiso para administrar la organización.</p>;
}

interface VinculoGerencia { id: string; gerente_id: string; responsable_id: string; activo: boolean }
interface CarteraGerente { id: string; gerente_id: string; empresa_id: string; activo: boolean }

function FiltroColumna({
  titulo,
  etiqueta,
  todos,
  sinAsignar,
  opciones,
  valor,
  alCambiar,
}: {
  titulo: string;
  etiqueta: string;
  todos: string;
  sinAsignar: string;
  opciones: Miembro[];
  valor: string;
  alCambiar: (valor: string) => void;
}) {
  return (
    <th scope="col">
      {titulo}
      <select className="bloque" aria-label={etiqueta} value={valor}
        onChange={(e) => alCambiar(e.target.value)}>
        <option value="">{todos}</option>
        <option value="sin-asignar">{sinAsignar}</option>
        {opciones.map((m) => <option key={m.id} value={m.id}>{m.codigo} · {m.nombre}</option>)}
      </select>
    </th>
  );
}

function coincideAsignacion(filtro: string, asignacion?: string | null) {
  return !filtro || (filtro === "sin-asignar" ? !asignacion : asignacion === filtro);
}

function EstadoAcceso({ activo, alCambiar }: { activo?: boolean | null; alCambiar?: () => void }) {
  return <>
    <span>{activo == null ? "Sin cuenta" : activo ? "Activo" : "Inactivo"}</span>
    {activo != null && alCambiar && <>{" "}
      <button type="button" onClick={alCambiar}>{activo ? "Desactivar" : "Activar"}</button>
    </>}
  </>;
}

interface LoteEmisor {
  ruc_emisor: string;
  gestor_solicitante_id: string | null;
  cantidad_documentos: number;
  cantidad_solicitudes: number;
}

interface SolicitudEmisor {
  id: string;
  gestor_propietario_id: string | null;
  responsable_propietario_id: string | null;
  estado: string;
}

function DetalleLoteEmisor({ lote, gestores, miembros }: {
  lote: LoteEmisor;
  gestores: Gestor[];
  miembros: Miembro[];
}) {
  const [pagina, setPagina] = useState(0);
  const parametros = new URLSearchParams({ offset: String(pagina * 100), limite: "100" });
  if (lote.gestor_solicitante_id) parametros.set("gestor_solicitante_id", lote.gestor_solicitante_id);
  const { datos, error, cargando } = useDatos<SolicitudEmisor[]>(
    "/api/v1/solicitudes-carga-emisor/lotes/" + encodeURIComponent(lote.ruc_emisor) + "?" + parametros.toString()
  );
  return <section>
    <h4>Solicitudes de {lote.ruc_emisor}</h4>
    {error && <p role="alert">{String(error)}</p>}
    {cargando && <p>Cargando detalle…</p>}
    {!!datos?.length && <table>
      <thead><tr><th>Solicitud</th><th>Gestor de cartera</th><th>Responsable de cartera</th><th>Estado</th></tr></thead>
      <tbody>{datos.map((solicitud) => <tr key={solicitud.id}>
        <td>{solicitud.id}</td>
        <td>{gestores.find((g) => g.id === solicitud.gestor_propietario_id)?.nombre ?? "Por verificar"}</td>
        <td>{miembros.find((m) => m.id === solicitud.responsable_propietario_id)?.nombre ?? "Por verificar"}</td>
        <td>{solicitud.estado}</td>
      </tr>)}</tbody>
    </table>}
    {!cargando && !error && datos?.length === 0 && <p>No hay más solicitudes.</p>}
    <button type="button" disabled={pagina === 0 || cargando} onClick={() => setPagina((p) => p - 1)}>Anterior</button>
    <button type="button" disabled={cargando || (datos?.length ?? 0) < 100} onClick={() => setPagina((p) => p + 1)}>Siguiente</button>
  </section>;
}

function RevisionEmisores({ gestores, miembros, empresas }: {
  gestores: Gestor[];
  miembros: Miembro[];
  empresas: Empresa[];
}) {
  const [loteSeleccionado, setLoteSeleccionado] = useState<LoteEmisor | null>(null);
  const { datos, error, cargando, recargar } = useDatos<LoteEmisor[]>("/api/v1/solicitudes-carga-emisor/lotes");
  return <section>
    <h3>Revisión de proveedores pendientes</h3>
    <p>Los documentos en cuarentena no se incorporan a la contabilidad. La revisión de cartera no acredita la validez fiscal.</p>
    <button type="button" onClick={() => recargar()}>Actualizar solicitudes</button>
    {cargando && <p>Cargando solicitudes…</p>}
    {error && <p role="alert">{String(error)}</p>}
    {!cargando && !error && datos?.length === 0 && <p>No hay solicitudes pendientes.</p>}
    {!!datos?.length && <div className="tabla-scroll"><table>
      <thead><tr><th>RUC</th><th>Proveedor</th><th>Gestor solicitante</th><th>Usuario</th><th>Responsable</th><th>Archivos únicos</th><th>Solicitudes</th><th>Detalle</th></tr></thead>
      <tbody>{datos.map((lote) => {
        const gestor = gestores.find((g) => g.id === lote.gestor_solicitante_id);
        const usuario = miembros.find((m) => m.id === gestor?.usuario_id);
        const responsable = miembros.find((m) => m.id === usuario?.responsable_id);
        const empresa = empresas.find((e) => e.ruc === lote.ruc_emisor);
        return <tr key={lote.ruc_emisor + ":" + lote.gestor_solicitante_id}>
          <td>{lote.ruc_emisor}</td><td>{empresa?.razon_social ?? "Sin nombre registrado"}</td>
          <td>{gestor ? gestor.codigo + " · " + gestor.nombre : "No identificado"}</td>
          <td>{usuario ? usuario.codigo + " · " + usuario.nombre : "No identificado"}</td>
          <td>{responsable ? responsable.codigo + " · " + responsable.nombre : "No identificado"}</td>
          <td>{lote.cantidad_documentos}</td><td>{lote.cantidad_solicitudes}</td>
          <td><button type="button" onClick={() => setLoteSeleccionado(lote)}>Ver solicitudes</button></td>
        </tr>;
      })}</tbody>
    </table></div>}
    {loteSeleccionado && <DetalleLoteEmisor key={loteSeleccionado.ruc_emisor + ":" + loteSeleccionado.gestor_solicitante_id} lote={loteSeleccionado} gestores={gestores} miembros={miembros} />}
  </section>;
}

function OrganizacionAdmin({ permiteRevisionEmisores }: { permiteRevisionEmisores: boolean }) {
  const [verRevisionEmisores, setVerRevisionEmisores] = useState(false);
  const { datos: miembros, error, cargando, recargar } = useDatos<Miembro[]>("/api/v1/miembros");
  const { datos: gestores, recargar: recargarGestores } = useDatos<Gestor[]>("/api/v1/gestores");
  const { datos: vinculos, recargar: recargarVinculos } = useDatos<VinculoGerencia[]>("/api/v1/gerencias/vinculos");
  const { datos: cartera, recargar: recargarCartera } = useDatos<CarteraGerente[]>("/api/v1/gerencias/empresas");
  const { datos: empresas, recargar: recargarEmpresas } = useDatos<Empresa[]>("/api/v1/empresas");
  const [pestanaAdmin, setPestanaAdmin] = useState<"GERENTE" | "SECRETARIA" | "RESPONSABLE" | "USUARIO" | "GESTOR">("RESPONSABLE");
  const [codigo, setCodigo] = useState("");
  const [nombre, setNombre] = useState("");
  const [rol, setRol] = useState<RolMiembro>("RESPONSABLE");
  const [porcentajeConAgente, setPorcentajeConAgente] = useState("1.5");
  const [porcentajeSinAgente, setPorcentajeSinAgente] = useState("1.5");
  const [miembroEditando, setMiembroEditando] = useState<string | null>(null);
  const [usuarioId, setUsuarioId] = useState("");
  const [filtroResponsable, setFiltroResponsable] = useState("");
  const [codigoGestor, setCodigoGestor] = useState("");
  const [nombreGestor, setNombreGestor] = useState("");
  const [porcentajeGestor, setPorcentajeGestor] = useState("");
  const [gestorEditando, setGestorEditando] = useState<string | null>(null);
  const [credencial, setCredencial] = useState<CredencialTemporal | null>(null);
  const [mensaje, setMensaje] = useState("");
  const [gerenteCartera, setGerenteCartera] = useState("");
  const [rucAlta, setRucAlta] = useState("");
  const [razonAlta, setRazonAlta] = useState("");
  const [tipoAlta, setTipoAlta] = useState("CLIENTE");
  const [textoImportacion, setTextoImportacion] = useState("");

  const administradores = (miembros ?? []).filter((m) => m.rol === "ADMINISTRADOR" || m.rol === "SUPERADMIN");
  const gerentes = useMemo(
    () => (miembros ?? []).filter((m) => m.rol === "GERENTE"),
    [miembros],
  );
  const responsables = useMemo(
    () => (miembros ?? []).filter((m) => m.rol === "RESPONSABLE"),
    [miembros],
  );
  const usuarios = useMemo(
    () => (miembros ?? []).filter((m) => m.rol === "USUARIO"),
    [miembros],
  );

  const usuariosFiltrados = usuarios.filter((u) =>
    coincideAsignacion(filtroResponsable, u.responsable_id),
  );
  const miembrosVisibles = pestanaAdmin === "USUARIO"
    ? usuariosFiltrados
    : (miembros ?? []).filter((m) => m.rol === pestanaAdmin);

  const asignarAdministrador = async (responsable: Miembro, administradorId: string) => {
    try {
      await enviarJson<Miembro>(`/api/v1/miembros/${responsable.id}/administrador`, "PUT", {
        administrador_id: administradorId || null,
      });
      recargar();
      setMensaje("Administración actualizada para " + responsable.codigo);
    } catch (e) {
      setMensaje(e instanceof Error ? e.message : String(e));
    }
  };

  const altaCartera = async (evento: FormEvent<HTMLFormElement>) => {
    evento.preventDefault();
    if (!gerenteCartera) { setMensaje("Seleccione un Gerente."); return; }
    try {
      const res = await enviarJson<{ resultado: string }>("/api/v1/gerencias/empresas/alta", "POST", {
        gerente_id: gerenteCartera, ruc: rucAlta.trim(), razon_social: razonAlta.trim(),
        tipo_relacion: tipoAlta,
      });
      setMensaje(res.resultado === "CREADA" ? "Empresa registrada y vinculada." : "Empresa existente vinculada.");
      setRucAlta(""); setRazonAlta("");
      recargarEmpresas(); recargarCartera();
    } catch (e) { setMensaje(String(e)); }
  };
  const importarCartera = async () => {
    if (!gerenteCartera) { setMensaje("Seleccione un Gerente."); return; }
    const filas = textoImportacion.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
    const empresasImportadas = filas.map((linea) => {
      const [ruc, razon_social, tipo_relacion = "SIN_CLASIFICAR"] = linea.split(";").map((v) => v.trim());
      return { ruc, razon_social, tipo_relacion: tipo_relacion.toUpperCase() };
    });
    try {
      const res = await enviarJson<{ creadas: number; vinculadas: number }>(
        "/api/v1/gerencias/empresas/importar", "POST",
        { gerente_id: gerenteCartera, empresas: empresasImportadas },
      );
      setMensaje(`Importación completada: ${res.creadas} nuevas y ${res.vinculadas} vinculadas.`);
      setTextoImportacion(""); recargarEmpresas(); recargarCartera();
    } catch (e) { setMensaje(String(e)); }
  };
  const vincularEmpresa = async (gerenteId: string, empresaId: string, activo: boolean) => {
    try {
      await enviarJson<CarteraGerente>("/api/v1/gerencias/empresas", "PUT", {
        gerente_id: gerenteId, empresa_id: empresaId, activo,
      });
      recargarCartera();
      setMensaje("Cartera de Gerencia actualizada.");
    } catch (e) {
      setMensaje(e instanceof Error ? e.message : String(e));
    }
  };

  const vincularGerente = async (gerenteId: string, responsableId: string, activo: boolean) => {
    try {
      await enviarJson<VinculoGerencia>("/api/v1/gerencias/vinculos", "PUT", {
        gerente_id: gerenteId, responsable_id: responsableId, activo,
      });
      recargarVinculos();
      setMensaje("Vínculo entre Gerencia y Responsable actualizado.");
    } catch (e) {
      setMensaje(e instanceof Error ? e.message : String(e));
    }
  };

  const asignarResponsable = async (usuario: Miembro, responsableId: string) => {
    try {
      await enviarJson<Miembro>(`/api/v1/miembros/${usuario.id}/responsable`, "PUT", {
        responsable_id: responsableId || null,
      });
      recargar();
      setMensaje("Responsable actualizado para " + usuario.codigo);
    } catch (e) {
      setMensaje(e instanceof Error ? e.message : String(e));
    }
  };

  const guardarMiembro = async (e: FormEvent) => {
    e.preventDefault();
    setMensaje("");
    setCredencial(null);
    try {
      if (miembroEditando) {
        await enviarJson<Miembro>("/api/v1/miembros/" + miembroEditando, "PATCH", {
          codigo,
          nombre,
          rol,
          porcentaje_con_agente: rol === "USUARIO" ? porcentajeConAgente : null,
          porcentaje_sin_agente: rol === "USUARIO" ? porcentajeSinAgente : null,
        });
        setMensaje("Miembro actualizado.");
      } else {
        const alta = await enviarJson<AltaMiembro>("/api/v1/miembros", "POST", {
          codigo,
          nombre,
          rol,
          porcentaje_con_agente: rol === "USUARIO" ? porcentajeConAgente : null,
          porcentaje_sin_agente: rol === "USUARIO" ? porcentajeSinAgente : null,
        });
        setCredencial(alta.credencial);
        setMensaje("Miembro creado. Entrega la clave temporal de forma segura.");
      }
      setCodigo("");
      setNombre("");
      setRol(pestanaAdmin === "GESTOR" ? "USUARIO" : pestanaAdmin);
      setPorcentajeConAgente("1.5");
      setPorcentajeSinAgente("1.5");
      setMiembroEditando(null);
      recargar();
      recargarGestores();
    } catch (e) {
      setMensaje(e instanceof Error ? e.message : String(e));
    }
  };

  const cambiarAcceso = async (tipo: "miembros" | "gestores", id: string, activo: boolean) => {
    try {
      setMensaje("");
      await enviarJson(`/api/v1/${tipo}/${id}/estado-acceso`, "PATCH", { activo });
      setMensaje(activo ? "Acceso activado." : "Acceso desactivado. Sesiones cerradas.");
      setCredencial(null);
      recargar();
      recargarGestores();
    } catch (e) {
      setMensaje(e instanceof Error ? e.message : String(e));
    }
  };

  const restablecerMiembro = async (miembro: Miembro) => {
    setMensaje("");
    const nueva = await enviarJson<CredencialTemporal>(
      "/api/v1/miembros/" + miembro.id + "/restablecer-acceso",
      "POST",
    );
    setCredencial(nueva);
    setMensaje("Acceso restablecido. La nueva clave temporal se muestra una sola vez.");
  };

  const guardarGestor = async (e: FormEvent) => {
    e.preventDefault();
    setMensaje("");
    setCredencial(null);
    try {
      const datos = { codigo: codigoGestor, nombre: nombreGestor, usuario_id: usuarioId };
      if (gestorEditando) {
        await enviarJson<Gestor>("/api/v1/gestores/" + gestorEditando, "PATCH", {
          ...datos, porcentaje_comision: porcentajeGestor === "" ? null : porcentajeGestor,
        });
        setMensaje("Gestor actualizado.");
      } else {
        const alta = await enviarJson<AltaGestor>("/api/v1/gestores", "POST", datos);
        setCredencial(alta.credencial);
        setMensaje("Gestor creado y vinculado. Entrega la clave temporal de forma segura.");
      }
      setCodigoGestor("");
      setNombreGestor("");
      setPorcentajeGestor("");
      setGestorEditando(null);
      recargarGestores();
    } catch (e) {
      setMensaje(e instanceof Error ? e.message : String(e));
    }
  };

  const restablecerGestor = async (gestor: Gestor) => {
    const nueva = await enviarJson<CredencialTemporal>(
      "/api/v1/gestores/" + gestor.id + "/restablecer-acceso",
      "POST",
    );
    setCredencial(nueva);
    setMensaje("Acceso del Gestor restablecido.");
  };

  return (
    <>
      <h2>Organización</h2>
      {permiteRevisionEmisores && <>
        <button type="button" onClick={() => setVerRevisionEmisores((v) => !v)}>
          {verRevisionEmisores ? "Ocultar revisión de proveedores" : "Revisión de proveedores"}
        </button>
        {verRevisionEmisores && <RevisionEmisores gestores={gestores ?? []} miembros={miembros ?? []} empresas={empresas ?? []} />}
      </>}
      <p className="tenue">
        Administración crea miembros y puede crear Gestores. Cada alta genera una clave temporal
        que debe cambiarse en el primer inicio de sesión.
      </p>
      <section className="panel-alerta" aria-label="Configuración inicial">
        <h3>Configuración inicial de la Administración</h3>
        <p className="tenue">El administrador ya dispone de su cuenta. Asigne nombres y genere credenciales
          individuales para Gerencia y Secretaría; después cree Responsables. Cada integrante
          debe cambiar su clave temporal al ingresar.</p>
        <p><strong>Gerencia:</strong> {(miembros ?? []).some(m => m.rol === "GERENTE") ? "Configurada" : "Pendiente"} · <strong>Secretaría:</strong> {(miembros ?? []).some(m => m.rol === "SECRETARIA") ? "Configurada" : "Pendiente"} · <strong>Responsables:</strong> {(miembros ?? []).filter(m => m.rol === "RESPONSABLE").length}</p>
      </section>
      <Credencial credencial={credencial} />
      {mensaje && <p className="tenue">{mensaje}</p>}
      {error && <p className="error">{error}</p>}
      {cargando && <p>Cargando…</p>}

      <div className="acciones" role="tablist" aria-label="Niveles de la organización">
        {(["GERENTE", "SECRETARIA", "RESPONSABLE", "USUARIO", "GESTOR"] as const).map((p) => (
          <button key={p} type="button" role="tab" aria-selected={pestanaAdmin === p}
            onClick={() => { setPestanaAdmin(p); setMiembroEditando(null); setGestorEditando(null); setRol(p === "GESTOR" ? "USUARIO" : p); }}>
            {p === "GERENTE" ? "Gerencia" : p === "SECRETARIA" ? "Secretaría" : p === "RESPONSABLE" ? "Responsables" : p === "USUARIO" ? "Usuarios" : "Gestores"}
          </button>
        ))}
      </div>
      {pestanaAdmin === "RESPONSABLE" && <section className="panel-configuracion">
        <h3>Asignación de Responsables a Administradores</h3>
        <p className="tenue">Cada responsable tiene una cadena de Administración. El cambio no modifica pagos anteriores.</p>
        <table><thead><tr><th>Responsable</th><th>Administrador asignado</th></tr></thead><tbody>
          {responsables.map((r) => <tr key={r.id}><td>{r.codigo} · {r.nombre}</td><td>
            <select aria-label={`Administrador de ${r.codigo}`} value={r.responsable_id ?? ""}
              onChange={(e) => void asignarAdministrador(r, e.target.value)}>
              <option value="">Sin administrador asignado</option>
              {administradores.map((a) => <option key={a.id} value={a.id}>{a.codigo} · {a.nombre}</option>)}
            </select>
          </td></tr>)}
        </tbody></table>
      </section>}
      {pestanaAdmin === "GERENTE" && <section className="panel-configuracion">
        <h3>Gerentes y Responsables compartidos</h3>
        <p className="tenue">
          Un Responsable puede trabajar con varios Gerentes y conserva su propio equipo de
          Usuarios y Gestores. Active las relaciones autorizadas por la Administración.
        </p>
        <div className="tabla-responsive"><table><thead><tr>
          <th>Responsable</th>
          {gerentes.map((g) => <th key={g.id}>{g.codigo}</th>)}
        </tr></thead><tbody>
          {responsables.map((r) => <tr key={r.id}>
            <td>{r.codigo} · {r.nombre}</td>
            {gerentes.map((g) => {
              const activo = vinculos?.some(
                (v) => v.gerente_id === g.id && v.responsable_id === r.id && v.activo
              ) ?? false;
              return <td key={g.id}>
                <input type="checkbox" aria-label={`Asignar ${r.codigo} a ${g.codigo}`}
                  checked={activo}
                  onChange={(e) => void vincularGerente(g.id, r.id, e.target.checked)} />
              </td>;
            })}
          </tr>)}
        </tbody></table></div>
      </section>}
      {pestanaAdmin === "GERENTE" && <section className="panel-configuracion">
        <h3>Empresas por Gerente</h3>
        <div className="panel-configuracion">
          <h4>Alta e importación de empresas a una cartera</h4>
          <label>Gerente destinatario
            <select value={gerenteCartera} onChange={(e) => setGerenteCartera(e.target.value)}>
              <option value="">Seleccionar Gerente</option>
              {gerentes.map((g) => <option key={g.id} value={g.id}>{g.codigo} · {g.nombre}</option>)}
            </select>
          </label>
          <form className="filtros" onSubmit={(e) => void altaCartera(e)}>
            <label>RUC
              <input value={rucAlta} onChange={(e) => setRucAlta(e.target.value)}
                pattern="[0-9]{11}" maxLength={11} required placeholder="11 dígitos" />
            </label>
            <label>Razón social
              <input value={razonAlta} onChange={(e) => setRazonAlta(e.target.value)}
                minLength={3} maxLength={300} required />
            </label>
            <label>Relación comercial
              <select value={tipoAlta} onChange={(e) => setTipoAlta(e.target.value)}>
                <option value="CLIENTE">Cliente</option>
                <option value="PROVEEDOR">Proveedor</option>
                <option value="AMBOS">Ambos</option>
                <option value="SIN_CLASIFICAR">Sin clasificar</option>
              </select>
            </label>
            <button type="submit">Registrar o vincular empresa</button>
          </form>
          <p className="tenue">Importación: una empresa por línea, RUC;RAZÓN SOCIAL;TIPO.
            Si el RUC ya existe, se vincula sin modificar su ficha fiscal.</p>
          <textarea rows={4} value={textoImportacion}
            onChange={(e) => setTextoImportacion(e.target.value)}
            placeholder="20538821374;MAREUF;CLIENTE" />
          <label>Archivo CSV separado por punto y coma
            <input type="file" accept=".csv,.txt,text/csv,text/plain"
              onChange={(e) => {
                const archivo = e.target.files?.[0];
                if (archivo) void archivo.text().then(setTextoImportacion);
              }} />
          </label>
          <button type="button" disabled={!textoImportacion.trim() || !gerenteCartera}
            onClick={() => void importarCartera()}>Importar empresas</button>
        </div>

        <p className="tenue">Las empresas comparten su RUC, pero solo los Gerentes
          autorizados pueden emitir pedidos de ellas.</p>
        <div style={{ overflowX: "auto" }}><table><thead><tr>
          <th>Empresa</th>
          {gerentes.map((g) => <th key={g.id}>{g.codigo}</th>)}
        </tr></thead><tbody>
          {(empresas ?? []).map((e) => <tr key={e.id}>
            <td>{e.ruc} · {e.razon_social}</td>
            {gerentes.map((g) => <td key={g.id}>
              <input
                type="checkbox"
                aria-label={`Permitir ${e.ruc} para ${g.codigo}`}
                checked={cartera?.some((x) =>
                  x.gerente_id === g.id && x.empresa_id === e.id && x.activo
                ) ?? false}
                onChange={(ev) => void vincularEmpresa(g.id, e.id, ev.target.checked)}
              />
            </td>)}
          </tr>)}
        </tbody></table></div>
      </section>}
      {pestanaAdmin === "USUARIO" && <section className="panel-configuracion">
        <h3>Asignación de Usuarios a Responsables</h3>
        <p className="tenue">La asignación se limita a esta Administración. No modifica los pagos históricos.</p>
        <table>
          <thead><tr>
            <th>Usuario</th>
            <FiltroColumna titulo="Responsable asignado" etiqueta="Filtrar usuarios por responsable"
              todos="Todos los responsables" sinAsignar="Sin responsable"
              opciones={responsables} valor={filtroResponsable} alCambiar={setFiltroResponsable} />
          </tr></thead>
          <tbody>
          {usuariosFiltrados.length === 0 && filtroResponsable &&
            <tr><td colSpan={2}>No hay usuarios para este filtro.</td></tr>}
          {usuariosFiltrados.map((u) => (
            <tr key={u.id}>
              <td>{u.codigo} · {u.nombre}</td>
              <td><select value={u.responsable_id ?? ""} onChange={(e) => void asignarResponsable(u, e.target.value)}>
                <option value="">Sin asignar</option>
                {responsables.map((r) => <option key={r.id} value={r.id}>{r.codigo} · {r.nombre}</option>)}
              </select></td>
            </tr>
          ))}</tbody>
        </table>
      </section>}
      <div className="columnas">
        {pestanaAdmin !== "GESTOR" && <section>
          <h3>{miembroEditando ? "Editar miembro" : "Crear miembro"}</h3>
          <form onSubmit={guardarMiembro} className="formulario-linea">
            <input
              placeholder="Código automático (opcional, editable)"
              value={codigo}
              onChange={(e) => setCodigo(e.target.value.toUpperCase())}
            />
            <input placeholder="Nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
            <select
              value={rol}
              onChange={(e) => setRol(e.target.value as RolMiembro)}
            >
              {ROLES.filter((r) => r === pestanaAdmin).map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
            {rol === "USUARIO" && (
              <>
              <label>
                % con agente de retención
                <input type="number" step="0.0001" min="0" max="100"
                  value={porcentajeConAgente}
                  onChange={(e) => setPorcentajeConAgente(e.target.value)} required />
              </label>
              <label>
                % sin agente de retención
                <input type="number" step="0.0001" min="0" max="100"
                  value={porcentajeSinAgente}
                  onChange={(e) => setPorcentajeSinAgente(e.target.value)} required />
              </label>
              </>
            )}
            <button type="submit">{miembroEditando ? "Guardar" : "Crear y generar clave"}</button>
            {miembroEditando && (
              <button type="button" onClick={() => {
                setMiembroEditando(null);
                setCodigo("");
                setNombre("");
                setRol("USUARIO");
                setPorcentajeConAgente("1.5");
      setPorcentajeSinAgente("1.5");
              }}>Cancelar</button>
            )}
          </form>

          <h3>Miembros</h3>
          <table>
            <thead><tr><th>Código</th><th>Nombre</th><th>Rol</th><th>% con agente</th><th>% sin agente</th>
              {pestanaAdmin === "USUARIO" && <FiltroColumna titulo="Responsable" etiqueta="Filtrar miembros por responsable"
                todos="Todos los responsables" sinAsignar="Sin responsable"
                opciones={responsables} valor={filtroResponsable} alCambiar={setFiltroResponsable} />}
              {(pestanaAdmin === "USUARIO" || pestanaAdmin === "RESPONSABLE") && <th>Estado de acceso</th>}
              <th>Acciones</th></tr></thead>
            <tbody>
              {pestanaAdmin === "USUARIO" && miembrosVisibles.length === 0 && filtroResponsable &&
                <tr><td colSpan={8}>No hay usuarios para este filtro.</td></tr>}
              {miembrosVisibles.map((m) => (
                <tr key={m.id}>
                  <td>{m.codigo}</td><td>{m.nombre}</td><td>{m.rol}</td>
                  <td>{m.rol === "USUARIO" ? (m.porcentaje_con_agente ?? m.porcentaje_produccion ?? "0") + "%" : "—"}</td>
                  <td>{m.rol === "USUARIO" ? (m.porcentaje_sin_agente ?? m.porcentaje_produccion ?? "0") + "%" : "—"}</td>
                  {pestanaAdmin === "USUARIO" && <td>
                    {responsables.find((r) => r.id === m.responsable_id)?.nombre ??
                      (m.responsable_id ? "No disponible" : "Sin asignar")}
                  </td>}
                  {(m.rol === "USUARIO" || m.rol === "RESPONSABLE") && <td>
                    <EstadoAcceso activo={m.acceso_activo} alCambiar={() => void cambiarAcceso("miembros", m.id, !m.acceso_activo)} />
                  </td>}
                  <td>
                    <button type="button" onClick={() => {
                      setMiembroEditando(m.id);
                      setCodigo(m.codigo);
                      setNombre(m.nombre);
                      setRol(m.rol);
                      setPorcentajeConAgente(m.porcentaje_con_agente ?? m.porcentaje_produccion ?? "1.5");
                      setPorcentajeSinAgente(m.porcentaje_sin_agente ?? m.porcentaje_produccion ?? "1.5");
                    }}>Editar</button>{" "}
                    <button type="button" onClick={() => void restablecerMiembro(m)}>
                      Restablecer acceso
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>}

        {pestanaAdmin === "GESTOR" && <section>
          <h3>{gestorEditando ? "Editar gestor" : "Crear gestor"}</h3>
          <form onSubmit={guardarGestor} className="formulario-linea">
            <select value={usuarioId} onChange={(e) => setUsuarioId(e.target.value)} required>
              <option value="">Usuario propietario</option>
              {usuarios.map((u) => <option key={u.id} value={u.id}>{u.codigo} · {u.nombre}</option>)}
            </select>
            <input
              placeholder="Código automático (opcional, editable)"
              value={codigoGestor}
              onChange={(e) => setCodigoGestor(e.target.value.toUpperCase())}
            />
            <input
              placeholder="Nombre gestor"
              value={nombreGestor}
              onChange={(e) => setNombreGestor(e.target.value)}
              required
            />
            {gestorEditando && <label>Tasa Gestor (%)
              <input type="number" min="0" max="100" step="0.0001"
                placeholder="Porcentaje de comisión"
                value={porcentajeGestor}
                onChange={(e) => setPorcentajeGestor(e.target.value)} />
            </label>}
            <button type="submit">{gestorEditando ? "Guardar gestor" : "Crear y generar clave"}</button>
            {gestorEditando && (
              <button type="button" onClick={() => {
                setGestorEditando(null);
                setCodigoGestor("");
                setNombreGestor("");
              }}>Cancelar</button>
            )}
          </form>
          <TablaGestores
            gestores={gestores ?? []}
            usuarios={usuarios}
            alEditar={(g) => {
              setGestorEditando(g.id);
              setUsuarioId(g.usuario_id ?? "");
              setCodigoGestor(g.codigo);
              setNombreGestor(g.nombre);
              setPorcentajeGestor(g.porcentaje_comision ?? "");
            }}
            alRestablecer={(g) => void restablecerGestor(g)}
            alCambiarAcceso={(g) => void cambiarAcceso("gestores", g.id, !g.acceso_activo)}
          />
        </section>}
      </div>
    </>
  );
}

function OrganizacionResponsable() {
  const [pestana, setPestana] = useState<"USUARIO" | "GESTOR">("USUARIO");
  const { datos: gestores, error } = useDatos<Gestor[]>("/api/v1/gestores");
  const { datos: usuarios } = useDatos<Miembro[]>("/api/v1/miembros/mis-usuarios");
  const [filtroUsuario, setFiltroUsuario] = useState("");
  const gestoresVisibles = (gestores ?? []).filter((g) =>
    coincideAsignacion(filtroUsuario, g.usuario_id),
  );
  return <>
    <h2>Organización de mi equipo</h2>
    <div className="acciones" role="tablist" aria-label="Mi organización">
      <button type="button" role="tab" aria-selected={pestana === "USUARIO"} onClick={() => setPestana("USUARIO")}>Usuarios</button>
      <button type="button" role="tab" aria-selected={pestana === "GESTOR"} onClick={() => setPestana("GESTOR")}>Gestores</button>
    </div>
    {pestana === "USUARIO" ? <MiEquipoResponsable /> : <>
      <p className="tenue">Gestores vinculados a los usuarios de tu equipo. Las asignaciones se modifican desde Administración o desde el usuario propietario.</p>
      {error && <p className="error">{error}</p>}
      <table><thead><tr><th>Gestor</th><FiltroColumna titulo="Usuario propietario" etiqueta="Filtrar gestores por usuario"
        todos="Todos los usuarios" sinAsignar="Sin usuario"
        opciones={usuarios ?? []} valor={filtroUsuario} alCambiar={setFiltroUsuario} /></tr></thead><tbody>
        {gestoresVisibles.length === 0 && filtroUsuario &&
          <tr><td colSpan={2}>No hay gestores para este filtro.</td></tr>}
        {gestoresVisibles.map(g => { const u = (usuarios ?? []).find(u => u.id === g.usuario_id); return <tr key={g.id}><td>{g.codigo} · {g.nombre}</td><td>{u ? `${u.codigo} · ${u.nombre}` : "No disponible"}</td></tr>; })}
      </tbody></table>
    </>}
  </>;
}

function OrganizacionUsuario({ sesion }: { sesion: SesionActual }) {
  const { datos: gestores, error, cargando, recargar } = useDatos<Gestor[]>("/api/v1/gestores");
  const [codigo, setCodigo] = useState("");
  const [nombre, setNombre] = useState("");
  const [editando, setEditando] = useState<string | null>(null);
  const [credencial, setCredencial] = useState<CredencialTemporal | null>(null);
  const [mensaje, setMensaje] = useState("");

  const guardar = async (e: FormEvent) => {
    e.preventDefault();
    if (!sesion.usuario_id) return;
    setCredencial(null);
    try {
      const datos = { codigo, nombre, usuario_id: sesion.usuario_id };
      if (editando) {
        await enviarJson<Gestor>("/api/v1/gestores/" + editando, "PATCH", datos);
        setMensaje("Gestor actualizado.");
      } else {
        const alta = await enviarJson<AltaGestor>("/api/v1/gestores", "POST", datos);
        setCredencial(alta.credencial);
        setMensaje("Gestor creado. Entrega la clave temporal de forma segura.");
      }
      setCodigo("");
      setNombre("");
      setEditando(null);
      recargar();
    } catch (e) {
      setMensaje(e instanceof Error ? e.message : String(e));
    }
  };

  const restablecer = async (g: Gestor) => {
    const nueva = await enviarJson<CredencialTemporal>(
      "/api/v1/gestores/" + g.id + "/restablecer-acceso",
      "POST",
    );
    setCredencial(nueva);
    setMensaje("Acceso del Gestor restablecido.");
  };

  return (
    <>
      <h2>Mis Gestores</h2>
      <p className="tenue">
        Usuario {sesion.codigo} · {sesion.nombre}. Los Gestores creados aquí quedan vinculados
        automáticamente a tu Usuario.
      </p>
      <Credencial credencial={credencial} />
      {mensaje && <p className="tenue">{mensaje}</p>}
      {error && <p className="error">{error}</p>}
      {cargando && <p>Cargando…</p>}
      <form onSubmit={guardar} className="formulario-linea">
        <input
          placeholder="Código / login gestor"
          value={codigo}
          onChange={(e) => setCodigo(e.target.value.toUpperCase())}
          required
        />
        <input placeholder="Nombre gestor" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
        <button type="submit">{editando ? "Guardar gestor" : "Crear Gestor"}</button>
        {editando && <button type="button" onClick={() => {
          setEditando(null);
          setCodigo("");
          setNombre("");
        }}>Cancelar</button>}
      </form>
      <TablaGestores
        gestores={gestores ?? []}
        usuarios={[]}
        alEditar={(g) => {
          setEditando(g.id);
          setCodigo(g.codigo);
          setNombre(g.nombre);
        }}
        alRestablecer={(g) => void restablecer(g)}
        ocultarUsuario
      />
    </>
  );
}

function Credencial({ credencial }: { credencial: CredencialTemporal | null }) {
  if (!credencial) return null;
  return (
    <div className="credencial-temporal">
      <strong>Credencial temporal — mostrar una sola vez</strong>
      <div>Usuario: <code>{credencial.login}</code></div>
      <div>Clave temporal: <code>{credencial.clave_temporal}</code></div>
      <small>El titular deberá cambiarla al iniciar sesión.</small>
    </div>
  );
}

function TablaGestores({
  gestores,
  usuarios,
  alEditar,
  alRestablecer,
  alCambiarAcceso,
  ocultarUsuario = false,
}: {
  gestores: Gestor[];
  usuarios: Miembro[];
  alEditar: (gestor: Gestor) => void;
  alRestablecer: (gestor: Gestor) => void;
  alCambiarAcceso?: (gestor: Gestor) => void;
  ocultarUsuario?: boolean;
}) {
  const [filtroUsuario, setFiltroUsuario] = useState("");
  const gestoresVisibles = gestores.filter((g) =>
    ocultarUsuario || coincideAsignacion(filtroUsuario, g.usuario_id),
  );
  return (
    <>
      <h3>Gestores</h3>
      <table>
        <thead>
          <tr>
            <th>Gestor</th>
            <th>Comisión</th>
            {!ocultarUsuario && <FiltroColumna titulo="Usuario" etiqueta="Filtrar gestores por usuario"
              todos="Todos los usuarios" sinAsignar="Sin usuario"
              opciones={usuarios} valor={filtroUsuario} alCambiar={setFiltroUsuario} />}
            <th>Estado de acceso</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {!ocultarUsuario && gestoresVisibles.length === 0 && filtroUsuario &&
            <tr><td colSpan={5}>No hay gestores para este filtro.</td></tr>}
          {gestoresVisibles.map((g) => {
            const usuario = usuarios.find((u) => u.id === g.usuario_id);
            return (
              <tr key={g.id}>
                <td>{g.codigo} · {g.nombre}</td>
                <td>{g.porcentaje_comision != null ? g.porcentaje_comision + "%" : "Sin configurar"}</td>
                {!ocultarUsuario && <td>{usuario ? usuario.codigo + " · " + usuario.nombre : "Sin usuario"}</td>}
                <td><EstadoAcceso activo={g.acceso_activo} alCambiar={alCambiarAcceso ? () => alCambiarAcceso(g) : undefined} /></td>
                <td>
                  <button type="button" onClick={() => alEditar(g)}>Editar</button>{" "}
                  <button type="button" onClick={() => alRestablecer(g)}>Restablecer acceso</button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </>
  );
}
