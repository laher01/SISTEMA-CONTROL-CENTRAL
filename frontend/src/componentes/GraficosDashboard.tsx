import "../dashboardGraficos.css";
import { alturaBarra, etiquetaFilaDashboard } from "../dashboardGraficos";
import { formatearMonto } from "../formato";
import type { AgrupacionDashboard, DashboardDesgloseFila, DashboardResumen } from "../tipos";

type Barra = { clave: string; etiqueta: string; valor: number; texto: string };

function Barras({ barras, titulo }: { barras: Barra[]; titulo: string }) {
  const maximo = Math.max(0, ...barras.map((barra) => Math.abs(barra.valor)));
  return (
    <div className="dashboard-barras" role="group" aria-label={titulo}>
      {barras.length === 0 ? <p>Sin datos para los filtros seleccionados.</p> : (
        <ul className="dashboard-barras-lista">
          {barras.map((barra) => (
            <li key={barra.clave} className="dashboard-barra">
              <strong className="dashboard-barra-valor">{barra.texto}</strong>
              <div className="dashboard-barra-pista" aria-hidden="true">
                <span className={barra.valor < 0 ? "dashboard-barra-negativa" : undefined}
                  style={{ height: alturaBarra(barra.valor, maximo) }} />
              </div>
              <span className="dashboard-barra-etiqueta">{barra.etiqueta}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function GraficoVistaOrdenada({ filas, agrupacion }: {
  filas: DashboardDesgloseFila[];
  agrupacion: AgrupacionDashboard;
}) {
  return (
    <section className="dashboard-grafico" aria-label="Gráfico de vista ordenada">
      <h3>Vista ordenada · expedientes</h3>
      <p className="dashboard-grafico-ayuda">Cantidades según la agrupación, el orden y los filtros seleccionados.</p>
      <Barras titulo="Expedientes por grupo" barras={filas.map((fila) => ({
        clave: fila.clave,
        etiqueta: etiquetaFilaDashboard(fila, agrupacion),
        valor: fila.expedientes,
        texto: fila.expedientes.toLocaleString("es-PE"),
      }))} />
    </section>
  );
}

export function GraficoMontos({ montos }: { montos: DashboardResumen["montos"] }) {
  return (
    <section className="dashboard-grafico" aria-label="Gráfico de montos">
      <h3>Montos</h3>
      <p className="dashboard-grafico-ayuda">Escala independiente por moneda. Bancarización y retención son clasificaciones del mismo total; no se suman entre sí.</p>
      {montos.length === 0 && <p>Sin datos para los filtros seleccionados.</p>}
      {montos.map((monto) => (
        <div className="dashboard-grafico-moneda" key={monto.moneda}>
          <h4>{monto.moneda}</h4>
          <Barras titulo={`Montos en ${monto.moneda}`} barras={[
            { clave: "bancarizable", etiqueta: "Bancarizable", valor: Number(monto.bancarizable) },
            { clave: "no_bancarizable", etiqueta: "No bancarizable", valor: Number(monto.no_bancarizable) },
            { clave: "con_agente", etiqueta: "Con agente de retención", valor: Number(monto.con_agente_retencion) },
            { clave: "sin_agente", etiqueta: "Sin agente de retención", valor: Number(monto.sin_agente_retencion) },
          ].map((barra) => ({ ...barra, texto: formatearMonto(monto.moneda, barra.valor) }))} />
        </div>
      ))}
    </section>
  );
}
