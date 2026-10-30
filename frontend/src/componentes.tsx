import { useEffect, type ReactNode } from "react";

import { ETIQUETA_ESTADO } from "./formato";
import type { EstadoExpediente } from "./tipos";

export function Semaforo({ estado }: { estado: EstadoExpediente }) {
  return <span className={`semaforo semaforo-${estado.toLowerCase()}`}>{ETIQUETA_ESTADO[estado]}</span>;
}

export function Estado({
  cargando,
  error,
  vacio,
  children,
}: {
  cargando: boolean;
  error?: string;
  vacio?: boolean;
  children: ReactNode;
}) {
  if (error) return <p className="error">No se pudo cargar: {error}</p>;
  if (cargando && vacio !== false) return <p className="tenue">Cargando…</p>;
  if (vacio) return <p className="tenue">No hay registros.</p>;
  return <>{children}</>;
}

export function Paginacion({
  pagina,
  hayMas,
  total,
  porPagina,
  alCambiar,
}: {
  pagina: number;
  hayMas: boolean;
  total?: number;
  porPagina?: number;
  alCambiar: (pagina: number) => void;
}) {
  const paginasTotales = total !== undefined && porPagina
    ? Math.ceil(total / porPagina)
    : undefined;
  const ultimaPagina = paginasTotales === undefined ? undefined : paginasTotales - 1;

  useEffect(() => {
    if (ultimaPagina !== undefined && pagina > ultimaPagina) {
      alCambiar(Math.max(0, ultimaPagina));
    }
  }, [alCambiar, pagina, ultimaPagina]);

  if (paginasTotales === 0 || (paginasTotales === undefined && pagina === 0 && !hayMas)) return null;

  if (paginasTotales !== undefined) {
    const paginas = obtenerPaginasVisibles(pagina, paginasTotales);
    return (
      <nav className="paginacion" aria-label="Paginación de resultados">
        <button disabled={pagina <= 0} onClick={() => alCambiar(pagina - 1)}>
          Anterior
        </button>
        {paginas.map((item, indice) => item === "…" ? (
          <span className="paginacion-ellipsis" key={`ellipsis-${indice}`} aria-hidden="true">…</span>
        ) : (
          <button
            key={item}
            type="button"
            className={item - 1 === pagina ? "activa" : undefined}
            aria-current={item - 1 === pagina ? "page" : undefined}
            aria-label={`Ir a la página ${item}`}
            onClick={() => alCambiar(item - 1)}
          >
            {item}
          </button>
        ))}
        <span aria-live="polite">Página {Math.min(pagina + 1, paginasTotales)} de {paginasTotales}</span>
        <button disabled={ultimaPagina === undefined || pagina >= ultimaPagina} onClick={() => alCambiar(pagina + 1)}>
          Siguiente
        </button>
      </nav>
    );
  }

  return (
    <nav className="paginacion" aria-label="Paginación de resultados">
      <button disabled={pagina === 0} onClick={() => alCambiar(pagina - 1)}>
        Anterior
      </button>
      <span>Página {pagina + 1}</span>
      <button disabled={!hayMas} onClick={() => alCambiar(pagina + 1)}>
        Siguiente
      </button>
    </nav>
  );
}

export function obtenerPaginasVisibles(pagina: number, totalPaginas: number): (number | "…")[] {
  if (totalPaginas <= 0) return [];
  if (totalPaginas <= 9) return Array.from({ length: totalPaginas }, (_, indice) => indice + 1);

  const actual = Math.min(Math.max(pagina + 1, 1), totalPaginas);
  const inicio = Math.max(2, actual - 2);
  const fin = Math.min(totalPaginas - 1, actual + 2);
  const paginas: (number | "…")[] = [1];
  if (inicio > 2) paginas.push("…");
  for (let numero = inicio; numero <= fin; numero += 1) paginas.push(numero);
  if (fin < totalPaginas - 1) paginas.push("…");
  paginas.push(totalPaginas);
  return paginas;
}
