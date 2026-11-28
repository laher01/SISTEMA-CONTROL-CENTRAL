import "./CeldaCpe.css";

export default function CeldaCpe({ estado }: { estado?: string | null }) {
  if (estado === "VALIDO") {
    return <td className="cpe-celda"><span role="img" aria-label="CPE válido" title="CPE válido">✓</span></td>;
  }
  if (estado === "INVALIDO") {
    return <td className="cpe-celda"><span role="img" aria-label="CPE no válido" title="CPE no válido">X</span></td>;
  }
  return <td className="cpe-celda">{estado === "PENDIENTE" ? "Pendiente" : "—"}</td>;
}
