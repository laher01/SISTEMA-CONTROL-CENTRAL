import type { ReactNode } from "react";

export function parametrosOrden(orden: string) {
  return {
    orden: orden.replace(/^-/, ""),
    direccion: orden.startsWith("-") ? "desc" : "asc",
  };
}

export default function EncabezadoOrden({
  campo, orden, cambiar, children, className,
}: {
  campo: string;
  orden: string;
  cambiar: (clave: string, valor: string) => void;
  children: ReactNode;
  className?: string;
}) {
  const sentido = orden === campo ? "ascending" : orden === `-${campo}` ? "descending" : "none";
  return (
    <th aria-sort={sentido} className={className}>
      <button
        type="button"
        className="encabezado-orden"
        onClick={() => cambiar("orden", sentido === "ascending" ? `-${campo}` : campo)}
      >
        {children} <span aria-hidden="true">{sentido === "ascending" ? "↑" : sentido === "descending" ? "↓" : "↕"}</span>
      </button>
    </th>
  );
}
