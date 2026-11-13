import { useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { conParametros, enviarJson, useDatos } from "../api";
import { Estado } from "../componentes";
import { formatearMonto, numeroComprobante } from "../formato";
import type { Documento, Expediente } from "../tipos";

type Asignacion = {
  expediente_id: string;
  importe_asignado: string;
  evidencia: string;
  confianza?: string | null;
  referencia_confirmada?: boolean;
  expediente?: { id: string; serie: string; correlativo: string; moneda: string; importe_total: string } | null;
};
type Pago = {
  id: string;
  documento_id: string;
  documento_nombre: string | null;
  banco: string | null;
  tipo_operacion: string;
  fecha_hora: string | null;
  numero_operacion: string | null;
  beneficiario: string | null;
  cuenta_beneficiario: string | null;
  agencia: string | null;
  moneda: string | null;
  importe: string | null;
  remitente: string | null;
  cuenta_remitente: string | null;
  estado: string;
  conciliado: boolean;
  total_asignado: string;
  diferencia: string | null;
  destacado_expediente_id?: string | null;
  asignaciones: Asignacion[];
};
type Borrador = { expediente: Expediente; importe: string };

export default function PagoDocumental() {
  const { documentoId = "" } = useParams();
  const [parametros] = useSearchParams();
  const destacado = parametros.get("expediente");
  const { datos: documento, error: errorDocumento, cargando: cargandoDocumento } = useDatos<Documento>(
    `/api/v1/documentos/${documentoId}`,
  );
  const { datos: grupos, error: errorPago, recargar } = useDatos<Pago[]>(
    `/api/v1/pagos-documentales/por-documento/${documentoId}`,
  );
  const objetivo = useDatos<Expediente>(destacado ? `/api/v1/expedientes/${destacado}` : null);
  const [buscar, setBuscar] = useState("");
  const busqueda = useDatos<Expediente[]>(
    conParametros("/api/v1/expedientes", { buscar: buscar.trim(), limit: "20" }),
  );
  const [borradores, setBorradores] = useState<Borrador[]>([]);
  const [montos, setMontos] = useState<Record<string, string>>({});
  const [cargando, setCargando] = useState(false);
  const [mensaje, setMensaje] = useState("");
  const [error, setError] = useState("");
  const pago = grupos?.[0];
  const sugerencias = leerSugerencias(documento);
  const totalBorrador = useMemo(
    () => borradores.reduce((suma, fila) => suma + (Number(fila.importe) || 0), 0),
    [borradores],
  );

  const agregar = (expediente: Expediente) => {
    setBorradores((actual) => actual.some((fila) => fila.expediente.id === expediente.id)
      ? actual
      : [...actual, { expediente, importe: "" }]);
  };

  const guardarDistribucion = async () => {
    setCargando(true); setError(""); setMensaje("");
    try {
      await enviarJson("/api/v1/pagos-documentales", "POST", {
        documento_id: documentoId,
        asignaciones: borradores.map((fila) => ({
          expediente_id: fila.expediente.id,
          importe_asignado: fila.importe,
          evidencia: `Referencia elegida por el usuario: ${numeroComprobante(fila.expediente.serie, fila.expediente.correlativo)}`,
        })),
      });
      setMensaje("Distribución guardada como pendiente de confirmación.");
      setBorradores([]); recargar();
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setCargando(false); }
  };

  const confirmar = async () => {
    if (!pago) return;
    setCargando(true); setError(""); setMensaje("");
    try {
      await enviarJson(`/api/v1/pagos-documentales/${pago.id}/conciliar`, "POST", {
        confirmar_referencias: true,
      });
      setMensaje("Pago conciliado. Las facturas conservan sus expedientes fiscales individuales.");
      recargar();
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setCargando(false); }
  };

  const actualizarDistribucion = async () => {
    if (!pago) return;
    setCargando(true); setError(""); setMensaje("");
    try {
      const asignaciones = pago.asignaciones.map((fila) => ({
          expediente_id: fila.expediente_id,
          importe_asignado: montos[fila.expediente_id] ?? fila.importe_asignado,
          evidencia: fila.evidencia,
          confianza: fila.confianza,
      }));
      await enviarJson(`/api/v1/pagos-documentales/${pago.id}/asignaciones`, "PUT", {
        asignaciones: [...asignaciones, ...borradores.map((fila) => ({
          expediente_id: fila.expediente.id,
          importe_asignado: fila.importe,
          evidencia: `Referencia elegida por el usuario: ${numeroComprobante(fila.expediente.serie, fila.expediente.correlativo)}`,
          confianza: undefined,
        }))],
      });
      setBorradores([]);
      setMensaje("Distribución actualizada; permanece pendiente de confirmación.");
      setMontos({});
      recargar();
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setCargando(false); }
  };

  const objetivoDisponible = objetivo.datos
    && !pago?.asignaciones.some((fila) => fila.expediente_id === objetivo.datos?.id);
  const borradoresValidos = borradores.every((fila) => Number(fila.importe) > 0);
  const tablaBorradores = (
    borradores.length > 0 && <table><thead><tr><th>Factura fiscal</th><th>Importe asignado</th><th></th></tr></thead><tbody>
            {borradores.map((fila) => <tr key={fila.expediente.id}><td>{numeroComprobante(fila.expediente.serie, fila.expediente.correlativo)}</td>
              <td><input aria-label={`Importe ${numeroComprobante(fila.expediente.serie, fila.expediente.correlativo)}`} type="number" min="0.01" step="0.01" value={fila.importe} onChange={(e) => setBorradores((actual) => actual.map((item) => item.expediente.id === fila.expediente.id ? { ...item, importe: e.target.value } : item))} /></td>
              <td><button className="secundario" onClick={() => setBorradores((actual) => actual.filter((item) => item.expediente.id !== fila.expediente.id))}>Quitar</button></td></tr>)}
          </tbody></table>
  );

  if (cargandoDocumento || !documento) {
    return <main className="pagina"><Estado cargando={cargandoDocumento} error={errorDocumento} vacio={false}>{null}</Estado></main>;
  }

  return (
    <main className="pagina">
      <header className="encabezado-pagina">
        <div><h1>Pago documental agrupado</h1><p>El voucher reúne pagos; cada factura conserva su expediente fiscal.</p></div>
        {destacado && objetivo.datos
          ? <Link className="boton secundario" to={`/expedientes/${objetivo.datos.id}`}>Volver al expediente</Link>
          : <Link className="boton secundario" to="/pendientes">Volver a Pendientes</Link>}
      </header>
      <section className="tarjeta">
        <h2>Voucher</h2>
        <p><a href={`/api/v1/documentos/${documento.id}/archivo`} target="_blank" rel="noreferrer">{documento.nombre_original}</a></p>
        <CampoExtraccion documento={documento} nombre="banco" etiqueta="Banco" />
        <CampoExtraccion documento={documento} nombre="tipo_operacion" etiqueta="Operación" />
        <CampoExtraccion documento={documento} nombre="fecha_emision" etiqueta="Fecha" />
        <CampoExtraccion documento={documento} nombre="hora_operacion" etiqueta="Hora" />
        <CampoExtraccion documento={documento} nombre="numero_operacion" etiqueta="N.º de operación" />
        <CampoExtraccion documento={documento} nombre="beneficiario" etiqueta="Beneficiario" />
        <CampoExtraccion documento={documento} nombre="cuenta_beneficiario" etiqueta="Cuenta destino" />
        <CampoExtraccion documento={documento} nombre="agencia" etiqueta="Agencia" />
        <CampoExtraccion documento={documento} nombre="remitente" etiqueta="Remitente" />
        <CampoExtraccion documento={documento} nombre="cuenta_remitente" etiqueta="Cuenta origen" />
        <CampoExtraccion documento={documento} nombre="importe_total" etiqueta="Importe" />
      </section>
      {sugerencias.length > 0 && <section className="tarjeta">
        <h2>Referencias de factura sugeridas por OCR</h2>
        <p>Estas lecturas no crean vínculos ni confirman pagos. Verifica cada referencia y su importe.</p>
        <ul>{sugerencias.map((fila, indice) => <li key={`${fila.serie}-${fila.correlativo}-${indice}`}>
          {fila.serie}-{fila.correlativo} · {fila.importe_asignado} · {Math.round(Number(fila.confianza ?? 0) * 100)}% · {fila.evidencia}
        </li>)}</ul>
      </section>}

      {objetivo.error && <p role="alert">{objetivo.error}</p>}
      {objetivoDisponible && objetivo.datos && !pago?.conciliado && <section className="tarjeta">
        <button type="button" disabled={borradores.some((fila) => fila.expediente.id === objetivo.datos?.id)}
          onClick={() => { if (objetivo.datos) agregar(objetivo.datos); }}>
          Agregar expediente {numeroComprobante(objetivo.datos.serie, objetivo.datos.correlativo)}
        </button>
      </section>}
      {pago ? (
        <section className="tarjeta">
          <h2>Facturas incluidas</h2>
          <p>Estado: <strong>{pago.estado}</strong> · Total del voucher: {pago.moneda ?? ""} {pago.importe ?? "Pendiente OCR"} · Asignado: {pago.total_asignado} · Diferencia: {pago.diferencia ?? "—"}</p>
          <table><thead><tr><th>Factura</th><th>Total factura</th><th>Asignación</th><th>Referencia</th></tr></thead>
            <tbody>{pago.asignaciones.map((fila) => <tr key={fila.expediente_id} className={destacado === fila.expediente_id ? "fila-destacada" : undefined}>
              <td>{fila.expediente ? <Link to={`/expedientes/${fila.expediente.id}`}>{numeroComprobante(fila.expediente.serie, fila.expediente.correlativo)}</Link> : fila.expediente_id}</td>
              <td>{fila.expediente ? formatearMonto(fila.expediente.moneda as "PEN" | "USD", fila.expediente.importe_total) : "—"}</td>
              <td>{pago.conciliado ? `${pago.moneda ?? ""} ${fila.importe_asignado}` : <input aria-label={`Importe asignado ${fila.expediente_id}`} type="number" min="0.01" step="0.01" value={montos[fila.expediente_id] ?? fila.importe_asignado} onChange={(e) => setMontos((actual) => ({ ...actual, [fila.expediente_id]: e.target.value }))} />}</td><td>{fila.referencia_confirmada ? "Confirmada" : "Pendiente de confirmación"} · {fila.evidencia}</td>
            </tr>)}</tbody>
          </table>
          {!pago.conciliado && <>
            {tablaBorradores}
            <button className="secundario" disabled={cargando || !borradoresValidos} onClick={() => void actualizarDistribucion()}>Actualizar distribución</button>
            <button disabled={cargando || borradores.length > 0 || !pago.importe || Number(pago.diferencia) !== 0} onClick={() => void confirmar()}>Confirmar conciliación</button>
          </>}
        </section>
      ) : (
        <section className="tarjeta">
          <h2>Distribuir pago entre facturas</h2>
          <p>Busca por número o proveedor. La selección de una factura requiere confirmación humana; el importe por sí solo no crea vínculos.</p>
          <label>Buscar factura<input value={buscar} onChange={(e) => setBuscar(e.target.value)} placeholder="F091-00007270 o proveedor" /></label>
          {busqueda.error && <p role="alert" className="error">{busqueda.error}</p>}
          {busqueda.datos?.map((expediente) => <p key={expediente.id}>
            <button className="secundario" onClick={() => agregar(expediente)}>Agregar</button>{" "}
            {numeroComprobante(expediente.serie, expediente.correlativo)} · {expediente.emisor.razon_social} · {formatearMonto(expediente.moneda, expediente.importe_total)}
          </p>)}
          {tablaBorradores}
          <p>Total distribuido: {totalBorrador.toFixed(2)} {leerCampo(documento, "moneda")}</p>
          <button disabled={cargando || !borradores.length || borradores.some((fila) => !fila.importe || Number(fila.importe) <= 0)} onClick={() => void guardarDistribucion()}>
            {cargando ? "Guardando…" : "Guardar distribución"}
          </button>
        </section>
      )}
      {mensaje && <p role="status">{mensaje}</p>}{(error || errorPago) && <p role="alert" className="error">{error || errorPago}</p>}
    </main>
  );
}

function leerCampo(documento: Documento, nombre: string): string {
  const datos = documento.datos_extraidos as Record<string, unknown> | null;
  const procesamiento = datos?.procesamiento_documental as Record<string, unknown> | undefined;
  const extraccion = procesamiento?.extraccion_estructurada as Record<string, unknown> | undefined;
  const campos = extraccion?.campos as Record<string, unknown> | undefined;
  const campo = campos?.[nombre] as { valor?: unknown } | string | undefined;
  return typeof campo === "string" ? campo : String(campo?.valor ?? "");
}

function leerSugerencias(documento?: Documento): { serie: string; correlativo: string; importe_asignado: string; confianza?: number; evidencia: string }[] {
  if (!documento) return [];
  const datos = documento.datos_extraidos as Record<string, unknown> | null;
  const procesamiento = datos?.procesamiento_documental as Record<string, unknown> | undefined;
  const extraccion = procesamiento?.extraccion_estructurada as Record<string, unknown> | undefined;
  const campos = extraccion?.campos as Record<string, unknown> | undefined;
  const contenedor = campos?.asignaciones_facturas as { valor?: unknown } | undefined;
  if (!Array.isArray(contenedor?.valor)) return [];
  return contenedor.valor.filter((fila): fila is { serie: string; correlativo: string; importe_asignado: string; confianza?: number; evidencia: string } =>
    typeof fila === "object" && fila !== null && "serie" in fila && "correlativo" in fila && "importe_asignado" in fila && "evidencia" in fila,
  );
}

function CampoExtraccion({ documento, nombre, etiqueta }: { documento: Documento; nombre: string; etiqueta: string }) {
  const datos = documento.datos_extraidos as Record<string, unknown> | null;
  const procesamiento = datos?.procesamiento_documental as Record<string, unknown> | undefined;
  const extraccion = procesamiento?.extraccion_estructurada as Record<string, unknown> | undefined;
  const campos = extraccion?.campos as Record<string, unknown> | undefined;
  const valorCrudo = campos?.[nombre] as { valor?: unknown; confianza?: unknown; evidencia?: unknown } | string | undefined;
  const confirmada = datos?.extraccion_confirmada as Record<string, unknown> | undefined;
  const camposConfirmados = confirmada?.campos as Record<string, unknown> | undefined;
  const valorConfirmado = camposConfirmados?.[nombre];
  const campo = typeof valorCrudo === "string"
    ? { valor: valorCrudo }
    : valorCrudo?.valor !== undefined
      ? valorCrudo
      : valorConfirmado !== undefined
        ? { valor: valorConfirmado, confianza: 1, evidencia: "Confirmación humana" }
        : undefined;
  if (!campo?.valor) return null;
  return <p><strong>{etiqueta}:</strong> {String(campo.valor)} <small>({Math.round(Number(campo.confianza ?? 0) * 100)}% · {String(campo.evidencia ?? "sin evidencia")})</small></p>;
}
