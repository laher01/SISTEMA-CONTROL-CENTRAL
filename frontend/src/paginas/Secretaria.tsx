import { useState } from "react";
import { Link } from "react-router-dom";
import FiltroJerarquia from "../componentes/FiltroJerarquia";
import type { SesionActual } from "../tipos";

import {
  conParametros, descargarPdfExpedientes, imprimirExpedientes, urlPdfExpediente,
  urlZipExpediente, useDatos,
} from "../api";
import { formatearFecha, formatearMonto } from "../formato";

interface RegistroSecretaria {
  id: string;
  serie: string;
  correlativo: string;
  tipo_comprobante: string;
  fecha_emision: string;
  fecha_registro: string;
  fecha_carga: string | null;
  estado: string;
  moneda: "PEN" | "USD";
  importe_total: string;
  emisor: string;
  emisor_ruc: string;
  receptor: string;
  receptor_ruc: string;
  responsable: string;
  responsable_codigo: string;
  usuario: string;
  usuario_codigo: string;
  gestor: string;
  gestor_codigo: string;
  faltantes: string[];
  documentos: number;
}
interface Resumen {
  total_expedientes: number;
  total_pen: string;
  total_usd: string;
  filas: RegistroSecretaria[];
}

export default function Secretaria({ sesion }: { sesion: SesionActual }) {
  const [responsableId, setResponsableId] = useState("");
  const [usuarioId, setUsuarioId] = useState("");
  const [gestorId, setGestorId] = useState("");
  const cambiarJerarquia = (clave: string, valor: string) => {
    cambiarFiltro(() => {
      if (clave === "responsable_id") { setResponsableId(valor); setUsuarioId(""); setGestorId(""); }
      if (clave === "usuario_id") { setUsuarioId(valor); setGestorId(""); }
      if (clave === "gestor_id") setGestorId(valor);
    });
  };
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [dia, setDia] = useState("");
  const [mes, setMes] = useState("");
  const ultimoDiaMes = mes ? new Date(Date.UTC(Number(mes.slice(0, 4)), Number(mes.slice(5, 7)), 0)).getUTCDate() : 0;
  const inicioMes = mes ? `${mes}-01` : "";
  const finMes = mes ? `${mes}-${String(ultimoDiaMes).padStart(2, "0")}` : "";
  const [emisor, setEmisor] = useState("");
  const [receptor, setReceptor] = useState("");
  const [estado, setEstado] = useState("");
  const [tipoBusqueda, setTipoBusqueda] = useState("correlativo");
  const [busqueda, setBusqueda] = useState("");
  const [seleccionados, setSeleccionados] = useState<Set<string>>(new Set());
  const [trabajando, setTrabajando] = useState(false);
  const [mensaje, setMensaje] = useState("");
  const filtros = {
    responsable_id: responsableId,
    usuario_id: usuarioId,
    gestor_id: gestorId,
    desde: inicioMes || dia || desde || "1900-01-01",
    hasta: finMes || dia || hasta || "9999-12-31",
    empresa_emisora: emisor.trim() || undefined,
    empresa_receptora: receptor.trim() || undefined,
    estado,
    correlativo: tipoBusqueda === "correlativo" ? busqueda.trim() || undefined : undefined,
    monto_desde: tipoBusqueda === "monto" ? busqueda.trim() || undefined : undefined,
    monto_hasta: tipoBusqueda === "monto" ? busqueda.trim() || undefined : undefined,
    guia_remitente: tipoBusqueda === "guia" ? busqueda.trim() || undefined : undefined,
  };
  const { datos, cargando, error } = useDatos<Resumen>(
    conParametros("/api/v1/dashboard/secretaria-expedientes", filtros),
  );
  const filas = datos?.filas ?? [];
  const todos = filas.length > 0 && filas.every((f) => seleccionados.has(f.id));
  const cambiarFiltro = (accion: () => void) => {
    accion();
    setSeleccionados(new Set());
    setMensaje("");
  };
  const alternar = (id: string, marcado: boolean) => {
    setSeleccionados((actual) => {
      const nuevos = new Set(actual);
      if (marcado) nuevos.add(id);
      else nuevos.delete(id);
      return nuevos;
    });
  };
  const operar = async (descargar: boolean) => {
    const ids = filas.filter((f) => seleccionados.has(f.id)).map((f) => f.id);
    if (!ids.length) return;
    setTrabajando(true);
    try {
      const r = descargar ? await descargarPdfExpedientes(ids) : await imprimirExpedientes(ids);
      setMensaje(
        `${descargar ? "Descarga" : "Impresión"}: ${r.expedientes} expedientes, ${r.pdfs} PDF; ${r.sinPdf} sin PDF.`,
      );
    } catch (e) {
      setMensaje(e instanceof Error ? e.message : String(e));
    } finally {
      setTrabajando(false);
    }
  };
  const notificar = (r: RegistroSecretaria) => {
    const texto = `Revisión documental: ${r.tipo_comprobante} ${r.serie}-${r.correlativo}. ` +
      `Responsable: ${r.responsable} / Usuario: ${r.usuario} / Gestor: ${r.gestor}. Faltantes: ${r.faltantes.join(", ") || "Sin faltantes obligatorios"}. ` +
      `Expediente: ${r.id}`;
    void navigator.clipboard.writeText(texto).then(
      () => setMensaje("Aviso copiado. Abra el chat interno y envíelo al responsable."),
      () => setMensaje(texto),
    );
  };

  return (
    <>
      <h2>Control documental de Secretaría</h2>
      <p className="tenue">
        Consulta transversal por emisor, receptor y periodo. Los importes no constituyen
        crédito fiscal validado; los documentos pendientes requieren revisión.
      </p>
      <div className="filtros">
        <FiltroJerarquia sesion={sesion} responsableId={responsableId} usuarioId={usuarioId} gestorId={gestorId} cambiar={cambiarJerarquia} />
        <label>Día <input type="date" value={dia} onChange={(e) => cambiarFiltro(() => { setDia(e.target.value); if (e.target.value) { setMes(""); setDesde(""); setHasta(""); } })} /></label>
        <label>Desde <input type="date" value={desde} onChange={(e) => cambiarFiltro(() => { setDesde(e.target.value); if (e.target.value) { setMes(""); setDia(""); } })} /></label>
        <label>Hasta <input type="date" value={hasta} onChange={(e) => cambiarFiltro(() => { setHasta(e.target.value); if (e.target.value) { setMes(""); setDia(""); } })} /></label>
        <label>Mes de emisión <input type="month" aria-label="Mes de emisión" value={mes} onChange={(e) => cambiarFiltro(() => { setMes(e.target.value); if (e.target.value) { setDia(""); setDesde(""); setHasta(""); } })} /></label>
        <input aria-label="Empresa emisora o proveedora" placeholder="Proveedor: RUC o razón social" maxLength={100} value={emisor} onChange={(e) => cambiarFiltro(() => setEmisor(e.target.value))} />
        <input aria-label="Empresa receptora o cliente" placeholder="Cliente: RUC o razón social" maxLength={100} value={receptor} onChange={(e) => cambiarFiltro(() => setReceptor(e.target.value))} />
        <select aria-label="Estado expediente" value={estado} onChange={(e) => cambiarFiltro(() => setEstado(e.target.value))}>
          <option value="">Todos los estados</option>
          <option value="VERDE">Verde / completo</option>
          <option value="AMARILLO">Amarillo / observación</option>
          <option value="NARANJA">Naranja / incompleto</option>
          <option value="ROJO">Rojo / vencido</option>
        </select>
      </div>
      <div className="filtros">
        <label>Buscar por
          <select aria-label="Tipo de búsqueda documental" value={tipoBusqueda} onChange={(e) => cambiarFiltro(() => { setTipoBusqueda(e.target.value); setBusqueda(""); })}>
            <option value="correlativo">Correlativo de comprobante</option>
            <option value="monto">Monto exacto</option>
            <option value="guia">Guía de remisión remitente (nombre del archivo)</option>
          </select>
        </label>
        <label>Dato de búsqueda
          <input
            aria-label="Dato de búsqueda documental"
            type={tipoBusqueda === "monto" ? "number" : "text"}
            min={tipoBusqueda === "monto" ? "0" : undefined}
            step={tipoBusqueda === "monto" ? "0.01" : undefined}
            placeholder={tipoBusqueda === "correlativo" ? "Ej. E001-1521" : tipoBusqueda === "monto" ? "Ej. 954.01" : "Ej. EG07-2269"}
            value={busqueda}
            onChange={(e) => cambiarFiltro(() => setBusqueda(e.target.value))}
          />
        </label>
      </div>
      <section className="panel-configuracion">
        <strong>Resumen general del filtro (todas las filas)</strong>
        <p>
          {datos?.total_expedientes ?? "…"} expedientes ·
          {" "}{formatearMonto("PEN", datos?.total_pen ?? "0")} ·
          {" "}{formatearMonto("USD", datos?.total_usd ?? "0")}
        </p>
      </section>
      <div className="acciones">
        <button type="button" onClick={() => setSeleccionados(new Set(filas.map((f) => f.id)))}>
          Seleccionar todos los resultados
        </button>
        <button type="button" onClick={() => setSeleccionados(new Set())}>Limpiar selección</button>
        <button type="button" disabled={!seleccionados.size || trabajando} onClick={() => void operar(false)}>
          Imprimir seleccionados ({seleccionados.size})
        </button>
        <button type="button" disabled={!seleccionados.size || trabajando} onClick={() => void operar(true)}>
          Descargar PDF ({seleccionados.size})
        </button>
        <Link to="/chat">Abrir chat interno</Link>
      </div>
      {mensaje && <p role="status">{mensaje}</p>}
      {cargando && <p>Cargando expedientes…</p>}
      {error && <p role="alert">{error}</p>}
      <div style={{ overflowX: "auto" }}>
        <table>
          <thead>
            <tr>
              <th><input type="checkbox" aria-label="Seleccionar visibles" checked={todos} onChange={(e) => setSeleccionados(e.target.checked ? new Set(filas.map((f) => f.id)) : new Set())} /></th>
              <th>Comprobante</th><th>Fecha documento</th><th>Fecha de carga</th><th>Proveedor/emisor</th><th>Cliente/receptor</th>
              {!responsableId && <th>Responsable</th>}
              {!usuarioId && <th>Usuario</th>}
              {!gestorId && <th>Gestor</th>}
              <th>Estado</th>
              <th>Documentos faltantes</th><th>Registrados</th><th>Importe</th><th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {filas.map((f) => (
              <tr key={f.id}>
                <td><input type="checkbox" aria-label={`Seleccionar ${f.serie}-${f.correlativo}`} checked={seleccionados.has(f.id)} onChange={(e) => alternar(f.id, e.target.checked)} /></td>
                <td><Link to={`/expedientes/${f.id}`}>{f.tipo_comprobante} {f.serie}-{f.correlativo}</Link></td>
                <td>{formatearFecha(f.fecha_emision)}</td>
                 <td>{f.fecha_carga ? formatearFecha(f.fecha_carga) : "Sin carga"}</td>
                <td>{f.emisor}<small className="bloque tenue">{f.emisor_ruc}</small></td>
                <td>{f.receptor}<small className="bloque tenue">{f.receptor_ruc}</small></td>
                {!responsableId && <td>{f.responsable}<small className="bloque tenue">{f.responsable_codigo}</small></td>}
                {!usuarioId && <td>{f.usuario}<small className="bloque tenue">{f.usuario_codigo}</small></td>}
                {!gestorId && <td>{f.gestor}<small className="bloque tenue">{f.gestor_codigo}</small></td>}
                <td><strong>{f.estado}</strong></td>
                <td>{f.faltantes.length ? f.faltantes.join(", ") : "Sin faltantes"}</td>
                <td>{f.documentos}</td>
                <td>{formatearMonto(f.moneda, f.importe_total)}</td>
                <td>
                  <a href={urlPdfExpediente(f.id)} download>PDF</a>{" · "}
                  <a href={urlZipExpediente(f.id)}>ZIP</a>{" · "}
                  <button type="button" onClick={() => notificar(f)}>Preparar aviso</button>
                  {" · "}<Link to="/chat">Chat</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!cargando && !error && !filas.length && <p>No hay expedientes para el filtro seleccionado.</p>}
    </>
  );
}
