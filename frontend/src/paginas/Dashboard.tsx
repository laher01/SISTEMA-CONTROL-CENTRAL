import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { useDatos } from "../api";
import { agrupacionInicial, controlesDashboard } from "../dashboardRoles";
import { Estado } from "../componentes";
import { ETIQUETA_ALERTA, ETIQUETA_ESTADO, formatearMonto } from "../formato";
import {
  ESTADOS_EXPEDIENTE,
  TIPOS_ALERTA,
  type AgrupacionDashboard,
  type DashboardDesglose,
  type DashboardResumen,
  type SesionActual,
} from "../tipos";

export default function Dashboard({ sesion }: { sesion: SesionActual }) {
  const { responsable: esAdministracion, usuario: mostrarUsuario, gestor: mostrarGestor } = controlesDashboard(sesion.rol);

  const [agruparPor, setAgruparPor] = useState<AgrupacionDashboard>(agrupacionInicial(sesion.rol));
  const [orden, setOrden] = useState<"asc" | "desc">("desc");
  const [responsableId, setResponsableId] = useState("");
  const [usuarioId, setUsuarioId] = useState("");
  const [gestorId, setGestorId] = useState("");
  const [mes, setMes] = useState("");
  const [emisorId, setEmisorId] = useState("");
  const [receptorId, setReceptorId] = useState("");
  const [tipoEmpresa, setTipoEmpresa] = useState<"" | "A" | "B">("");
  const [fechaDesde, setFechaDesde] = useState("");
  const [fechaHasta, setFechaHasta] = useState("");

  const filtros = useMemo(() => {
    const params = new URLSearchParams();
    if (responsableId) params.set("responsable_id", responsableId);
    if (usuarioId) params.set("usuario_id", usuarioId);
    if (gestorId) params.set("gestor_id", gestorId);
    if (emisorId) params.set("emisor_id", emisorId);
    if (receptorId) params.set("receptor_id", receptorId);
    if (tipoEmpresa) params.set("tipo_empresa", tipoEmpresa);
    if (fechaDesde) params.set("fecha_desde", fechaDesde);
    if (fechaHasta) params.set("fecha_hasta", fechaHasta);
    if (mes) params.set("mes", mes);
    return params.toString();
  }, [responsableId, usuarioId, gestorId, emisorId, receptorId, tipoEmpresa, fechaDesde, fechaHasta, mes]);

  const rutaDesglose = `/api/v1/dashboard/desglose?agrupar_por=${agruparPor}&orden=${orden}&${filtros}`;
  const { datos, error, cargando } = useDatos<DashboardResumen>(`/api/v1/dashboard/resumen?${filtros}`);
  const { datos: opciones } = useDatos<{
    responsables: { id: string; nombre: string }[];
    usuarios: { id: string; nombre: string }[];
    gestores: { id: string; nombre: string }[];
    emisores: { id: string; nombre: string }[];
    receptores: { id: string; nombre: string }[];
  }>(`/api/v1/dashboard/opciones?${filtros}`);

  const {
    datos: desglose,
    error: errorDesglose,
    cargando: cargandoDesglose,
  } = useDatos<DashboardDesglose>(rutaDesglose);

  const pendientes =
    (datos?.documentos_pendientes.PENDIENTE_CLASIFICACION ?? 0) +
    (datos?.documentos_pendientes.PENDIENTE_RELACION ?? 0);

  const limpiarFiltros = () => {
    setResponsableId("");
    setUsuarioId("");
    setGestorId("");
    setMes("");
    setEmisorId("");
    setReceptorId("");
    setTipoEmpresa("");
    setFechaDesde("");
    setFechaHasta("");
  };

  return (
    <>
      <h2>Dashboard</h2>
      <Estado cargando={cargando} error={error} vacio={!datos}>
        {datos && (
          <>
            <section className="tarjetas">
              <div className="tarjeta">
                <span className="cifra">{datos.expedientes_total}</span>
                <span>Expedientes</span>
              </div>
              {ESTADOS_EXPEDIENTE.map((estado) => (
                <Link
                  key={estado}
                  to={`/expedientes?estado=${estado}`}
                  className={`tarjeta borde-${estado.toLowerCase()}`}
                >
                  <span className="cifra">{datos.por_estado[estado]}</span>
                  <span>{ETIQUETA_ESTADO[estado]}</span>
                </Link>
              ))}
              <Link to="/expedientes?pendiente_aprobacion=true" className="tarjeta">
                <span className="cifra">{datos.pendientes_aprobacion}</span>
                <span>Pendientes de aprobación</span>
              </Link>
              <Link to="/pendientes" className="tarjeta">
                <span className="cifra">{pendientes}</span>
                <span>Documentos sin expediente</span>
              </Link>
              <Link to="/expedientes?pendiente_aprobacion=true" className="tarjeta borde-rojo">
                <span className="cifra">{datos.documentos_receptor_no_autorizado}</span>
                <span>Documentos de receptores no autorizados</span>
              </Link>
            </section>

            <section>
              <h3>Vista ordenada</h3>
              <div className="filtros">
                <label>
                  Agrupar por
                  <select
                    value={agruparPor}
                    onChange={(e) => setAgruparPor(e.target.value as AgrupacionDashboard)}
                  >
                    {esAdministracion && <option value="responsable">Responsable</option>}
                    {mostrarUsuario && <option value="usuario">Usuario</option>}
                    {mostrarGestor && <option value="gestor">Gestor</option>}
                    <option value="tipo_empresa">Tipo de empresa</option>
                    <option value="emisor">Empresa emisora</option>
                    <option value="receptor">Empresa receptora</option>
                    <option value="dia">Día</option>
                    <option value="mes">Mes</option>
                    <option value="anio">Año</option>
                  </select>
                </label>
                <label>
                  Orden
                  <select value={orden} onChange={(e) => setOrden(e.target.value as "asc" | "desc")}>
                    <option value="desc">Mayor / más reciente</option>
                    <option value="asc">Menor / más antiguo</option>
                  </select>
                </label>
                {esAdministracion && <label>
                  Responsable
                  <select value={responsableId} onChange={(e) => {
                    setResponsableId(e.target.value);
                    setUsuarioId(""); setGestorId(""); setEmisorId(""); setReceptorId("");
                  }}>
                    <option value="">Todos</option>
                    {(opciones?.responsables ?? []).map((x) => <option key={x.id} value={x.id}>{x.nombre}</option>)}
                  </select>
                </label>}
                {mostrarUsuario && <label>
                  Usuario
                  <select value={usuarioId} onChange={(e) => {
                    setUsuarioId(e.target.value);
                    setGestorId(""); setEmisorId(""); setReceptorId("");
                  }}>
                    <option value="">Todos</option>
                    {(opciones?.usuarios ?? []).map((x) => <option key={x.id} value={x.id}>{x.nombre}</option>)}
                  </select>
                </label>}
                {mostrarGestor && <label>
                  Gestor
                  <select value={gestorId} onChange={(e) => {
                    setGestorId(e.target.value); setEmisorId(""); setReceptorId("");
                  }}>
                    <option value="">Todos</option>
                    {(opciones?.gestores ?? []).map((x) => <option key={x.id} value={x.id}>{x.nombre}</option>)}
                  </select>
                </label>}
                <label>
                  Emisor
                  <select value={emisorId} onChange={(e) => {setEmisorId(e.target.value); setReceptorId("");}}>
                    <option value="">Todos</option>
                    {(opciones?.emisores ?? []).map((x) => <option key={x.id} value={x.id}>{x.nombre}</option>)}
                  </select>
                </label>
                <label>
                  Receptor
                  <select value={receptorId} onChange={(e) => setReceptorId(e.target.value)}>
                    <option value="">Todos</option>
                    {(opciones?.receptores ?? []).map((x) => <option key={x.id} value={x.id}>{x.nombre}</option>)}
                  </select>
                </label>
                <label>
                  Tipo de empresa (emisor / proveedor)
                  <select
                    value={tipoEmpresa}
                    onChange={(e) => setTipoEmpresa(e.target.value as "" | "A" | "B")}
                  >
                    <option value="">Todas</option>
                    <option value="A">Tipo A</option>
                    <option value="B">Tipo B</option>
                  </select>
                </label>
                <label>
                  Mes de emisión
                  <input type="month" value={mes} onChange={(e) => setMes(e.target.value)} />
                </label>
                <label>
                  Desde
                  <input
                    type="date"
                    value={fechaDesde}
                    onChange={(e) => setFechaDesde(e.target.value)}
                  />
                </label>
                <label>
                  Hasta
                  <input
                    type="date"
                    value={fechaHasta}
                    onChange={(e) => setFechaHasta(e.target.value)}
                  />
                </label>
                <button onClick={limpiarFiltros}>Limpiar filtros</button>
              </div>

              <Estado
                cargando={cargandoDesglose}
                error={errorDesglose}
                vacio={!desglose || desglose.filas.length === 0}
              >
                {desglose && desglose.filas.length > 0 && (
                  <table>
                    <thead>
                      <tr>
                        <th>{etiquetaAgrupacion(agruparPor)}</th>
                        <th>RUC</th>
                        <th className="num">Expedientes</th>
                        <th className="num">Total PEN</th>
                        <th className="num">Total USD</th>
                      </tr>
                    </thead>
                    <tbody>
                      {desglose.filas.map((fila) => (
                        <tr key={fila.clave}>
                          <td>{fila.etiqueta}</td>
                          <td>{fila.ruc ?? "—"}</td>
                          <td className="num">{fila.expedientes}</td>
                          <td className="num">{formatearMonto("PEN", fila.total_pen)}</td>
                          <td className="num">{formatearMonto("USD", fila.total_usd)}</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr>
                        <th>Total filtrado</th><th>—</th>
                        <th className="num">{desglose.filas.reduce((sum, fila) => sum + fila.expedientes, 0)}</th>
                        <th className="num">{formatearMonto("PEN", desglose.filas.reduce((sum, fila) => sum + Number(fila.total_pen), 0))}</th>
                        <th className="num">{formatearMonto("USD", desglose.filas.reduce((sum, fila) => sum + Number(fila.total_usd), 0))}</th>
                      </tr>
                    </tfoot>
                  </table>
                )}
              </Estado>
            </section>

            <div className="columnas">
              <section>
                <h3>Alertas abiertas</h3>
                <table>
                  <tbody>
                    {TIPOS_ALERTA.map((tipo) => (
                      <tr key={tipo}>
                        <td>
                          <Link to={`/alertas?tipo=${tipo}`}>{ETIQUETA_ALERTA[tipo]}</Link>
                        </td>
                        <td className="num">{datos.alertas_abiertas[tipo]}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
              <section>
                <h3>Montos</h3>
                <table>
                  <thead>
                    <tr>
                      <th>Moneda</th>
                      <th className="num">Bancarizable</th>
                      <th className="num">No bancarizable</th>
                    </tr>
                  </thead>
                  <tbody>
                    {datos.montos.map((m) => (
                      <tr key={m.moneda}>
                        <td>{m.moneda}</td>
                        <td className="num">{formatearMonto(m.moneda, m.bancarizable)}</td>
                        <td className="num">{formatearMonto(m.moneda, m.no_bancarizable)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            </div>
          </>
        )}
      </Estado>
    </>
  );
}

function etiquetaAgrupacion(agruparPor: AgrupacionDashboard): string {
  const etiquetas: Record<AgrupacionDashboard, string> = {
    responsable: "Responsable",
    usuario: "Usuario",
    gestor: "Gestor",
    tipo_empresa: "Tipo de empresa",
    emisor: "Empresa emisora",
    receptor: "Empresa receptora",
    dia: "Día",
    mes: "Mes",
    anio: "Año",
  };
  return etiquetas[agruparPor];
}
