import { useState } from "react";

import { enviarJson, useDatos } from "../api";
import { Estado } from "../componentes";
import type {
  ClasificacionProveedor,
  Empresa,
  TipoRelacionEmpresa,
} from "../tipos";

type Campo = "autorizada" | "agente_retencion";

const ETIQUETA_RELACION: Record<TipoRelacionEmpresa, string> = {
  PROVEEDOR: "Proveedor",
  CLIENTE: "Cliente",
  AMBOS: "Proveedor y cliente",
  SIN_CLASIFICAR: "Sin clasificar",
};

export default function Empresas() {
  const { datos, error, cargando, recargar } = useDatos<Empresa[]>("/api/v1/empresas");
  const [errorCambio, setErrorCambio] = useState("");
  const [editandoId, setEditandoId] = useState<string | null>(null);
  const [rucEditado, setRucEditado] = useState("");
  const [razonEditada, setRazonEditada] = useState("");
  const [relacionEditada, setRelacionEditada] =
    useState<TipoRelacionEmpresa>("SIN_CLASIFICAR");
  const [clasificacionEditada, setClasificacionEditada] =
    useState<ClasificacionProveedor | "">("");

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
    setRelacionEditada(empresa.tipo_relacion);
    setClasificacionEditada(empresa.clasificacion_proveedor ?? "");
    setErrorCambio("");
  };

  const cancelarEdicion = () => {
    setEditandoId(null);
    setRucEditado("");
    setRazonEditada("");
    setRelacionEditada("SIN_CLASIFICAR");
    setClasificacionEditada("");
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

    const proveedor =
      relacionEditada === "PROVEEDOR" || relacionEditada === "AMBOS";

    try {
      await enviarJson<Empresa>(`/api/v1/empresas/${empresa.id}`, "PATCH", {
        ruc,
        razon_social: razon,
        tipo_relacion: relacionEditada,
        clasificacion_proveedor: proveedor ? clasificacionEditada || null : null,
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
        El sistema clasifica automáticamente al emisor como proveedor y al receptor como cliente.
        Si un mismo RUC aparece en ambos lados se identifica como proveedor y cliente. La
        clasificación Tipo A / Tipo B aplica únicamente a proveedores.
      </p>
      {errorCambio && <p className="error">{errorCambio}</p>}
      <Estado cargando={cargando} error={error} vacio={datos?.length === 0}>
        <table>
          <thead>
            <tr>
              <th>Relación</th>
              <th>RUC</th>
              <th>Razón social</th>
              <th>Usuario</th>
              <th>Tipo proveedor</th>
              <th>Editar</th>
              <th>Autorizada</th>
              <th>Agente de retención</th>
            </tr>
          </thead>
          <tbody>
            {datos?.map((empresa) => {
              const editando = editandoId === empresa.id;
              const proveedor =
                (editando ? relacionEditada : empresa.tipo_relacion) === "PROVEEDOR" ||
                (editando ? relacionEditada : empresa.tipo_relacion) === "AMBOS";
              return (
                <tr key={empresa.id}>
                  <td>
                    {editando ? (
                      <select
                        value={relacionEditada}
                        onChange={(ev) => {
                          const valor = ev.target.value as TipoRelacionEmpresa;
                          setRelacionEditada(valor);
                          if (valor === "CLIENTE" || valor === "SIN_CLASIFICAR") {
                            setClasificacionEditada("");
                          }
                        }}
                      >
                        <option value="PROVEEDOR">Proveedor</option>
                        <option value="CLIENTE">Cliente</option>
                        <option value="AMBOS">Proveedor y cliente</option>
                        <option value="SIN_CLASIFICAR">Sin clasificar</option>
                      </select>
                    ) : (
                      ETIQUETA_RELACION[empresa.tipo_relacion]
                    )}
                  </td>
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
                    {(empresa.usuarios ?? []).length > 0
                      ? (empresa.usuarios ?? [])
                          .map((usuario) => `${usuario.codigo} · ${usuario.nombre}`)
                          .join(", ")
                      : "—"}
                  </td>
                  <td>
                    {editando ? (
                      <select
                        value={clasificacionEditada}
                        disabled={!proveedor}
                        onChange={(ev) =>
                          setClasificacionEditada(
                            ev.target.value as ClasificacionProveedor | "",
                          )
                        }
                      >
                        <option value="">Sin tipo</option>
                        <option value="A">Tipo A</option>
                        <option value="B">Tipo B</option>
                      </select>
                    ) : proveedor ? (
                      empresa.clasificacion_proveedor
                        ? `Tipo ${empresa.clasificacion_proveedor}`
                        : "Sin tipo"
                    ) : (
                      "—"
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
