import { Link } from "react-router-dom";

import { useDatos } from "../api";
import { Estado } from "../componentes";
import { ETIQUETA_ALERTA, ETIQUETA_ESTADO, formatearMonto } from "../formato";
import { ESTADOS_EXPEDIENTE, TIPOS_ALERTA, type DashboardResumen } from "../tipos";

export default function Dashboard() {
  const { datos, error, cargando } = useDatos<DashboardResumen>("/api/v1/dashboard/resumen");
  const pendientes =
    (datos?.documentos_pendientes.PENDIENTE_CLASIFICACION ?? 0) +
    (datos?.documentos_pendientes.PENDIENTE_RELACION ?? 0);

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
