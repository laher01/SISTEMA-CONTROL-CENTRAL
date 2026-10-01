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
