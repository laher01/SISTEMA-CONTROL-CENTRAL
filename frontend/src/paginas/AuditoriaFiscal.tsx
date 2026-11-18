import { useState } from "react";
import { Link } from "react-router-dom";

import { conParametros, useDatos } from "../api";

interface Fila {
  expediente_id: string;
  comprobante: string;
  fecha_emision: string;
  emisor_ruc: string;
  receptor_ruc: string;
  moneda: string;
  estado_documental: string;
  estado_fiscal: string;
}

export default function AuditoriaFiscal() {
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [emisor, setEmisor] = useState("");
  const [receptor, setReceptor] = useState("");
  const [moneda, setMoneda] = useState("");
  const [pagina, setPagina] = useState(0);
  const limite = 50;
  const cambiar = (setter: (valor: string) => void, valor: string) => {
    setter(valor);
    setPagina(0);
  };
  const { datos, cargando, error } = useDatos<{ total: number; filas: Fila[] }>(
    conParametros("/api/v1/registros/auditoria-fiscal", {
      fecha_desde: desde || undefined,
      fecha_hasta: hasta || undefined,
      emisor: emisor || undefined,
      receptor: receptor || undefined,
      moneda: moneda || undefined,
      limit: String(limite),
      offset: String(pagina * limite),
    }),
  );
  return <>
    <h2>Auditoría de crédito fiscal</h2>
    <p>Inventario de facturas registradas para revisión documental y tributaria.
      El registro de una factura no acredita derecho a crédito fiscal.</p>
    <div className="filtros">
      <label>Desde <input type="date" value={desde} onChange={(e) => cambiar(setDesde, e.target.value)} /></label>
      <label>Hasta <input type="date" value={hasta} onChange={(e) => cambiar(setHasta, e.target.value)} /></label>
      <label>Emisor <input value={emisor} maxLength={100} onChange={(e) => cambiar(setEmisor, e.target.value)} /></label>
      <label>Receptor <input value={receptor} maxLength={100} onChange={(e) => cambiar(setReceptor, e.target.value)} /></label>
      <label>Moneda <select value={moneda} onChange={(e) => cambiar(setMoneda, e.target.value)}>
        <option value="">Todas</option><option value="PEN">PEN</option><option value="USD">USD</option>
      </select></label>
    </div>
    {cargando && <p>Cargando facturas…</p>}
    {error && <p role="alert">{error}</p>}
    {!cargando && !error && datos && <>
      <p><strong>{datos.total} facturas pendientes de verificación fiscal</strong></p>
      <p>El crédito fiscal validado no está disponible sin evidencia tributaria independiente.</p>
      <div className="tabla-scroll"><table>
        <thead><tr><th>Factura</th><th>Fecha</th><th>RUC emisor</th><th>RUC receptor</th><th>Moneda</th><th>Estado documental</th><th>Revisión fiscal</th></tr></thead>
        <tbody>{datos.filas.map((fila) => <tr key={fila.expediente_id}>
          <td><Link to={"/expedientes/" + fila.expediente_id}>{fila.comprobante}</Link></td>
          <td>{fila.fecha_emision}</td><td>{fila.emisor_ruc}</td><td>{fila.receptor_ruc}</td>
          <td>{fila.moneda}</td><td>{fila.estado_documental}</td><td>Pendiente de verificación</td>
        </tr>)}</tbody>
      </table></div>
      {!datos.filas.length && <p>No hay facturas para los filtros elegidos.</p>}
      <button type="button" disabled={pagina === 0} onClick={() => setPagina((p) => p - 1)}>Anterior</button>{" "}
      <button type="button" disabled={(pagina + 1) * limite >= datos.total} onClick={() => setPagina((p) => p + 1)}>Siguiente</button>
    </>}
  </>;
}
