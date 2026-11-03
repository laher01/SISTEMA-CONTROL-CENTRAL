import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { enviarJson, useDatos } from "../api";
import { Estado } from "../componentes";
import type {
  ClasificacionProveedor,
  Empresa,
  SesionActual,
} from "../tipos";

type Campo = "autorizada" | "agente_retencion";
type PestanaEmpresa = "PROVEEDORES" | "CLIENTES";
type OrdenEmpresas = "ruc" | "razon_social" | "usuario" | "tipo" | "autorizada";

export function ordenarEmpresas(
  empresas: Empresa[],
  orden: OrdenEmpresas,
  direccion: "asc" | "desc",
): Empresa[] {
  const compararTexto = (a: string, b: string) =>
    a.localeCompare(b, "es", { numeric: true, sensitivity: "base" });
  return [...empresas].sort((a, b) => {
    let comparacion = 0;
    if (orden === "ruc") comparacion = compararTexto(a.ruc, b.ruc);
    if (orden === "razon_social") comparacion = compararTexto(a.razon_social, b.razon_social);
    if (orden === "usuario") comparacion = compararTexto(
      (a.usuarios ?? []).map((u) => `${u.codigo} ${u.nombre}`).join(" "),
      (b.usuarios ?? []).map((u) => `${u.codigo} ${u.nombre}`).join(" "),
    );
    if (orden === "tipo") comparacion = compararTexto(
      a.clasificacion_proveedor ?? "",
      b.clasificacion_proveedor ?? "",
    );
    if (orden === "autorizada") comparacion = Number(a.autorizada) - Number(b.autorizada);
    return (direccion === "asc" ? 1 : -1) * comparacion || compararTexto(a.ruc, b.ruc);
  });
}

