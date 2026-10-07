import { useDatos } from "../api";
import { Estado } from "../componentes";
import { formatearMonto } from "../formato";
import type { ComprasProveedorFila, ProduccionResumen } from "../tipos";

export default function Produccion() {
  const { datos, error, cargando } = useDatos<ProduccionResumen>("/api/v1/produccion/resumen");
  const { datos: compras } = useDatos<ComprasProveedorFila[]>("/api/v1/produccion/compras");

  return (
    <>
      <h2>Producción por usuario y gestor</h2>
      <p className="tenue">
        Acumulado de expedientes por Usuario, Gestor y moneda para controlar el origen
        de la información y el volumen de compras.
      </p>
      <Estado cargando={cargando} error={error} vacio={datos?.filas.length === 0}>
        <table>
          <thead>
            <tr>
              <th>Usuario</th>
              <th>Gestor</th>
              <th>Moneda</th>
              <th className="num">Expedientes</th>
              <th className="num">Importe total</th>
            </tr>
          </thead>
          <tbody>
            {datos?.filas.map((fila) => (
              <tr key={(fila.usuario_id ?? "sin") + "-" + (fila.gestor_id ?? "sin") + "-" + fila.moneda}>
                <td>{fila.usuario_codigo} · {fila.usuario_nombre}</td>
                <td>{fila.gestor_codigo} · {fila.gestor_nombre}</td>
                <td>{fila.moneda}</td>
                <td className="num">{fila.expedientes}</td>
                <td className="num">{formatearMonto(fila.moneda, fila.importe_total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Estado>

      <h3>Compras por proveedor y receptor</h3>
      <table>
        <thead>
          <tr>
            <th>Usuario</th>
            <th>Gestor</th>
            <th>Proveedor emisor</th>
            <th>Empresa receptora</th>
            <th>Moneda</th>
            <th className="num">Expedientes</th>
            <th className="num">Importe</th>
          </tr>
        </thead>
        <tbody>
          {compras?.map((fila, indice) => (
            <tr key={fila.emisor_ruc + "-" + fila.receptor_ruc + "-" + fila.gestor_codigo + "-" + fila.moneda + "-" + indice}>
              <td>{fila.usuario_codigo}</td>
              <td>{fila.gestor_codigo}</td>
              <td>{fila.emisor_razon_social} ({fila.emisor_ruc})</td>
              <td>{fila.receptor_razon_social} ({fila.receptor_ruc})</td>
              <td>{fila.moneda}</td>
              <td className="num">{fila.expedientes}</td>
              <td className="num">{formatearMonto(fila.moneda, fila.importe_total)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
