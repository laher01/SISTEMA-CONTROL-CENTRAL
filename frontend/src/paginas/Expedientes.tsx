import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { conParametros, descargarPdfExpedientes, imprimirExpedientes, obtener, urlPdfExpediente, urlZipExpediente, useDatos } from "../api";
import { Estado, Paginacion, Semaforo } from "../componentes";
import FiltroJerarquia from "../componentes/FiltroJerarquia";
import { ETIQUETA_ESTADO, formatearFecha, formatearMonto, numeroExpediente } from "../formato";
import { ESTADOS_EXPEDIENTE, type Expediente, type SesionActual } from "../tipos";
import { formatearMonto as monto } from "../formato";

const POR_PAGINA = 50;

export default function Expedientes({ sesion }: { sesion: SesionActual }) {
  const [parametros, setParametros] = useSearchParams();
  const [seleccionados, setSeleccionados] = useState<Set<string>>(new Set());
  const [mensaje, setMensaje] = useState("");
  const [imprimiendo, setImprimiendo] = useState(false);
  const [descargando, setDescargando] = useState(false);

  const usuarioId = parametros.get("usuario_id") ?? "";
  const gestorId = parametros.get("gestor_id") ?? "";
  const estado = parametros.get("estado") ?? "";
  const pendiente = parametros.get("pendiente_aprobacion") ?? "";
  const receptor = parametros.get("receptor_ruc") ?? "";
  const emisor = parametros.get("emisor_ruc") ?? "";
  const tipoEmpresa = parametros.get("tipo_empresa") ?? "";
  const dia = parametros.get("dia") ?? "";
  const desde = parametros.get("fecha_desde") ?? "";
  const hasta = parametros.get("fecha_hasta") ?? "";
  const buscar = parametros.get("buscar") ?? "";
  const pagina = Number(parametros.get("pagina") ?? "0");

  const filtrosBase = {
    estado,
    usuario_id: usuarioId,
    gestor_id: gestorId,
    pendiente_aprobacion: pendiente,
    receptor_ruc: receptor.length === 11 ? receptor : undefined,
    emisor_ruc: emisor.length === 11 ? emisor : undefined,
    tipo_empresa: tipoEmpresa,
    dia,
    fecha_desde: desde,
    fecha_hasta: hasta,
    buscar: buscar.trim(),
  };

  const ruta = conParametros("/api/v1/expedientes", {
    ...filtrosBase,
    limit: String(POR_PAGINA),
    offset: String(pagina * POR_PAGINA),
  });
  const rutaIds = conParametros("/api/v1/expedientes/ids", {
    ...filtrosBase,
    limit: "1000",
  });
  const { datos, error, cargando } = useDatos<Expediente[]>(ruta);
  const { datos: resumen } = useDatos<{ total_expedientes: number; total_pen: string; total_usd: string }>(
    conParametros("/api/v1/expedientes/resumen", filtrosBase),
  );

  const cambiar = (clave: string, valor: string) => {
    const siguiente = new URLSearchParams(parametros);
    if (valor) siguiente.set(clave, valor);
    else siguiente.delete(clave);
    if (clave === "usuario_id") siguiente.delete("gestor_id");
    if (clave !== "pagina") siguiente.delete("pagina");
    setSeleccionados(new Set());
    setMensaje("");
    setParametros(siguiente);
  };

  const visibles = datos ?? [];
  const todosVisibles =
    visibles.length > 0 && visibles.every((item) => seleccionados.has(item.id));

  const alternarVisible = (id: string, marcado: boolean) => {
    setSeleccionados((actual) => {
      const siguiente = new Set(actual);
      if (marcado) siguiente.add(id);
      else siguiente.delete(id);
      return siguiente;
    });
  };

  const alternarTodosVisibles = (marcado: boolean) => {
    setSeleccionados((actual) => {
      const siguiente = new Set(actual);
      for (const item of visibles) {
        if (marcado) siguiente.add(item.id);
        else siguiente.delete(item.id);
      }
      return siguiente;
    });
  };

  const seleccionarTodosFiltrados = async () => {
    try {
      const ids = await obtener<string[]>(rutaIds);
      setSeleccionados(new Set(ids));
      setMensaje(`Seleccionados ${ids.length} expedientes del filtro actual.`);
    } catch (e) {
      setMensaje(e instanceof Error ? e.message : String(e));
    }
  };

  const imprimirSeleccion = async () => {
    if (seleccionados.size === 0) return;
    setImprimiendo(true);
    setMensaje("");
    try {
      const ordenFiltro = await obtener<string[]>(rutaIds);
      const idsOrdenados = ordenFiltro.filter((id) => seleccionados.has(id));
      const resultado = await imprimirExpedientes(idsOrdenados);
      setMensaje(
        `Impresión preparada: ${resultado.expedientes} expediente(s), ${resultado.pdfs} PDF(s)` +
          (resultado.sinPdf > 0 ? ` · sin PDF: ${resultado.sinPdf}` : ""),
      );
    } catch (e) {
      setMensaje(e instanceof Error ? e.message : String(e));
    } finally {
      setImprimiendo(false);
    }
  };

  const descargarSeleccion = async () => {
    if (seleccionados.size === 0) return;
    setDescargando(true);
    setMensaje("");
    try {
      const ordenFiltro = await obtener<string[]>(rutaIds);
      const idsOrdenados = ordenFiltro.filter((id) => seleccionados.has(id));
      if (idsOrdenados.length === 0) throw new Error("No hay expedientes seleccionados en el filtro actual.");
      const resultado = await descargarPdfExpedientes(idsOrdenados);
      setMensaje(
        `Descarga preparada: ${resultado.expedientes} expediente(s), ${resultado.pdfs} PDF(s)` +
          (resultado.sinPdf > 0 ? ` · sin PDF: ${resultado.sinPdf}` : ""),
      );
    } catch (e) {
      setMensaje(e instanceof Error ? e.message : String(e));
    } finally {
      setDescargando(false);
    }
  };

  return (
    <>
      <h2>Expedientes</h2>
      <div className="filtros">
        <FiltroJerarquia sesion={sesion} usuarioId={usuarioId} gestorId={gestorId} cambiar={cambiar} />
        <select aria-label="Tipo de empresa" value={tipoEmpresa} onChange={(e) => cambiar("tipo_empresa", e.target.value)}>
          <option value="">Todas las empresas</option>
          <option value="A">Tipo A</option>
          <option value="B">Tipo B</option>
        </select>
        <label>Día <input type="date" value={dia} onChange={(e) => cambiar("dia", e.target.value)} /></label>
        <label>Desde <input type="date" value={desde} onChange={(e) => cambiar("fecha_desde", e.target.value)} /></label>
        <label>Hasta <input type="date" value={hasta} onChange={(e) => cambiar("fecha_hasta", e.target.value)} /></label>
        <input placeholder="RUC emisor (11 dígitos)" value={emisor} maxLength={11} onChange={(e) => cambiar("emisor_ruc", e.target.value.replace(/\D/g, ""))} />
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

      <section className="panel-configuracion">
        <strong>Total del filtro completo (todas las páginas)</strong>
        <p>{resumen?.total_expedientes ?? "…"} expedientes · {monto("PEN", resumen?.total_pen ?? "0")} · {monto("USD", resumen?.total_usd ?? "0")}</p>
      </section>

      <div className="acciones">
        <button onClick={() => void seleccionarTodosFiltrados()}>
          Seleccionar todos los resultados del filtro
        </button>
        <button
          disabled={seleccionados.size === 0 || imprimiendo}
          onClick={() => void imprimirSeleccion()}
        >
          {imprimiendo ? "Preparando impresión…" : `Imprimir seleccionados (${seleccionados.size})`}
        </button>
        <button
          disabled={seleccionados.size === 0 || descargando || imprimiendo}
          onClick={() => void descargarSeleccion()}
        >
          {descargando ? "Preparando PDF…" : `Descargar PDF (${seleccionados.size})`}
        </button>
        {seleccionados.size > 0 && (
          <button onClick={() => setSeleccionados(new Set())}>Limpiar selección</button>
        )}
      </div>
      {mensaje && <p className="tenue">{mensaje}</p>}

      <Estado cargando={cargando} error={error} vacio={datos?.length === 0}>
        <table>
          <thead>
            <tr>
              <th>
                <input
                  type="checkbox"
                  aria-label="Seleccionar expedientes visibles"
                  checked={todosVisibles}
                  onChange={(e) => alternarTodosVisibles(e.target.checked)}
                />
              </th>
              <th>Estado</th>
              <th>Tipo</th>
              <th>Comprobante</th>
              <th>Emisión</th>
              <th>Emisor</th>
              <th>Receptor</th>
              <th className="num">Importe</th>
              <th>Descarga</th>
            </tr>
          </thead>
          <tbody>
            {datos?.map((e) => (
              <tr key={e.id}>
                <td>
                  <input
                    type="checkbox"
                    aria-label={`Seleccionar ${e.serie}-${e.correlativo}`}
                    checked={seleccionados.has(e.id)}
                    onChange={(ev) => alternarVisible(e.id, ev.target.checked)}
                  />
                </td>
                <td>
                  <Semaforo estado={e.estado} />
                </td>
                <td>{e.emisor.clasificacion_proveedor ? `Tipo ${e.emisor.clasificacion_proveedor}` : "Sin clasificar"}</td>
                <td>
                  <Link to={`/expedientes/${e.id}`}>
                    {e.tipo_comprobante === "RHE"
                      ? numeroExpediente(e.tipo_comprobante, e.serie, e.correlativo)
                      : "FACT " + numeroExpediente(e.tipo_comprobante, e.serie, e.correlativo)}
                  </Link>
                </td>
                <td>{formatearFecha(e.fecha_emision)}</td>
                <td><strong>{e.emisor.razon_social}</strong><small className="bloque tenue">RUC {e.emisor.ruc}</small></td>
                <td>
                  <strong>{e.receptor.razon_social}</strong>
                  <small className="bloque tenue">RUC {e.receptor.ruc}</small>
                  {e.pendiente_aprobacion && <span className="etiqueta">No autorizado</span>}
                </td>
                <td className="num">{formatearMonto(e.moneda, e.importe_total)}</td>
                <td>
                  <a href={urlPdfExpediente(e.id)} download={`expediente-${e.serie}-${e.correlativo}.pdf`}>
                    Descargar PDF
                  </a>
                  {" · "}
                  <a href={urlZipExpediente(e.id)}>ZIP completo</a>
                </td>
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
