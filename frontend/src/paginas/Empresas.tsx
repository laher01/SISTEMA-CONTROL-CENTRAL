import { useState } from "react";

import { enviarJson, useDatos } from "../api";
import { Estado } from "../componentes";
import type {
  ClasificacionProveedor,
  Empresa,
  TipoRelacionEmpresa,
} from "../tipos";

type Campo = "autorizada" | "agente_retencion";
type PestanaEmpresa = "PROVEEDORES" | "CLIENTES";

export default function Empresas() {
  const { datos, error, cargando, recargar } = useDatos<Empresa[]>("/api/v1/empresas");
  const [pestana, setPestana] = useState<PestanaEmpresa>("PROVEEDORES");
  const [errorCambio, setErrorCambio] = useState("");
  const [editandoId, setEditandoId] = useState<string | null>(null);
  const [rucEditado, setRucEditado] = useState("");
  const [razonEditada, setRazonEditada] = useState("");
  const [relacionEditada, setRelacionEditada] =
    useState<TipoRelacionEmpresa>("SIN_CLASIFICAR");
  const [clasificacionEditada, setClasificacionEditada] =
    useState<ClasificacionProveedor | "">("");

  const proveedores =
    datos?.filter(
      (empresa) =>
        empresa.tipo_relacion === "PROVEEDOR" || empresa.tipo_relacion === "AMBOS",
    ) ?? [];
  const clientes =
    datos?.filter(
      (empresa) => empresa.tipo_relacion === "CLIENTE" || empresa.tipo_relacion === "AMBOS",
    ) ?? [];
  const sinClasificar =
    datos?.filter((empresa) => empresa.tipo_relacion === "SIN_CLASIFICAR") ?? [];
  const empresasVisibles = pestana === "PROVEEDORES" ? proveedores : clientes;
  const esProveedor = pestana === "PROVEEDORES";

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

  const usuariosEmpresa = (empresa: Empresa) =>
    (empresa.usuarios ?? []).length > 0
      ? (empresa.usuarios ?? [])
          .map((usuario) => `${usuario.codigo} · ${usuario.nombre}`)
          .join(", ")
      : "—";

  return (
    <>
      <h2>Empresas</h2>
      <p className="tenue">
        Proveedores y clientes se administran por separado. Si un mismo RUC cumple ambos roles,
        aparecerá en las dos pestañas. La clasificación Tipo A / Tipo B aplica únicamente a
        proveedores.
      </p>

      <div className="acciones">
        <button
          className={pestana === "PROVEEDORES" ? "activo" : undefined}
          onClick={() => {
            setPestana("PROVEEDORES");
            cancelarEdicion();
          }}
        >
          Proveedores ({proveedores.length})
        </button>
        <button
          className={pestana === "CLIENTES" ? "activo" : undefined}
          onClick={() => {
            setPestana("CLIENTES");
            cancelarEdicion();
          }}
        >
          Clientes ({clientes.length})
        </button>
      </div>

      {sinClasificar.length > 0 && (
        <p className="tenue">
          Hay {sinClasificar.length} empresa(s) sin clasificar. Puedes asignarles su relación desde
          Editar cuando aparezcan vinculadas a un documento.
        </p>
      )}

      {errorCambio && <p className="error">{errorCambio}</p>}

      <Estado cargando={cargando} error={error} vacio={empresasVisibles.length === 0}>
        <table>
          <thead>
            <tr>
              <th>RUC</th>
              <th>Razón social</th>
              <th>Usuario</th>
              {esProveedor && <th>Tipo proveedor</th>}
              <th>Editar</th>
              <th>Autorizada</th>
              <th>Agente de retención</th>
            </tr>
          </thead>
          <tbody>
            {empresasVisibles.map((empresa) => {
              const editando = editandoId === empresa.id;
              const proveedorActual =
                (editando ? relacionEditada : empresa.tipo_relacion) === "PROVEEDOR" ||
                (editando ? relacionEditada : empresa.tipo_relacion) === "AMBOS";

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
                      <>
                        {empresa.razon_social}
                        {empresa.tipo_relacion === "AMBOS" && (
                          <span className="etiqueta">Proveedor y cliente</span>
                        )}
                      </>
                    )}
                  </td>
                  <td>{usuariosEmpresa(empresa)}</td>

                  {esProveedor && (
                    <td>
                      {editando ? (
                        <select
                          value={clasificacionEditada}
                          disabled={!proveedorActual}
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
                      ) : empresa.clasificacion_proveedor ? (
                        `Tipo ${empresa.clasificacion_proveedor}`
                      ) : (
                        "Sin tipo"
                      )}
                    </td>
                  )}

                  <td>
                    {editando ? (
                      <div className="acciones">
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
