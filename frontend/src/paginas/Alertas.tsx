import { Link, useSearchParams } from "react-router-dom";

import { conParametros, useDatos } from "../api";
import { Estado } from "../componentes";
import { ETIQUETA_ALERTA, formatearFecha } from "../formato";
import { TIPOS_ALERTA, type Alerta } from "../tipos";

export default function Alertas() {
  const [parametros, setParametros] = useSearchParams();
  const tipo = parametros.get("tipo") ?? "";
  const resuelta = parametros.get("resuelta") ?? "false";
  const { datos, error, cargando } = useDatos<Alerta[]>(
    conParametros("/api/v1/alertas", { tipo, resuelta, limit: "500" }),
  );

  const cambiar = (clave: string, valor: string) => {
    const siguiente = new URLSearchParams(parametros);
    if (valor) siguiente.set(clave, valor);
    else siguiente.delete(clave);
    setParametros(siguiente);
  };

  return (
    <>
      <h2>Alertas</h2>
      <div className="filtros">
        <select value={tipo} onChange={(e) => cambiar("tipo", e.target.value)}>
          <option value="">Todos los tipos</option>
          {TIPOS_ALERTA.map((t) => (
            <option key={t} value={t}>
              {ETIQUETA_ALERTA[t]}
            </option>
          ))}
        </select>
        <select value={resuelta} onChange={(e) => cambiar("resuelta", e.target.value)}>
          <option value="false">Abiertas</option>
          <option value="true">Resueltas</option>
        </select>
      </div>
      <Estado cargando={cargando} error={error} vacio={datos?.length === 0}>
        <table>
          <thead>
            <tr>
              <th>Tipo</th>
              <th>Detalle</th>
              <th>Desde</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {datos?.map((a) => (
              <tr key={a.id}>
                <td>{ETIQUETA_ALERTA[a.tipo]}</td>
                <td>{a.mensaje}</td>
                <td>{formatearFecha(a.created_at)}</td>
                <td>
                  <Link to={`/expedientes/${a.expediente_id}`}>Ver expediente</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Estado>
    </>
  );
}
