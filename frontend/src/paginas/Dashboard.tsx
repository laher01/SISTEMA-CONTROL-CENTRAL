import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { useDatos } from "../api";
import { Estado } from "../componentes";
import { ETIQUETA_ALERTA, ETIQUETA_ESTADO, formatearMonto } from "../formato";
import {
  ESTADOS_EXPEDIENTE,
  TIPOS_ALERTA,
  type AgrupacionDashboard,
  type DashboardDesglose,
  type DashboardResumen,
  type Empresa,
  type Miembro,
} from "../tipos";

export default function Dashboard() {
  const { datos, error, cargando } = useDatos<DashboardResumen>("/api/v1/dashboard/resumen");
  const { datos: usuarios } = useDatos<Miembro[]>("/api/v1/miembros?rol=USUARIO");
  const { datos: empresas } = useDatos<Empresa[]>("/api/v1/empresas");

  const [agruparPor, setAgruparPor] = useState<AgrupacionDashboard>("usuario");
  const [orden, setOrden] = useState<"asc" | "desc">("desc");
  const [usuarioId, setUsuarioId] = useState("");
  const [emisorId, setEmisorId] = useState("");
  const [receptorId, setReceptorId] = useState("");
  const [fechaDesde, setFechaDesde] = useState("");
  const [fechaHasta, setFechaHasta] = useState("");

  const rutaDesglose = useMemo(() => {
    const params = new URLSearchParams({
      agrupar_por: agruparPor,
      orden,
    });
    if (usuarioId) params.set("usuario_id", usuarioId);
    if (emisorId) params.set("emisor_id", emisorId);
    if (receptorId) params.set("receptor_id", receptorId);
    if (fechaDesde) params.set("fecha_desde", fechaDesde);
    if (fechaHasta) params.set("fecha_hasta", fechaHasta);
    return `/api/v1/dashboard/desglose?${params.toString()}`;
  }, [agruparPor, orden, usuarioId, emisorId, receptorId, fechaDesde, fechaHasta]);

  const {
    datos: desglose,
    error: errorDesglose,
    cargando: cargandoDesglose,
  } = useDatos<DashboardDesglose>(rutaDesglose);

  const pendientes =
    (datos?.documentos_pendientes.PENDIENTE_CLASIFICACION ?? 0) +
    (datos?.documentos_pendientes.PENDIENTE_RELACION ?? 0);

  const limpiarFiltros = () => {
    setUsuarioId("");
    setEmisorId("");
    setReceptorId("");
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
                    <option value="usuario">Usuario</option>
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
                <label>
                  Usuario
                  <select value={usuarioId} onChange={(e) => setUsuarioId(e.target.value)}>
                    <option value="">Todos</option>
                    {(usuarios ?? []).map((usuario) => (
                      <option key={usuario.id} value={usuario.id}>
                        {usuario.codigo} · {usuario.nombre}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Emisor
                  <select value={emisorId} onChange={(e) => setEmisorId(e.target.value)}>
                    <option value="">Todos</option>
                    {(empresas ?? []).map((empresa) => (
                      <option key={empresa.id} value={empresa.id}>
                        {empresa.razon_social} · {empresa.ruc}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Receptor
                  <select value={receptorId} onChange={(e) => setReceptorId(e.target.value)}>
                    <option value="">Todos</option>
                    {(empresas ?? []).map((empresa) => (
                      <option key={empresa.id} value={empresa.id}>
                        {empresa.razon_social} · {empresa.ruc}
                      </option>
                    ))}
                  </select>
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
    usuario: "Usuario",
    emisor: "Empresa emisora",
    receptor: "Empresa receptora",
    dia: "Día",
    mes: "Mes",
    anio: "Año",
  };
  return etiquetas[agruparPor];
}
