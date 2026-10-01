import { useState } from "react";

import { enviarJson, useDatos } from "../api";
import { Estado } from "../componentes";
import type { Empresa } from "../tipos";

type Campo = "autorizada" | "agente_retencion";

export default function Empresas() {
  const { datos, error, cargando, recargar } = useDatos<Empresa[]>("/api/v1/empresas");
  const [errorCambio, setErrorCambio] = useState("");

  const cambiar = async (empresa: Empresa, campo: Campo, valor: boolean) => {
    setErrorCambio("");
    try {
      await enviarJson(`/api/v1/empresas/${empresa.id}`, "PATCH", { [campo]: valor });
      recargar();
    } catch (e) {
      setErrorCambio(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <>
      <h2>Empresas</h2>
      <p className="tenue">
        Se crean solas al subir XML. Marca como <strong>autorizadas</strong> las empresas del grupo
        que pueden recibir comprobantes y como <strong>agente de retención</strong> las que lo son;
        los expedientes se recalculan al guardar.
      </p>
      {errorCambio && <p className="error">{errorCambio}</p>}
      <Estado cargando={cargando} error={error} vacio={datos?.length === 0}>
        <table>
          <thead>
            <tr>
              <th>RUC</th>
              <th>Razón social</th>
              <th>Autorizada</th>
              <th>Agente de retención</th>
            </tr>
          </thead>
          <tbody>
            {datos?.map((e) => (
              <tr key={e.id}>
                <td>{e.ruc}</td>
                <td>{e.razon_social}</td>
                <td>
                  <input
                    type="checkbox"
                    aria-label={`Autorizada ${e.ruc}`}
                    checked={e.autorizada}
                    onChange={(ev) => cambiar(e, "autorizada", ev.target.checked)}
                  />
                </td>
                <td>
                  <input
                    type="checkbox"
                    aria-label={`Agente de retención ${e.ruc}`}
                    checked={e.agente_retencion}
                    onChange={(ev) => cambiar(e, "agente_retencion", ev.target.checked)}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Estado>
    </>
  );
}
