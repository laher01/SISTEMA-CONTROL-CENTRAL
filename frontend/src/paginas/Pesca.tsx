import { useState } from "react";
import type { FormEvent } from "react";

import { enviarFormulario, enviarJson, useDatos } from "../api";

type Operacion = {
  id: string;
  fecha_reporte: string;
  puerto: string;
  muelle: string;
  planta: string;
  estado: string;
};

type Descarga = { descarga_id: string; embarcacion_id: string; matricula: string; nombre: string };
type Vehiculo = {
  id: string;
  placa: string;
  tipo: string;
  chofer: string;
  estado: string;
  turno: string | null;
  fecha_reporte_planta: string | null;
  inicio_planta: string | null;
  fin_planta: string | null;
};
type Archivo = { id: string; tipo: string; nombre: string };
type Paquete = { vehiculo_id: string; placa: string; documentacion_lista: boolean; faltantes: string[] };
type Resumen = {
  total_peso_muelle_kg: number;
  total_peso_aceptado_planta_kg: number;
  vehiculos: Array<{
    vehiculo_id: string;
    placa: string;
    resultado_planta: string;
    peso_aceptado: number | null;
    unidad: string | null;
    peso_muelle_kg: number | null;
  }>;
};

const DOCUMENTOS = [
  ["guia_remitente", "Guía de remisión remitente"],
  ["guia_transportista", "Guía de remisión transportista"],
  ["acta_fiscalizacion", "Acta de fiscalización"],
  ["formato_descarga", "Formato de descarga"],
  ["certificado_procedencia", "Certificado de procedencia"],
  ["certificado_captura", "Certificado de captura"],
  ["peso_planta", "Peso registrado en planta"],
  ["otro", "Otro documento"],
] as const;

function fechaHoraLocalActual() {
  const fecha = new Date(Date.now() - new Date().getTimezoneOffset() * 60_000);
  return fecha.toISOString().slice(0, 16);
}

async function manejar<T>(accion: () => Promise<T>, alExito: () => void, alError: (mensaje: string) => void) {
  try {
    await accion();
    alExito();
  } catch (error) {
    alError(error instanceof Error ? error.message : String(error));
  }
}

