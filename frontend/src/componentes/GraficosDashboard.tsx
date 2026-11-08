import { useId, type KeyboardEvent, type ReactNode } from "react";
import "../dashboardGraficos.css";
import { alturaBarra, etiquetaFilaDashboard, sectoresCirculares, type VistaGrafico } from "../dashboardGraficos";
import { formatearMonto } from "../formato";
import type { AgrupacionDashboard, DashboardDesgloseFila, DashboardResumen } from "../tipos";

type Barra = { clave: string; etiqueta: string; valor: number; texto: string };

const VISTAS: { valor: VistaGrafico; etiqueta: string }[] = [
  { valor: "barras", etiqueta: "Barras verticales" },
  { valor: "circular", etiqueta: "Circular 3D" },
  { valor: "lineas", etiqueta: "Líneas" },
];

export function VistasGraficosDashboard({ vista, alCambiar, children }: {
  vista: VistaGrafico;
  alCambiar: (vista: VistaGrafico) => void;
  children: ReactNode;
}) {
  const id = useId();
  const teclado = (evento: KeyboardEvent<HTMLButtonElement>, indice: number) => {
    let destino: number;
    if (evento.key === "ArrowRight") destino = (indice + 1) % VISTAS.length;
    else if (evento.key === "ArrowLeft") destino = (indice + VISTAS.length - 1) % VISTAS.length;
    else if (evento.key === "Home") destino = 0;
    else if (evento.key === "End") destino = VISTAS.length - 1;
    else return;
    evento.preventDefault();
    const seleccion = VISTAS[destino];
    if (!seleccion) return;
    alCambiar(seleccion.valor);
    evento.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>("[role=tab]")[destino]?.focus();
  };
  return (
    <section className="dashboard-vistas" aria-label="Vistas de gráficos">
      <div className="dashboard-pestanas" role="tablist" aria-label="Tipo de gráfico">
        {VISTAS.map((opcion, indice) => (
          <button key={opcion.valor} type="button" role="tab" id={`${id}-${opcion.valor}`}
            aria-selected={vista === opcion.valor} aria-controls={`${id}-panel`}
            tabIndex={vista === opcion.valor ? 0 : -1}
            onClick={() => alCambiar(opcion.valor)} onKeyDown={(evento) => teclado(evento, indice)}>
            {opcion.etiqueta}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`${id}-panel`} aria-labelledby={`${id}-${vista}`} className="dashboard-graficos">
        {children}
      </div>
    </section>
  );
}

function Circular({ barras, titulo }: { barras: Barra[]; titulo: string }) {
  const { valido, total, sectores, fondo } = sectoresCirculares(barras.map((barra) => barra.valor));
  return (
    <div className="dashboard-circular" role="group" aria-label={titulo}>
      {valido && total > 0 ? (
        <div className="dashboard-circular-perspectiva">
          <div className="dashboard-circular-disco" role="img" aria-label={`${titulo} · circular 3D`}
            style={{ background: fondo }} />
        </div>
      ) : <p className="dashboard-grafico-ayuda">{valido ? "Total cero: no hay proporciones para representar." : "Los valores con signo se muestran en la leyenda; consulta Barras o Líneas para compararlos."}</p>}
      <ul className="dashboard-leyenda">
        {barras.map((barra, indice) => (
          <li key={barra.clave}>
            <span className="dashboard-leyenda-color" aria-hidden="true" style={{ background: sectores[indice]?.color }} />
            <span>{barra.etiqueta}</span><strong>{barra.texto}</strong>
            {valido && total > 0 && <span>{(sectores[indice]?.porcentaje ?? 0).toLocaleString("es-PE", { maximumFractionDigits: 1 })}%</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Lineas({ barras, titulo }: { barras: Barra[]; titulo: string }) {
  const ancho = Math.max(520, barras.length * 90 + 100);
  const valores = barras.map((barra) => Number.isFinite(barra.valor) ? barra.valor : 0);
  const minimo = Math.min(0, ...valores);
  const maximoDatos = Math.max(0, ...valores);
  const maximo = maximoDatos === minimo ? minimo + 1 : maximoDatos;
  const rango = maximo - minimo || 1;
  const x = (indice: number) => barras.length === 1 ? (ancho + 60) / 2 : 90 + indice * (ancho - 120) / (barras.length - 1);
  const y = (valor: number) => 18 + (maximo - valor) / rango * 170;
  return (
    <div role="group" aria-label={titulo}>
      <div className="dashboard-lineas-scroll">
        <svg className="dashboard-lineas" width={ancho} height="240" viewBox={`0 0 ${ancho} 240`}
          role="img" aria-label={`${titulo} · líneas`}>
          <title>{`${titulo}: comparación según el orden actual de los grupos`}</title>
          {[0, .5, 1].map((fraccion) => {
            const valor = minimo + rango * fraccion;
            return <g key={fraccion}>
              <line x1="90" x2={ancho - 30} y1={y(valor)} y2={y(valor)} className="dashboard-lineas-guia" />
              <text x="80" y={y(valor) + 4} textAnchor="end">{valor.toLocaleString("es-PE", { maximumFractionDigits: 2 })}</text>
            </g>;
          })}
          <polyline points={valores.map((valor, indice) => `${x(indice)},${y(valor)}`).join(" ")}
            className="dashboard-lineas-trazo" />
          {barras.map((barra, indice) => (
            <g key={barra.clave}>
              <circle cx={x(indice)} cy={y(valores[indice] ?? 0)} r="4" className="dashboard-lineas-punto">
                <title>{`${barra.etiqueta}: ${barra.texto}`}</title>
              </circle>
              <text x={x(indice)} y="213" textAnchor="middle">{barra.etiqueta.length > 13 ? `${barra.etiqueta.slice(0, 12)}…` : barra.etiqueta}</text>
            </g>
          ))}
        </svg>
      </div>
      <ul className="dashboard-leyenda">
        {barras.map((barra) => <li key={barra.clave}><span>{barra.etiqueta}</span><strong>{barra.texto}</strong></li>)}
      </ul>
    </div>
  );
}

function Grafico({ barras, titulo, vista }: { barras: Barra[]; titulo: string; vista: VistaGrafico }) {
  if (barras.length === 0) return <p>Sin datos para los filtros seleccionados.</p>;
  if (vista === "circular") return <Circular barras={barras} titulo={titulo} />;
  if (vista === "lineas") return <Lineas barras={barras} titulo={titulo} />;
  return <Barras barras={barras} titulo={titulo} />;
}

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

export function GraficoVistaOrdenada({ filas, agrupacion, vista = "barras" }: {
  filas: DashboardDesgloseFila[];
  agrupacion: AgrupacionDashboard;
  vista?: VistaGrafico;
}) {
  return (
    <section className="dashboard-grafico" aria-label="Gráfico de vista ordenada">
      <h3>Vista ordenada · expedientes</h3>
      <p className="dashboard-grafico-ayuda">Cantidades según la agrupación, el orden y los filtros seleccionados.</p>
      <Grafico vista={vista} titulo="Expedientes por grupo" barras={filas.map((fila) => ({
        clave: fila.clave,
        etiqueta: etiquetaFilaDashboard(fila, agrupacion),
        valor: fila.expedientes,
        texto: fila.expedientes.toLocaleString("es-PE"),
      }))} />
    </section>
  );
}

export function GraficoMontos({ montos, vista = "barras" }: { montos: DashboardResumen["montos"]; vista?: VistaGrafico }) {
  return (
    <section className="dashboard-grafico" aria-label="Gráfico de montos">
      <h3>Montos</h3>
      <p className="dashboard-grafico-ayuda">Escala independiente por moneda. Bancarización y retención son clasificaciones del mismo total; no se suman entre sí.</p>
      {montos.length === 0 && <p>Sin datos para los filtros seleccionados.</p>}
      {montos.map((monto) => (
        <div className="dashboard-grafico-moneda" key={monto.moneda}>
          <h4>{monto.moneda}</h4>
          {(() => {
            const barras = [
              { clave: "bancarizable", etiqueta: "Bancarizable", valor: Number(monto.bancarizable) },
              { clave: "no_bancarizable", etiqueta: "No bancarizable", valor: Number(monto.no_bancarizable) },
              { clave: "con_agente", etiqueta: "Con agente de retención", valor: Number(monto.con_agente_retencion) },
              { clave: "sin_agente", etiqueta: "Sin agente de retención", valor: Number(monto.sin_agente_retencion) },
            ].map((barra) => ({ ...barra, texto: formatearMonto(monto.moneda, barra.valor) }));
            return vista === "circular" ? <div className="dashboard-circulares-montos">
              <section><h5>Bancarización</h5><Grafico vista={vista} titulo={`Bancarización en ${monto.moneda}`} barras={barras.slice(0, 2)} /></section>
              <section><h5>Retención</h5><Grafico vista={vista} titulo={`Retención en ${monto.moneda}`} barras={barras.slice(2)} /></section>
            </div> : <Grafico vista={vista} titulo={`Montos en ${monto.moneda}`} barras={barras} />;
          })()}
        </div>
      ))}
    </section>
  );
}
