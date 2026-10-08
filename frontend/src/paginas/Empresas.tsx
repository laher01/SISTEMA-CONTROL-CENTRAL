import { useState } from "react";

import { enviarJson, useDatos } from "../api";
import { Estado } from "../componentes";
import type { Empresa } from "../tipos";

type Campo = "autorizada" | "agente_retencion";

export default function Empresas() {
  const { datos, error, cargando, recargar } = useDatos<Empresa[]>("/api/v1/empresas");
  const [errorCambio, setErrorCambio] = useState("");
  const [editandoId, setEditandoId] = useState<string | null>(null);
  const [rucEditado, setRucEditado] = useState("");
  const [razonEditada, setRazonEditada] = useState("");

  const cambiar = async (empresa: Empresa, campo: Campo, valor: boolean) => {
    setErrorCambio("");
    try {
      await enviarJson(`/api/v1/empresas/${empresa.id}`, "PATCH", { [campo]: valor });
      recargar();
    } catch (e) {
      setErrorCambio(e instanceof Error ? e.message : String(e));
    }
  };

  const iniciarEdicion = (empresa: Empresa) => {
    setEditandoId(empresa.id);
    setRucEditado(empresa.ruc);
    setRazonEditada(empresa.razon_social);
    setErrorCambio("");
  };

  const cancelarEdicion = () => {
    setEditandoId(null);
    setRucEditado("");
    setRazonEditada("");
  };

  const guardarEdicion = async (empresa: Empresa) => {
    setErrorCambio("");
    const ruc = rucEditado.trim();
    const razon = razonEditada.trim();

    if (!/^\d{11}$/.test(ruc)) {
      setErrorCambio("El RUC debe tener exactamente 11 dígitos.");
      return;
    }
    if (!razon) {
      setErrorCambio("La razón social no puede quedar vacía.");
      return;
    }

    try {
      await enviarJson<Empresa>(`/api/v1/empresas/${empresa.id}`, "PATCH", {
        ruc,
        razon_social: razon,
      });
      cancelarEdicion();
      recargar();
    } catch (e) {
      setErrorCambio(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <>
      <h2>Empresas</h2>
      <p className="tenue">
        Se crean automáticamente al procesar comprobantes. Si una extracción viene incorrecta,
        puedes corregir manualmente el RUC o la razón social desde <strong>Editar</strong>.
      </p>
      {errorCambio && <p className="error">{errorCambio}</p>}
      <Estado cargando={cargando} error={error} vacio={datos?.length === 0}>
        <table>
          <thead>
            <tr>
              <th>RUC</th>
              <th>Razón social</th>
              <th>Editar</th>
              <th>Autorizada</th>
              <th>Agente de retención</th>
            </tr>
          </thead>
          <tbody>
            {datos?.map((empresa) => {
              const editando = editandoId === empresa.id;
              return (
                <tr key={empresa.id}>
                  <td>
                    {editando ? (
                      <input
                        value={rucEditado}
                        onChange={(ev) => setRucEditado(ev.target.value.replace(/\D/g, ""))}
                        maxLength={11}
                        inputMode="numeric"
                        aria-label={`Editar RUC ${empresa.ruc}`}
                      />
                    ) : (
                      empresa.ruc
                    )}
                  </td>
                  <td>
                    {editando ? (
                      <input
                        value={razonEditada}
                        onChange={(ev) => setRazonEditada(ev.target.value)}
                        maxLength={300}
                        aria-label={`Editar razón social ${empresa.ruc}`}
                      />
                    ) : (
                      empresa.razon_social
                    )}
                  </td>
                  <td>
                    {editando ? (
                      <div className="acciones">
                        <button onClick={() => void guardarEdicion(empresa)}>Guardar</button>
                        <button onClick={cancelarEdicion}>Cancelar</button>
                      </div>
                    ) : (
                      <button onClick={() => iniciarEdicion(empresa)}>Editar</button>
                    )}
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      aria-label={`Autorizada ${empresa.ruc}`}
                      checked={empresa.autorizada}
                      onChange={(ev) => cambiar(empresa, "autorizada", ev.target.checked)}
                    />
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      aria-label={`Agente de retención ${empresa.ruc}`}
                      checked={empresa.agente_retencion}
                      onChange={(ev) => cambiar(empresa, "agente_retencion", ev.target.checked)}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Estado>
    </>
  );
}