export default function Pesca() {
  const { datos: operaciones, error, cargando, recargar } = useDatos<Operacion[]>("/api/v1/pesca/operaciones");
  const [seleccionada, setSeleccionada] = useState("");
  const [aviso, setAviso] = useState("");
  const op = operaciones?.find((item) => item.id === seleccionada);
  const base = seleccionada ? `/api/v1/pesca/operaciones/${seleccionada}` : "/api/v1/pesca/operaciones";
  const { datos: descargas, recargar: recargarDescargas } = useDatos<Descarga[]>(seleccionada ? `${base}/embarcaciones` : "");
  const { datos: vehiculos, recargar: recargarVehiculos } = useDatos<Vehiculo[]>(seleccionada ? `${base}/vehiculos` : "");
  const { datos: archivos, recargar: recargarArchivos } = useDatos<Archivo[]>(seleccionada ? `${base}/documentos` : "");
  const { datos: paquetes, recargar: recargarPaquetes } = useDatos<Paquete[]>(seleccionada ? `${base}/documentacion` : "");
  const { datos: resumen, recargar: recargarResumen } = useDatos<Resumen>(seleccionada ? `${base}/resumen` : "");

  const refrescarDetalle = () => {
    recargarDescargas();
    recargarVehiculos();
    recargarArchivos();
    recargarPaquetes();
    recargarResumen();
  };
  const listar = () => {
    recargar();
    refrescarDetalle();
  };

  const crearOperacion = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formulario = event.currentTarget;
    const form = new FormData(formulario);
    void manejar(
      () => enviarJson<Operacion>("/api/v1/pesca/operaciones", "POST", {
        puerto: form.get("puerto"), muelle: form.get("muelle"), planta: form.get("planta"),
      }),
      () => { setAviso("Operación creada."); formulario.reset(); recargar(); },
      setAviso,
    );
  };

  const agregarEmbarcacion = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!seleccionada) return;
    const formulario = event.currentTarget;
    const form = new FormData(formulario);
    void manejar(
      () => enviarJson<Descarga>(`${base}/embarcaciones`, "POST", {
        matricula: form.get("matricula"), nombre: form.get("nombre"), patron_armador: form.get("patron_armador"),
        intermediario: form.get("intermediario") || null,
      }),
      () => { setAviso("Embarcación vinculada."); formulario.reset(); refrescarDetalle(); }, setAviso,
    );
  };

  const agregarVehiculo = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!seleccionada) return;
    const formulario = event.currentTarget;
    const form = new FormData(formulario);
    void manejar(
      () => enviarJson<Vehiculo>(`${base}/vehiculos`, "POST", {
        placa: form.get("placa"), tipo: form.get("tipo"), chofer: form.get("chofer"), turno: form.get("turno") || null,
      }),
      () => { setAviso("Vehículo agregado."); formulario.reset(); refrescarDetalle(); }, setAviso,
    );
  };

  const subirArchivo = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!seleccionada) return;
    const formulario = event.currentTarget;
    const form = new FormData(formulario);
    const file = form.get("archivo");
    if (!(file instanceof File) || !file.size) { setAviso("Selecciona el archivo o foto que vas a subir."); return; }
    const data = new FormData();
    data.append("archivo", file);
    data.append("tipo", String(form.get("tipo")));
    const idVehiculo = String(form.get("vehiculo"));
    if (idVehiculo) data.append("vehiculo_ids", idVehiculo);
    void manejar(
      () => enviarFormulario(`${base}/documentos`, data),
      () => { setAviso("Documento guardado."); formulario.reset(); refrescarDetalle(); }, setAviso,
    );
  };

  const cerrarOperacion = () => {
    if (!seleccionada) return;
    void manejar(
      () => enviarJson(`${base}/cerrar`, "POST"),
      () => { setAviso("Operación cerrada."); listar(); }, setAviso,
    );
  };

  return (
    <section className="pesca">
      <header className="pesca-cabecera">
        <div><p className="sobrelinea">MUELLE · PLANTA</p><h2>Operaciones de pesca</h2><p>Seguimiento de descargas, vehículos, pesos aceptados y documentos.</p></div>
        <button type="button" onClick={listar}>Actualizar</button>
      </header>
      {aviso && <p className="pesca-aviso" role="status">{aviso}<button type="button" onClick={() => setAviso("")}>Cerrar</button></p>}
      <div className="pesca-columnas">
        <div className="pesca-panel">
          <h3>Nueva operación</h3>
          <form className="pesca-form" onSubmit={crearOperacion}>
            <label>Puerto<input name="puerto" required placeholder="Paita" /></label>
            <label>Muelle<input name="muelle" required placeholder="Nombre del muelle" /></label>
            <label>Planta de destino<input name="planta" required placeholder="Planta procesadora" /></label>
            <button type="submit">Crear operación de hoy</button>
          </form>
          <h3>Operaciones recientes</h3>
          {cargando && <p>Cargando operaciones…</p>}
          {error && <p className="pesca-error">{error}</p>}
          {!cargando && !error && !operaciones?.length && <p>Aún no hay operaciones registradas.</p>}
          <div className="pesca-lista">
            {operaciones?.map((item) => (
              <button className={`pesca-op ${seleccionada === item.id ? "seleccionada" : ""}`} type="button" key={item.id} onClick={() => { setSeleccionada(item.id); setAviso(""); }}>
                <span><strong>{item.muelle}</strong><small>{item.puerto} · {new Date(`${item.fecha_reporte}T12:00:00`).toLocaleDateString("es-PE")}</small></span>
                <span className="pesca-estado">{item.estado === "cerrada" ? "Cerrada" : "En proceso"}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="pesca-detalle">
          {!op ? <div className="pesca-vacio"><h3>Selecciona una operación</h3><p>Verás aquí sus embarcaciones, vehículos y registro de planta.</p></div> : <>
            <div className="pesca-titulo-detalle"><div><p className="sobrelinea">{op.puerto} · {op.muelle}</p><h3>{op.planta}</h3></div><span className="pesca-estado grande">{op.estado === "cerrada" ? "Cerrada" : "En proceso"}</span></div>
            <div className="pesca-metricas"><div><small>Peso muelle</small><strong>{((resumen?.total_peso_muelle_kg ?? 0) / 1000).toFixed(3)} t</strong></div><div><small>Peso aceptado planta</small><strong>{((resumen?.total_peso_aceptado_planta_kg ?? 0) / 1000).toFixed(3)} t</strong></div><div><small>Vehículos</small><strong>{vehiculos?.length ?? 0}</strong></div></div>
            <div className="pesca-subpaneles">
              <form className="pesca-form pesca-form-horizontal" onSubmit={agregarEmbarcacion}>
                <h4>Vincular embarcación</h4>
                <label>Matrícula<input name="matricula" required /></label><label>Nombre<input name="nombre" required /></label>
                <label>Patrón o armador<input name="patron_armador" required /></label><label>Intermediario (opcional)<input name="intermediario" /></label>
                <button type="submit">Agregar embarcación</button>
              </form>
              <form className="pesca-form pesca-form-horizontal" onSubmit={agregarVehiculo}>
                <h4>Agregar vehículo</h4><label>Placa<input name="placa" required /></label>
                <label>Tipo<input name="tipo" required placeholder="3 ejes, carreta…" /></label><label>Chofer<input name="chofer" required /></label>
                <label>Turno de planta (si existe)<input name="turno" /></label><button type="submit">Agregar vehículo</button>
              </form>
            </div>

            <h4>Embarcaciones vinculadas</h4>
            {descargas?.length ? <ul className="pesca-chips">{descargas.map((d) => <li key={d.descarga_id}><strong>{d.nombre}</strong><small>{d.matricula}</small></li>)}</ul> : <p className="muted">Agrega la primera embarcación.</p>}

            <h4>Vehículos y recepción en planta</h4>
            {!vehiculos?.length ? <p className="muted">Agrega un vehículo para iniciar el seguimiento.</p> : <div className="pesca-vehiculos">{vehiculos.map((v) => {
              const linea = resumen?.vehiculos.find((x) => x.vehiculo_id === v.id);
              const paquete = paquetes?.find((x) => x.vehiculo_id === v.id);
              return <VehiculoCard key={v.id} operationId={seleccionada} vehicle={v} descargas={descargas ?? []} linea={linea} paquete={paquete} alGuardar={() => { setAviso("Datos de vehículo actualizados."); refrescarDetalle(); }} alError={setAviso} />;
            })}</div>}

            <form className="pesca-form pesca-doc-upload" onSubmit={subirArchivo}>
              <h4>Documentación de la operación</h4>
              <label>Tipo de documento<select name="tipo">{DOCUMENTOS.map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>
              <label>Vincular a<select name="vehiculo"><option value="">Toda la operación</option>{vehiculos?.map((v) => <option key={v.id} value={v.id}>{v.placa} · {v.chofer}</option>)}</select></label>
              <label>Foto o archivo (PDF/JPG/PNG/WEBP)<input name="archivo" type="file" accept="application/pdf,image/jpeg,image/png,image/webp" required /></label>
              <button type="submit">Subir documento</button>
            </form>
            <div className="pesca-documentacion"><strong>Documentación por vehículo</strong>{paquetes?.map((p) => <p key={p.vehiculo_id}><span>{p.placa}</span>{p.documentacion_lista ? <b className="texto-verde">Lista para presentar</b> : <small>Falta: {p.faltantes.join(", ")}</small>}</p>)}</div>
            <details className="pesca-archivos"><summary>Archivos cargados ({archivos?.length ?? 0})</summary><ul>{archivos?.map((a) => <li key={a.id}>{a.tipo.replaceAll("_", " ")} · <a href={`/api/v1/pesca/documentos/${a.id}/archivo`} target="_blank" rel="noreferrer">{a.nombre}</a></li>)}</ul></details>
            <button className="pesca-cerrar-op" type="button" disabled={!vehiculos?.length || vehiculos.some((v) => v.estado !== "cerrado")} onClick={cerrarOperacion}>Cerrar operación del día</button>
          </>}
        </div>
      </div>
    </section>
  );
}

type VehiculoLinea = Resumen["vehiculos"][number];
function VehiculoCard({ operationId, vehicle, descargas, linea, paquete, alGuardar, alError }: {
  operationId: string; vehicle: Vehiculo; descargas: Descarga[]; linea?: VehiculoLinea; paquete?: Paquete;
  alGuardar: () => void; alError: (mensaje: string) => void;
}) {
  const [peso, setPeso] = useState(linea?.peso_aceptado?.toString() ?? "");
  const [unidad, setUnidad] = useState(linea?.unidad ?? "ton");
  const [resultado, setResultado] = useState(linea?.resultado_planta === "pendiente" ? "completo" : linea?.resultado_planta ?? "completo");
  const [cajas, setCajas] = useState("0");
  const [motivo, setMotivo] = useState("");
  const [foto, setFoto] = useState<File | null>(null);
  const [esperando, setEsperando] = useState(false);
  const [sinFechaFinal, setSinFechaFinal] = useState(false);
  const [descargaId, setDescargaId] = useState(descargas[0]?.descarga_id ?? "");
  const [pesoMuelle, setPesoMuelle] = useState("");
  const [cajasMuelle, setCajasMuelle] = useState("");
  const [inicio, setInicio] = useState(false);
  const [fechaReporte, setFechaReporte] = useState(vehicle.fecha_reporte_planta ?? "");
  const [inicioManual, setInicioManual] = useState(vehicle.inicio_planta ? new Date(vehicle.inicio_planta).toISOString().slice(0, 16) : "");
  const [finManual, setFinManual] = useState(vehicle.fin_planta ? new Date(vehicle.fin_planta).toISOString().slice(0, 16) : "");
  const [observacionFechas, setObservacionFechas] = useState("");
  const [fechaFinalPeso, setFechaFinalPeso] = useState(fechaHoraLocalActual);
  const asignarCarga = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!descargaId) { alError("Vincula una embarcación primero."); return; }
    setEsperando(true);
    try {
      await enviarJson(`/api/v1/pesca/vehiculos/${vehicle.id}/cargas`, "POST", {
        descarga_id: descargaId, peso_muelle_kg: pesoMuelle ? Number(pesoMuelle) : null,
        cajas: cajasMuelle ? Number(cajasMuelle) : null,
      });
      setPesoMuelle(""); setCajasMuelle(""); alGuardar();
    } catch (error) { alError(error instanceof Error ? error.message : String(error)); }
    finally { setEsperando(false); }
  };
  const iniciarPlanta = async () => {
    setInicio(true);
    try { await enviarJson(`/api/v1/pesca/vehiculos/${vehicle.id}/planta/iniciar`, "POST"); alGuardar(); }
    catch (error) { alError(error instanceof Error ? error.message : String(error)); }
    finally { setInicio(false); }
  };
  const guardarFechas = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!observacionFechas.trim()) { alError("Indica el motivo del ajuste de fecha u hora."); return; }
    setEsperando(true);
    try {
      await enviarJson(`/api/v1/pesca/vehiculos/${vehicle.id}/planta/fechas`, "PATCH", {
        fecha_reporte_planta: fechaReporte || null,
        inicio_planta: inicioManual ? new Date(inicioManual).toISOString() : null,
        fin_planta: finManual ? new Date(finManual).toISOString() : null,
        observacion: observacionFechas,
      });
      setObservacionFechas(""); alGuardar();
    } catch (error) { alError(error instanceof Error ? error.message : String(error)); }
    finally { setEsperando(false); }
  };
  const cerrar = async () => {
    if (!foto) { alError("Selecciona la foto de huincha o ticket de planta antes de cerrar."); return; }
    setEsperando(true);
    try {
      await enviarJson(`/api/v1/pesca/vehiculos/${vehicle.id}/planta`, "POST", {
        resultado, peso_aceptado: Number(peso || 0), unidad, cajas_rechazadas: Number(cajas || 0),
        motivo_rechazo: motivo || null, no_registrar_fecha_finalizacion: sinFechaFinal,
        fecha_finalizacion: !sinFechaFinal && fechaFinalPeso ? new Date(fechaFinalPeso).toISOString() : null,
      });
      const data = new FormData(); data.append("archivo", foto); data.append("tipo", "peso_planta"); data.append("vehiculo_ids", vehicle.id);
      await enviarFormulario(`/api/v1/pesca/operaciones/${operationId}/documentos`, data);
      await enviarJson(`/api/v1/pesca/vehiculos/${vehicle.id}/planta/cerrar`, "POST");
      alGuardar();
    } catch (error) { alError(error instanceof Error ? error.message : String(error)); }
    finally { setEsperando(false); }
  };
  const acceptedKg = Number(linea?.peso_aceptado ?? 0) * ({ ton: 1000, kg: 1, lb: 0.45359237, oz: 0.02834952 }[linea?.unidad ?? "ton"] ?? 1000);
  const colorPeso = linea?.peso_muelle_kg == null ? "" : acceptedKg > linea.peso_muelle_kg ? "verde" : acceptedKg === linea.peso_muelle_kg ? "naranja" : "rojo";
  return <article className="pesca-vehiculo">
    <header><div><strong>{vehicle.placa}</strong><small>{vehicle.tipo} · {vehicle.chofer}</small></div><span className={`pesca-estado ${vehicle.estado === "cerrado" ? "cerrado" : ""}`}>{vehicle.estado.replaceAll("_", " ")}</span></header>
    <div className="pesca-vehiculo-meta"><span>Turno: {vehicle.turno || "Sin turno"}</span><span>{descargas.length} embarcaciones vinculadas</span></div>
    {vehicle.estado === "pendiente_planta" && <button type="button" className="pesca-secundario" disabled={inicio} onClick={() => void iniciarPlanta()}>{inicio ? "Registrando…" : "Iniciar recepción en planta"}</button>}
    {vehicle.estado !== "cerrado" && <details className="pesca-fechas"><summary>Fechas y horas de planta</summary><form className="pesca-form pesca-fechas-form" onSubmit={(event) => void guardarFechas(event)}>
      <label>Fecha de reporte<input type="date" value={fechaReporte} onChange={(e) => setFechaReporte(e.target.value)} /></label>
      <label>Inicio de descarga<input type="datetime-local" value={inicioManual} onChange={(e) => setInicioManual(e.target.value)} /></label>
      <label>Fin de descarga<input type="datetime-local" value={finManual} onChange={(e) => setFinManual(e.target.value)} /></label>
      <label>Motivo del ajuste<input value={observacionFechas} onChange={(e) => setObservacionFechas(e.target.value)} required /></label>
      <button type="submit" disabled={esperando}>Guardar fechas</button>
    </form></details>}
    {vehicle.estado !== "cerrado" && <form className="pesca-form pesca-carga-form" onSubmit={(event) => void asignarCarga(event)}>
      <strong>Asignar carga desde muelle</strong>
      <label>Embarcación<select value={descargaId} onChange={(e) => setDescargaId(e.target.value)} required><option value="">Seleccionar…</option>{descargas.map((d) => <option key={d.descarga_id} value={d.descarga_id}>{d.nombre} · {d.matricula}</option>)}</select></label>
      <label>Peso de muelle (kg)<input type="number" min="0" step="0.001" value={pesoMuelle} onChange={(e) => setPesoMuelle(e.target.value)} /></label>
      <label>Cajas (si se registran)<input type="number" min="0" step="1" value={cajasMuelle} onChange={(e) => setCajasMuelle(e.target.value)} /></label>
      <button type="submit" disabled={esperando || !descargaId}>Guardar carga</button>
    </form>}
    {linea?.peso_aceptado != null && <p className={`pesca-diferencia ${colorPeso}`}>Aceptado en planta: {linea.peso_aceptado} {linea.unidad} · comparación muelle: {colorPeso || "pendiente"}</p>}
    {paquete && !paquete.documentacion_lista && <p className="pesca-pendiente-doc">Pendiente: {paquete.faltantes.join(", ")}</p>}
    {vehicle.estado !== "cerrado" && <div className="pesca-form pesca-peso-form">
      <label>Resultado<select value={resultado} onChange={(e) => setResultado(e.target.value)}><option value="completo">Completo</option><option value="parcial">Parcial</option><option value="rechazado">Rechazado</option></select></label>
      <label>Peso aceptado<input type="number" min="0" step="0.001" value={peso} onChange={(e) => setPeso(e.target.value)} /></label>
      <label>Unidad<select value={unidad} onChange={(e) => setUnidad(e.target.value)}><option value="ton">Toneladas</option><option value="kg">Kilogramos</option><option value="lb">Libras</option><option value="oz">Onzas</option></select></label>
      {resultado !== "completo" && <label>Cajas rechazadas<input type="number" min="0" step="1" value={cajas} onChange={(e) => setCajas(e.target.value)} /></label>}
      {resultado === "rechazado" && <label>Motivo<select value={motivo} onChange={(e) => setMotivo(e.target.value)}><option value="">Seleccionar…</option><option value="calidad">Calidad</option><option value="contaminacion_quimica">Contaminación química</option><option value="excedente">Excedente</option><option value="otro">Otro</option></select></label>}
      {!sinFechaFinal && <label>Fecha/hora final<input type="datetime-local" value={fechaFinalPeso} onChange={(e) => setFechaFinalPeso(e.target.value)} /></label>}
      <label>Evidencia de peso<input type="file" accept="application/pdf,image/jpeg,image/png,image/webp" onChange={(e) => setFoto(e.target.files?.[0] ?? null)} /></label>
      <label className="pesca-checkbox"><input type="checkbox" checked={sinFechaFinal} onChange={(e) => setSinFechaFinal(e.target.checked)} /> No registrar fecha final</label>
      <button type="button" disabled={esperando || (!peso && resultado !== "rechazado") || (resultado === "rechazado" && !motivo)} onClick={() => void cerrar()}>{esperando ? "Guardando…" : "Guardar peso y evidencia"}</button>
    </div>}
  </article>;
}