export default function Empresas({ sesion }: { sesion: SesionActual }) {
  const puedeClasificar = sesion.rol === "SUPERADMIN" || sesion.rol === "ADMINISTRADOR";
  const puedeAutorizar = puedeClasificar || sesion.rol === "SECRETARIA" || sesion.rol === "RESPONSABLE" || sesion.rol === "GERENTE";
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
  const [editandoRazonId, setEditandoRazonId] = useState<string | null>(null);
  const [razonEditada, setRazonEditada] = useState("");
  const [orden, setOrden] = useState<OrdenEmpresas>("ruc");
  const [direccionOrden, setDireccionOrden] = useState<"asc" | "desc">("asc");

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
  const empresasOrdenadas = useMemo(
    () => ordenarEmpresas(empresasVisibles, orden, direccionOrden),
    [empresasVisibles, orden, direccionOrden],
  );

  const ordenarPor = (campo: OrdenEmpresas) => {
    if (orden === campo) setDireccionOrden((actual) => actual === "asc" ? "desc" : "asc");
    else {
      setOrden(campo);
      setDireccionOrden("asc");
    }
  };

  const encabezadoOrdenable = (texto: string, campo: OrdenEmpresas) => (
    <th aria-sort={orden === campo ? (direccionOrden === "asc" ? "ascending" : "descending") : "none"}>
      <button type="button" className="empresas-ordenar" onClick={() => ordenarPor(campo)}>
        {texto}{orden === campo ? (direccionOrden === "asc" ? " ↑" : " ↓") : " ↕"}
      </button>
    </th>
  );

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
      if (campo === "autorizada") {
        setMensaje(
          valor
            ? "Autorización activada para los expedientes que ingresen desde ahora."
            : "Autorización desactivada para los expedientes que ingresen desde ahora; los expedientes anteriores conservan su estado.",
        );
      }
      recargar();
    } catch (e) {
      setErrorCambio(e instanceof Error ? e.message : String(e));
    }
  };

  const iniciarEdicionRazon = (empresa: Empresa) => {
    setEditandoRazonId(empresa.id);
    setRazonEditada(empresa.razon_social);
    setErrorCambio("");
  };

  const cancelarEdicionRazon = () => {
    setEditandoRazonId(null);
    setRazonEditada("");
  };

  const guardarRazonSocial = async (empresa: Empresa) => {
    setErrorCambio("");
    const razon = razonEditada.trim();

    if (!razon) {
      setErrorCambio("La razón social no puede quedar vacía.");
      return;
    }

    try {
      await enviarJson<Empresa>(`/api/v1/empresas/${empresa.id}`, "PATCH", {
        razon_social: razon,
      });
      cancelarEdicionRazon();
      recargar();
    } catch (e) {
      setErrorCambio(e instanceof Error ? e.message : String(e));
    }
  };

  const clasificarProveedor = async (
    empresa: Empresa,
    clasificacion: ClasificacionProveedor,
  ) => {
    setErrorCambio("");
    try {
      await enviarJson<Empresa>(`/api/v1/empresas/${empresa.id}`, "PATCH", {
        tipo_relacion:
          empresa.tipo_relacion === "SIN_CLASIFICAR"
            ? "PROVEEDOR"
            : empresa.tipo_relacion,
        clasificacion_proveedor: clasificacion,
      });
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
      <p className="tenue">El estado de autorización rige para expedientes nuevos; los anteriores conservan su estado registrado.</p>

      <div className="acciones">
        <button
          className={pestana === "PROVEEDORES" ? "activo" : undefined}
          onClick={() => {
            setPestana("PROVEEDORES");
            cancelarEdicionRazon();
          }}
        >
          Proveedores ({proveedores.length})
        </button>
        <button
          className={pestana === "CLIENTES" ? "activo" : undefined}
          onClick={() => {
            setPestana("CLIENTES");
            cancelarEdicionRazon();
          }}
        >
          Clientes ({clientes.length})
        </button>
      </div>

      <div className="acciones">
        <button type="button" className={pestana === "SIN_CLASIFICAR" ? "activo" : undefined}
          onClick={() => { setPestana("SIN_CLASIFICAR"); setSeleccion([]); cancelarEdicionRazon(); }}>
          Sin clasificar ({(datos ?? []).filter((e) => e.tipo_relacion === "SIN_CLASIFICAR" ||
            ((e.tipo_relacion === "PROVEEDOR" || e.tipo_relacion === "AMBOS") && !e.clasificacion_proveedor)).length})
        </button>
        <button type="button" disabled={!seleccion.length || operando} onClick={() => void notificar()}>
          Notificar inmediatamente a Administrador ({seleccion.length})
        </button>
        {pestana === "SIN_CLASIFICAR" && puedeClasificar && <>
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
          esta lista; al asignarles Tipo A o Tipo B se registrarán como proveedores.
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
              {encabezadoOrdenable("RUC", "ruc")}
              {encabezadoOrdenable("Razón social", "razon_social")}
              {encabezadoOrdenable("Usuario", "usuario")}
              {esProveedor && encabezadoOrdenable("Tipo proveedor", "tipo")}
              {encabezadoOrdenable("Autorizada", "autorizada")}
              <th>Agente de retención</th>
            </tr>
          </thead>
          <tbody>
            {empresasOrdenadas.map((empresa) => {
              const editandoRazon = editandoRazonId === empresa.id;

              return (
                <tr key={empresa.id}>
                  <td><input type="checkbox" aria-label={`Seleccionar ${empresa.ruc}`}
                    disabled={!pendientes.some((e) => e.id === empresa.id)}
                    checked={seleccion.includes(empresa.id)}
                    onChange={(ev) => setSeleccion((prev) => ev.target.checked ? [...prev, empresa.id] : prev.filter((id) => id !== empresa.id))}/></td>
                  <td>{empresa.ruc}</td>
                  <td>
                    {editandoRazon ? (
                      <div className="acciones empresas-razon-social-edicion">
                        <input
                          value={razonEditada}
                          onChange={(ev) => setRazonEditada(ev.target.value)}
                          maxLength={300}
                          aria-label={`Editar razón social ${empresa.ruc}`}
                          autoFocus
                        />
                        <button type="button" onClick={() => void guardarRazonSocial(empresa)}>
                          Guardar
                        </button>
                        <button type="button" onClick={cancelarEdicionRazon}>
                          Cancelar
                        </button>
                      </div>
                    ) : (
                      <>
                        {puedeClasificar ? (
                          <button
                            type="button"
                            className="empresas-razon-social-enlace"
                            aria-label={`Editar razón social ${empresa.ruc}`}
                            onClick={() => iniciarEdicionRazon(empresa)}
                          >
                            {empresa.razon_social}
                          </button>
                        ) : (
                          empresa.razon_social
                        )}
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
                      <fieldset className="empresas-tipo-proveedor" disabled={!puedeClasificar || operando}>
                        <legend className="solo-lectores">Tipo de proveedor para {empresa.ruc}</legend>
                        {(["A", "B"] as const).map((tipo) => (
                          <label key={tipo}>
                            <input
                              type="radio"
                              name={`tipo-proveedor-${empresa.id}`}
                              value={tipo}
                              checked={empresa.clasificacion_proveedor === tipo}
                              onChange={() => void clasificarProveedor(empresa, tipo)}
                            />
                            <span>Tipo {tipo}</span>
                          </label>
                        ))}
                      </fieldset>
                    </td>
                  )}
                  <td>
                    <input
                      type="checkbox"
                      aria-label={`Autorizada ${empresa.ruc}`}
                      checked={empresa.autorizada}
                      disabled={!puedeAutorizar}
                      onChange={(ev) => cambiar(empresa, "autorizada", ev.target.checked)}
                    />
                    <span className={empresa.autorizada ? "estado-autorizacion-activa" : "estado-autorizacion-desactivada"}>
                      {empresa.autorizada ? "Autorizada" : "Desactivada"}
                    </span>
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      aria-label={`Agente de retención ${empresa.ruc}`}
                      checked={empresa.agente_retencion}
                      disabled={!puedeClasificar}
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
