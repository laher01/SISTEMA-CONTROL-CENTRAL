import { useState } from "react";

import { conParametros, useDatos } from "../api";
import { formatearMonto } from "../formato";

interface FilaSecretaria {
  receptor_ruc: string;
  receptor: string;
  moneda: "PEN" | "USD";
  expedientes: number;
  total: string;
}

export default function Secretaria() {
  const [desde, setDesde] = useState("2026-10-01");
  const [hasta, setHasta] = useState("2026-10-31");
  const ruta = conParametros("/api/v1/dashboard/secretaria-clientes", { desde, hasta });
  const { datos, cargando, error } = useDatos<FilaSecretaria[]>(ruta);

  return (
    <>
      <h2>Control documental por Cliente/Receptor</h2>
      <p className="tenue">
        Vista transversal de Secretaría de expedientes registrados por cada Cliente.
        Los importes no constituyen crédito fiscal validado.
      </p>
      <div className="filtros">
        <label>Desde <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} /></label>
        <label>Hasta <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} /></label>
      </div>
      {cargando && <p>Cargando datos…</p>}
      {error && <p role="alert">{error}</p>}
      <table>
        <thead><tr><th>RUC</th><th>Cliente/Receptor</th><th>Moneda</th><th>Expedientes</th><th>Total registrado</th></tr></thead>
        <tbody>
          {(datos ?? []).map((fila) => (
            <tr key={fila.receptor_ruc + fila.moneda}>
              <td>{fila.receptor_ruc}</td>
              <td>{fila.receptor}</td>
              <td>{fila.moneda}</td>
              <td>{fila.expedientes}</td>
              <td>{formatearMonto(fila.moneda, fila.total)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
