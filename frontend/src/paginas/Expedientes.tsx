import { Link, useSearchParams } from "react-router-dom";

import { conParametros, useDatos } from "../api";
import { Estado, Paginacion, Semaforo } from "../componentes";
import { ETIQUETA_ESTADO, formatearFecha, formatearMonto, numeroExpediente } from "../formato";
import { ESTADOS_EXPEDIENTE, type Expediente } from "../tipos";

const POR_PAGINA = 50;

export default function Expedientes() {
  const [parametros, setParametros] = useSearchParams();
  const estado = parametros.get("estado") ?? "";
  const pendiente = parametros.get("pendiente_aprobacion") ?? "";
  const receptor = parametros.get("receptor_ruc") ?? "";
  const buscar = parametros.get("buscar") ?? "";
  const pagina = Number(parametros.get("pagina") ?? "0");

  const ruta = conParametros("/api/v1/expedientes", {
    estado,
    pendiente_aprobacion: pendiente,
    receptor_ruc: receptor.length === 11 ? receptor : undefined,
    buscar: buscar.trim(),
    limit: String(POR_PAGINA),
    offset: String(pagina * POR_PAGINA),
  });
  const { datos, error, cargando } = useDatos<Expediente[]>(ruta);

  const cambiar = (clave: string, valor: string) => {
    const siguiente = new URLSearchParams(parametros);
    if (valor) siguiente.set(clave, valor);
    else siguiente.delete(clave);
    if (clave !== "pagina") siguiente.delete("pagina");
    setParametros(siguiente);
  };

  return (
    <>
      <h2>Expedientes</h2>
      <div className="filtros">
        <input
          placeholder="Buscar F001-123, RHE-E001-15, RUC o proveedor"
          value={buscar}
          maxLength={100}
          onChange={(e) => cambiar("buscar", e.target.value)}
        />
        <select value={estado} onChange={(e) => cambiar("estado", e.target.value)}>
          <option value="">Todos los estados</option>
          {ESTADOS_EXPEDIENTE.map((e) => (
            <option key={e} value={e}>
              {ETIQUETA_ESTADO[e]}
            </option>
          ))}
        </select>
        <select value={pendiente} onChange={(e) => cambiar("pendiente_aprobacion", e.target.value)}>
          <option value="">Aprobación: todos</option>
          <option value="true">Pendientes de aprobación</option>
          <option value="false">Receptor autorizado</option>
        </select>
        <input
          placeholder="RUC receptor (11 dígitos)"
          value={receptor}
          maxLength={11}
          onChange={(e) => cambiar("receptor_ruc", e.target.value.replace(/\D/g, ""))}
        />
      </div>
      <Estado cargando={cargando} error={error} vacio={datos?.length === 0}>
        <table>
          <thead>
            <tr>
              <th>Estado</th>
              <th>Comprobante</th>
              <th>Emisión</th>
              <th>Emisor</th>
              <th>Receptor</th>
              <th className="num">Importe</th>
            </tr>
          </thead>
          <tbody>
            {datos?.map((e) => (
              <tr key={e.id}>
                <td>
                  <Semaforo estado={e.estado} />
                </td>
                <td>
                  <Link to={`/expedientes/${e.id}`}>
                    {e.tipo_comprobante === "RHE"
                      ? numeroExpediente(e.tipo_comprobante, e.serie, e.correlativo)
                      : "FACT " + numeroExpediente(e.tipo_comprobante, e.serie, e.correlativo)}
                  </Link>
                </td>
                <td>{formatearFecha(e.fecha_emision)}</td>
                <td>{e.emisor.razon_social}</td>
                <td>
                  {e.receptor.razon_social}
                  {e.pendiente_aprobacion && <span className="etiqueta">No autorizado</span>}
                </td>
                <td className="num">{formatearMonto(e.moneda, e.importe_total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Estado>
      <Paginacion
        pagina={pagina}
        hayMas={(datos?.length ?? 0) === POR_PAGINA}
        alCambiar={(p) => cambiar("pagina", String(p))}
      />
    </>
  );
}
