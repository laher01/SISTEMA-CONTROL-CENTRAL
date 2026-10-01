import type { ReactNode } from "react";

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
  alCambiar,
}: {
  pagina: number;
  hayMas: boolean;
  alCambiar: (pagina: number) => void;
}) {
  if (pagina === 0 && !hayMas) return null;
  return (
    <div className="paginacion">
      <button disabled={pagina === 0} onClick={() => alCambiar(pagina - 1)}>
        Anterior
      </button>
      <span>Página {pagina + 1}</span>
      <button disabled={!hayMas} onClick={() => alCambiar(pagina + 1)}>
        Siguiente
      </button>
    </div>
  );
}
