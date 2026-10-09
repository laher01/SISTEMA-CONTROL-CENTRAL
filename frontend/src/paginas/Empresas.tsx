import { useState } from "react";
import { useSearchParams } from "react-router-dom";

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
  const [params] = useSearchParams();
  const rucFiltro = params.get("ruc") ?? "";
  const [pestana, setPestana] = useState<PestanaEmpresa | "SIN_CLASIFICAR">(
    params.get("pendientes") === "1" ? "SIN_CLASIFICAR" : "PROVEEDORES",
  );
  const [seleccion, setSeleccion] = useState<string[]>([]);
  const [clasificacionMasiva, setClasificacionMasiva] = useState<"A" | "B">("B");
  const [operando, setOperando] = useState(false);
  const [mensaje, setMensaje] = useState("");
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
  const empresasVisibles = (pestana === "PROVEEDORES" ? proveedores : pestana === "CLIENTES" ? clientes :
    datos?.filter((e) => e.tipo_relacion === "SIN_CLASIFICAR" ||
      ((e.tipo_relacion === "PROVEEDOR" || e.tipo_relacion === "AMBOS") && !e.clasificacion_proveedor)) ?? []
  ).filter((e) => !rucFiltro || e.ruc === rucFiltro);
  const esProveedor = pestana !== "CLIENTES";
  const pendientes = empresasVisibles.filter((e) => e.tipo_relacion === "SIN_CLASIFICAR" ||
    ((e.tipo_relacion === "PROVEEDOR" || e.tipo_relacion === "AMBOS") && !e.clasificacion_proveedor));

  const notificar = async () => {
    if (!seleccion.length) return;
    setOperando(true);
    setErrorCambio("");
    try {
      const respuesta = await enviarJson<{ empresas: number; administradores: number }>(
        "/api/v1/empresas/notificar-clasificacion", "POST", { empresa_ids: seleccion },
      );
      setMensaje(`Aviso enviado: ${respuesta.empresas} empresa(s) a ${respuesta.administradores} administrador(es).`);
    } catch (e) { setErrorCambio(e instanceof Error ? e.message : String(e)); }
    finally { setOperando(false); }
  };

  const actualizarSeleccionadas = async () => {
    if (!seleccion.length) return;
    setOperando(true);
    setErrorCambio("");
    let actualizadas = 0;
    try {
      for (const empresa of pendientes.filter((e) => seleccion.includes(e.id))) {
        await enviarJson(`/api/v1/empresas/${empresa.id}`, "PATCH", {
          tipo_relacion: empresa.tipo_relacion === "SIN_CLASIFICAR" ? "PROVEEDOR" : empresa.tipo_relacion,
          clasificacion_proveedor: clasificacionMasiva,
        });
        actualizadas += 1;
      }
      setMensaje(`${actualizadas} empresa(s) clasificadas; autorización pendiente de revisión individual.`);
      setSeleccion([]);
      recargar();
    } catch (e) { setErrorCambio(`Actualizadas ${actualizadas}; error: ${e instanceof Error ? e.message : String(e)}`); recargar(); }
    finally { setOperando(false); }
  };

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

      <div className="acciones">
        <button type="button" className={pestana === "SIN_CLASIFICAR" ? "activo" : undefined}
          onClick={() => { setPestana("SIN_CLASIFICAR"); setSeleccion([]); cancelarEdicion(); }}>
          Sin clasificar ({(datos ?? []).filter((e) => e.tipo_relacion === "SIN_CLASIFICAR" ||
            ((e.tipo_relacion === "PROVEEDOR" || e.tipo_relacion === "AMBOS") && !e.clasificacion_proveedor)).length})
        </button>
        <button type="button" disabled={!seleccion.length || operando} onClick={() => void notificar()}>
          Notificar inmediatamente a Administrador ({seleccion.length})
        </button>
        {pestana === "SIN_CLASIFICAR" && <>
          <select aria-label="Clasificación a aplicar" value={clasificacionMasiva}
            onChange={(e) => setClasificacionMasiva(e.target.value as "A" | "B")}>
            <option value="A">Tipo A</option><option value="B">Tipo B</option>
          </select>
          <button type="button" disabled={!seleccion.length || operando} onClick={() => void actualizarSeleccionadas()}>
            Actualizar solo seleccionadas ({seleccion.length})
          </button>
        </>}
      </div>
      {mensaje && <p role="status">{mensaje}</p>}
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
              <th><input type="checkbox" aria-label="Seleccionar pendientes visibles"
                checked={pendientes.length > 0 && pendientes.every((e) => seleccion.includes(e.id))}
                onChange={(ev) => setSeleccion(ev.target.checked ? pendientes.map((e) => e.id) : [])}/></th>
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
                  <td><input type="checkbox" aria-label={`Seleccionar ${empresa.ruc}`}
                    disabled={!pendientes.some((e) => e.id === empresa.id)}
                    checked={seleccion.includes(empresa.id)}
                    onChange={(ev) => setSeleccion((prev) => ev.target.checked ? [...prev, empresa.id] : prev.filter((id) => id !== empresa.id))}/></td>
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
                        {!empresa.clasificacion_proveedor && (empresa.tipo_relacion === "PROVEEDOR" || empresa.tipo_relacion === "AMBOS" || empresa.tipo_relacion === "SIN_CLASIFICAR") && <span className="etiqueta">Sin clasificar</span>}
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
