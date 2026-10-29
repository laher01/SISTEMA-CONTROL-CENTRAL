import { useState } from "react";
import type { FormEvent } from "react";

import { enviarFormulario, enviarJson, useDatos } from "../api";
import type { SesionActual } from "../tipos";

const ROLES_PESCA = [
  ["JEFE_BAHIA", "Jefe de bahía"], ["GERENTE", "Gerente"],
  ["ENCARGADO_MUELLE", "Encargado de muelle"], ["ARMADOR", "Armador"], ["PATRON", "Patrón"],
  ["APUNTADOR_MUELLE", "Apuntador de muelle"], ["APUNTADOR_PLANTA", "Apuntador de planta"],
  ["JEFE_CUADRILLA", "Jefe de cuadrilla"], ["SECRETARIA", "Secretaría"],
  ["TRAMITADORA", "Tramitadora"], ["TRANSPORTISTA", "Transportista"],
] as const;

type RolPesca = (typeof ROLES_PESCA)[number][0];
type CuentaCandidata = { cuenta_id: string; codigo: string; nombre: string };
type CuentaResponsablePesaje = CuentaCandidata & { rol: "APUNTADOR_MUELLE" | "ENCARGADO_MUELLE" };
type AsignacionPesca = { id: string; cuenta_id: string; rol: RolPesca; activa: boolean; codigo: string; nombre: string };
type ActividadCuadrilla = "LAVADO" | "CAJEO" | "ESTIBA";
type AsignacionCuadrilla = { id: string; nombre_integrante: string; actividad: ActividadCuadrilla; activa: boolean; monto_pago: number | null };
type RegistroActividad = { id: string; vehiculo_id: string; actividad: string; estado: string; cajas: number | null; hielo_kg: number | null; verificacion_visual: boolean | null; contaminacion_detectada: boolean | null; revision_final: boolean | null; observacion: string | null; actor_cuenta_id: string; updated_at: string };

type Operacion = {
  id: string;
  fecha_reporte: string;
  puerto: string;
  muelle: string;
  planta: string;
  armador_reportante: string | null;
  comprador: string | null;
  remitente: string | null;
  destinatario: string | null;
  facturador: string | null;
  toneladas_declaradas: number | null;
  precio_propuesto: number | null;
  precio_acuerdo_embarcacion_confirmado: boolean;
  precio_acuerdo_aceptado: boolean;
  precio_ajuste_pendiente: boolean;
  precio_confirmado: number | null;
  precio_confirmado_por: string | null;
  precio_confirmado_at: string | null;
  descarga_prevista: string | null;
  llegada_planta_prevista: string | null;
  jefe_bahia: string | null;
  encargado_muelle: string | null;
  apuntador: string | null;
  responsable_pesaje_muelle: "APUNTADOR_MUELLE" | "ENCARGADO_MUELLE" | null;
  responsable_pesaje_muelle_cuenta_id: string | null;
  modalidad_pago_cuadrilla: "UNICO" | "DESGLOSE" | null;
  monto_pago_cuadrilla: number | null;
  factura_serie: string | null;
  factura_correlativo: string | null;
  factura_emitida_at: string | null;
  factura_emitida_por: string | null;
  estado_facturacion: string;
  estado: string;
};

type Descarga = { descarga_id: string; embarcacion_id: string; matricula: string; nombre: string; armador: string | null; patron: string | null; peso_declarado_kg: number | null; inicio_descarga: string | null; fin_descarga: string | null };
type Vehiculo = {
  id: string;
  placa: string;
  tipo: string;
  chofer: string;
  estado: string;
  salida_muelle: string | null;
  llegada_planta: string | null;
  turno: string | null;
  fecha_reporte_planta: string | null;
  inicio_planta: string | null;
  fin_planta: string | null;
};
type Archivo = { id: string; tipo: string; etapa: string; nombre: string; vehiculo_id: string | null; estado_revision: "PENDIENTE" | "VERIFICADO" | "OBSERVADO"; observacion_revision: string | null; revisado_por: string | null; revisado_at: string | null; version: number; vigente: boolean; documento_anterior_id: string | null };
type Movimiento = { id: string; operacion_id: string | null; clase: string; pagador: string; beneficiario: string; concepto: string; tipo_gasto: string | null; tipo_comprobante: string | null; motivo_boleta_muelle: string | null; importe: number; moneda: string; registrado_por: string; comprobante_documento_id: string | null; voucher_documento_id: string | null; abonado: number; saldo: number; estado: string };
type Paquete = { vehiculo_id: string; placa: string; documentacion_lista: boolean; faltantes: string[] };
type Resumen = {
  total_peso_muelle_kg: number;
  total_peso_aceptado_planta_kg: number;
  embarcaciones: Array<{
    descarga_id: string;
    nombre: string;
    matricula: string;
    peso_declarado_kg: number | null;
    peso_muelle_total_kg: number;
    cajas_total: number;
  }>;
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
  ["certificado_matricula", "Certificado de matrícula"],
  ["permiso_pesca", "Permiso de pesca"],
  ["certificado_sanipes", "Certificado SANIPES"],
  ["reporte_satelital", "Constancia / reporte satelital"],
  ["visto_bueno_produce", "Visto bueno PRODUCE"],
  ["guia_remitente", "Guía de remisión remitente"],
  ["guia_transportista", "Guía de remisión transportista"],
  ["acta_fiscalizacion", "Acta de fiscalización"],
  ["formato_descarga", "Formato de descarga"],
  ["certificado_procedencia", "Certificado de procedencia"],
  ["certificado_captura", "Certificado de captura"],
  ["factura", "Factura emitida"],
  ["peso_planta", "Peso registrado en planta"],
  ["otro", "Otro documento"],
] as const;
const ETAPAS_DOCUMENTO = [
  ["EMBARCACION", "Embarcación"], ["MUELLE", "Muelle y descarga"],
  ["TRANSPORTE", "Traslado"], ["PLANTA", "Planta procesadora"],
  ["TRAMITADORA", "Tramitadora"], ["FACTURACION", "Facturación"], ["GENERAL", "General"],
] as const;
const ETAPA_TIPO_DOCUMENTO: Record<string, string> = {
  certificado_matricula: "EMBARCACION", permiso_pesca: "EMBARCACION", certificado_sanipes: "EMBARCACION",
  reporte_satelital: "EMBARCACION", visto_bueno_produce: "EMBARCACION", acta_fiscalizacion: "MUELLE",
  formato_descarga: "MUELLE", guia_remitente: "TRANSPORTE", guia_transportista: "TRANSPORTE",
  peso_planta: "PLANTA", certificado_procedencia: "TRAMITADORA", factura: "FACTURACION",
  boleta: "FACTURACION", recibo_honorarios: "FACTURACION",
};

function fechaHoraLocalActual() {
  const fecha = new Date(Date.now() - new Date().getTimezoneOffset() * 60_000);
  return fecha.toISOString().slice(0, 16);
}

function aFechaHoraLocal(valor: string | null) {
  if (!valor) return "";
  const fecha = new Date(valor);
  return new Date(fecha.getTime() - fecha.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}

async function manejar<T>(accion: () => Promise<T>, alExito: () => void, alError: (mensaje: string) => void) {
  try {
    await accion();
    alExito();
  } catch (error) {
    alError(error instanceof Error ? error.message : String(error));
  }
}

export default function Pesca({ sesion }: { sesion: SesionActual }) {
  const esAdministrador = sesion.rol === "ADMINISTRADOR";
  const { datos: rolesAsignados } = useDatos<{ cuenta_id: string; roles: RolPesca[] }>("/api/v1/pesca/roles/mios");
  const roles = rolesAsignados?.roles ?? [];
  const puedeOperar = roles.length > 0;
  const puedeVerPrecios = roles.includes("JEFE_BAHIA") || roles.includes("GERENTE");
  const puedeProponerPrecio = roles.includes("ARMADOR") || roles.includes("PATRON");
  const puedeControlarMuelle = roles.includes("JEFE_BAHIA") || roles.includes("ENCARGADO_MUELLE");
  const puedeCapturarPlanta = roles.includes("APUNTADOR_PLANTA");
  const puedeControlarPlanta = roles.includes("APUNTADOR_PLANTA");
  const puedeLavar = roles.includes("JEFE_CUADRILLA");
  const puedeCajear = roles.includes("JEFE_CUADRILLA");
  const puedeEstibar = roles.includes("JEFE_CUADRILLA");
  const puedeEditarFechasPlanta = puedeControlarPlanta;
  const puedeSubirDocumentos = ["JEFE_BAHIA", "ENCARGADO_MUELLE", "ARMADOR", "PATRON", "APUNTADOR_MUELLE", "APUNTADOR_PLANTA", "SECRETARIA", "TRAMITADORA"].some((rol) => roles.includes(rol as RolPesca));
  const { datos: operaciones, error, cargando, recargar } = useDatos<Operacion[]>(puedeOperar ? "/api/v1/pesca/operaciones" : null);
  const [seleccionada, setSeleccionada] = useState("");
  const [aviso, setAviso] = useState("");
  const op = operaciones?.find((item) => item.id === seleccionada);
  const puedeCapturarMuelle = Boolean(
    op?.responsable_pesaje_muelle &&
    op.responsable_pesaje_muelle_cuenta_id === rolesAsignados?.cuenta_id &&
    roles.includes(op.responsable_pesaje_muelle),
  );
  const base = seleccionada ? `/api/v1/pesca/operaciones/${seleccionada}` : "/api/v1/pesca/operaciones";
  const { datos: descargas, recargar: recargarDescargas } = useDatos<Descarga[]>(seleccionada ? `${base}/embarcaciones` : "");
  const { datos: vehiculos, recargar: recargarVehiculos } = useDatos<Vehiculo[]>(seleccionada ? `${base}/vehiculos` : "");
  const { datos: archivos, recargar: recargarArchivos } = useDatos<Archivo[]>(seleccionada ? `${base}/documentos` : "");
  const { datos: paquetes, recargar: recargarPaquetes } = useDatos<Paquete[]>(seleccionada ? `${base}/documentacion` : "");
  const { datos: resumen, recargar: recargarResumen } = useDatos<Resumen>(seleccionada ? `${base}/resumen` : "");
  const { datos: movimientos, recargar: recargarMovimientos } = useDatos<Movimiento[]>(seleccionada && roles.includes("JEFE_BAHIA") ? `${base}/movimientos` : null);
  const { datos: prestamos, recargar: recargarPrestamos } = useDatos<Movimiento[]>(roles.includes("JEFE_BAHIA") ? "/api/v1/pesca/movimientos-personales" : null);
  const candidatos = useDatos<CuentaCandidata[]>(esAdministrador ? "/api/v1/pesca/roles/candidatos" : null);
  const asignaciones = useDatos<AsignacionPesca[]>(esAdministrador ? "/api/v1/pesca/roles/asignaciones" : null);
  const candidatosPesajeMuelle = useDatos<CuentaResponsablePesaje[]>(seleccionada && roles.includes("JEFE_BAHIA") ? `${base}/responsables-pesaje-muelle/candidatos` : null);
  const asignacionesCuadrilla = useDatos<AsignacionCuadrilla[]>(seleccionada && roles.includes("JEFE_CUADRILLA") ? `${base}/cuadrilla` : null);
  const [cuentaAsignar, setCuentaAsignar] = useState("");
  const [rolAsignar, setRolAsignar] = useState<RolPesca>("JEFE_BAHIA");
  const [actividadAsignar, setActividadAsignar] = useState<ActividadCuadrilla>("LAVADO");
  const [nombreIntegrante, setNombreIntegrante] = useState("");
  const [modoPagoCuadrilla, setModoPagoCuadrilla] = useState<"UNICO" | "DESGLOSE" | null>(null);
  const [responsablePesajeId, setResponsablePesajeId] = useState("");
  const [responsablePesajeRol, setResponsablePesajeRol] = useState<"APUNTADOR_MUELLE" | "ENCARGADO_MUELLE" | "">("");
  const [tipoGasto, setTipoGasto] = useState("MUELLE");
  const [tipoComprobanteGasto, setTipoComprobanteGasto] = useState("factura");
  const [tipoDocumentoCarga, setTipoDocumentoCarga] = useState("certificado_matricula");
  const [etapaDocumentoCarga, setEtapaDocumentoCarga] = useState("EMBARCACION");
  const modalidadCuadrillaActual = modoPagoCuadrilla ?? op?.modalidad_pago_cuadrilla ?? "UNICO";

  const refrescarDetalle = () => {
    recargarDescargas();
    recargarVehiculos();
    recargarArchivos();
    recargarPaquetes();
    recargarResumen();
    recargarMovimientos();
  };

  const registrarMovimiento = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formulario = event.currentTarget;
    const form = new FormData(formulario);
    const clase = String(form.get("clase"));
    void manejar(
      () => enviarJson<Movimiento>("/api/v1/pesca/movimientos", "POST", {
        operacion_id: clase === "prestamo_personal_bahia" ? null : seleccionada,
        clase, pagador: form.get("pagador"), beneficiario: form.get("beneficiario"),
        concepto: form.get("concepto"), importe: Number(form.get("importe")), moneda: form.get("moneda"),
        tipo_gasto: ["gasto_empresa", "gasto_bahia_reembolsable"].includes(clase) ? tipoGasto : null,
        tipo_comprobante: ["gasto_empresa", "gasto_bahia_reembolsable"].includes(clase) ? tipoComprobanteGasto : null,
        motivo_boleta_muelle: tipoGasto === "MUELLE" && tipoComprobanteGasto === "boleta" ? form.get("motivo_boleta_muelle") : null,
        cantidad: form.get("cantidad") ? Number(form.get("cantidad")) : null,
        tarifa_unitaria: form.get("tarifa_unitaria") ? Number(form.get("tarifa_unitaria")) : null,
      }),
      () => { setAviso("Movimiento guardado con trazabilidad."); formulario.reset(); refrescarDetalle(); recargarPrestamos(); }, setAviso,
    );
  };

  const registrarAbono = (event: FormEvent<HTMLFormElement>, movimientoId: string, trasGuardar: () => void) => {
    event.preventDefault();
    const formulario = event.currentTarget;
    const form = new FormData(formulario);
    const data = new FormData();
    data.append("importe", String(form.get("importe")));
    data.append("observacion", String(form.get("observacion") || ""));
    const voucher = form.get("archivo_voucher");
    if (voucher instanceof File && voucher.size) data.append("archivo_voucher", voucher);
    void manejar(
      () => enviarFormulario(`/api/v1/pesca/movimientos/${movimientoId}/abonos`, data),
      () => { setAviso("Devolución o reembolso registrado."); formulario.reset(); trasGuardar(); }, setAviso,
    );
  };

  const adjuntarVoucherMovimiento = (event: FormEvent<HTMLFormElement>, movimientoId: string, trasGuardar: () => void) => {
    event.preventDefault();
    const formulario = event.currentTarget;
    const file = new FormData(formulario).get("archivo");
    if (!(file instanceof File) || !file.size) { setAviso("Selecciona la evidencia del pago."); return; }
    const data = new FormData(); data.append("archivo", file);
    void manejar(
      () => enviarFormulario(`/api/v1/pesca/movimientos/${movimientoId}/voucher`, data),
      () => { setAviso("Voucher de pago adjuntado."); formulario.reset(); trasGuardar(); }, setAviso,
    );
  };

  const adjuntarComprobante = (event: FormEvent<HTMLFormElement>, movimientoId: string, trasGuardar: () => void) => {
    event.preventDefault();
    const formulario = event.currentTarget;
    const file = new FormData(formulario).get("archivo");
    if (!(file instanceof File) || !file.size) { setAviso("Selecciona el comprobante del movimiento."); return; }
    const data = new FormData(); data.append("archivo", file);
    void manejar(
      () => enviarFormulario(`/api/v1/pesca/movimientos/${movimientoId}/comprobante`, data),
      () => { setAviso("Comprobante adjuntado al movimiento."); formulario.reset(); trasGuardar(); }, setAviso,
    );
  };
  const listar = () => {
    recargar();
    refrescarDetalle();
  };

  const guardarRol = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      await enviarJson("/api/v1/pesca/roles/asignaciones", "PUT", { cuenta_id: cuentaAsignar, rol: rolAsignar, activa: true });
      setAviso("Rol pesquero asignado y auditado.");
      asignaciones.recargar();
    } catch (error) {
      setAviso(error instanceof Error ? error.message : String(error));
    }
  };

  const cambiarEstadoRol = async (fila: AsignacionPesca, activa: boolean) => {
    try {
      await enviarJson("/api/v1/pesca/roles/asignaciones", "PUT", { cuenta_id: fila.cuenta_id, rol: fila.rol, activa });
      setAviso(activa ? "Rol pesquero reactivado." : "Rol pesquero desactivado y auditado.");
      asignaciones.recargar();
    } catch (error) {
      setAviso(error instanceof Error ? error.message : String(error));
    }
  };

  const guardarAsignacionCuadrilla = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      const form = new FormData(event.currentTarget);
      await enviarJson(`${base}/cuadrilla`, "PUT", {
        nombre_integrante: nombreIntegrante,
        actividad: actividadAsignar,
        activa: true,
        monto_pago: form.get("monto_pago") ? Number(form.get("monto_pago")) : null,
      });
      setAviso("Integrante registrado por el Jefe de Cuadrilla.");
      setNombreIntegrante("");
      asignacionesCuadrilla.recargar();
    } catch (error) {
      setAviso(error instanceof Error ? error.message : String(error));
    }
  };

  const cambiarAsignacionCuadrilla = async (fila: AsignacionCuadrilla, activa: boolean) => {
    try {
      await enviarJson(`${base}/cuadrilla`, "PUT", { nombre_integrante: fila.nombre_integrante, actividad: fila.actividad, activa, monto_pago: fila.monto_pago });
      setAviso(activa ? "Integrante reactivado." : "Integrante retirado de esta actividad.");
      asignacionesCuadrilla.recargar();
    } catch (error) {
      setAviso(error instanceof Error ? error.message : String(error));
    }
  };

  const configurarPagoCuadrilla = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await enviarJson(`${base}/cuadrilla/pago`, "PUT", {
        modalidad: modalidadCuadrillaActual,
        monto_unico: modalidadCuadrillaActual === "UNICO" && form.get("monto_pago_unico") ? Number(form.get("monto_pago_unico")) : null,
      });
      setAviso("Modalidad de pago de cuadrilla guardada. La entrega se registra como efectivo por el Jefe de Cuadrilla.");
      recargar();
    } catch (error) {
      setAviso(error instanceof Error ? error.message : String(error));
    }
  };

  const crearOperacion = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formulario = event.currentTarget;
    const form = new FormData(formulario);
    void manejar(
      () => enviarJson<Operacion>("/api/v1/pesca/operaciones", "POST", {
        puerto: form.get("puerto"), muelle: form.get("muelle"), planta: form.get("planta"),
        armador_reportante: form.get("armador_reportante") || null,
        comprador: form.get("comprador") || null, remitente: form.get("remitente") || null,
        destinatario: form.get("destinatario") || null, facturador: form.get("facturador") || null,
        toneladas_declaradas: form.get("toneladas_declaradas") ? Number(form.get("toneladas_declaradas")) : null,
        precio_propuesto: form.get("precio_propuesto") ? Number(form.get("precio_propuesto")) : null,
        descarga_prevista: form.get("descarga_prevista") ? new Date(String(form.get("descarga_prevista"))).toISOString() : null,
        llegada_planta_prevista: form.get("llegada_planta_prevista") ? new Date(String(form.get("llegada_planta_prevista"))).toISOString() : null,
        jefe_bahia: form.get("jefe_bahia") || null, encargado_muelle: form.get("encargado_muelle") || null,
        apuntador: form.get("apuntador") || null,
      }),
      () => { setAviso("Operación creada."); formulario.reset(); recargar(); },
      setAviso,
    );
  };

  const confirmarPrecio = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!seleccionada) return;
    const form = new FormData(event.currentTarget);
    const ruta = op?.precio_ajuste_pendiente ? "aceptar-ajuste-precio" : "confirmar-precio";
    void manejar(
      () => enviarJson<Operacion>(`${base}/${ruta}`, "POST", {
        acepta_acuerdo: form.has("acepta_acuerdo"),
      }),
      () => { setAviso(op?.precio_ajuste_pendiente ? "Ajuste de precio aceptado." : "Precio acordado aceptado y bloqueado para esta operación."); recargar(); }, setAviso,
    );
  };

  const confirmarAcuerdoEmbarcacion = () => {
    if (!seleccionada) return;
    void manejar(
      () => enviarJson<Operacion>(`${base}/confirmar-acuerdo-embarcacion`, "POST", { confirma_precio_acordado: true }),
      () => { setAviso("La embarcación confirmó el precio acordado. Queda pendiente la aceptación del Jefe de Bahía o Gerente."); recargar(); },
      setAviso,
    );
  };

  const solicitarAjustePrecio = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!seleccionada) return;
    const form = new FormData(event.currentTarget);
    void manejar(
      () => enviarJson<Operacion>(`${base}/solicitar-ajuste-precio`, "POST", {
        precio_acordado: Number(form.get("precio_acordado")), motivo: form.get("motivo"),
      }),
      () => { setAviso("Ajuste enviado y confirmado por la embarcación. Jefe de Bahía o Gerente debe aceptarlo."); recargar(); },
      setAviso,
    );
  };

  const asignarPesajeMuelle = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!seleccionada) return;
    const cuentaId = responsablePesajeId || op?.responsable_pesaje_muelle_cuenta_id;
    const rol = responsablePesajeRol || op?.responsable_pesaje_muelle;
    if (!cuentaId || !rol) return;
    void manejar(
      () => enviarJson<Operacion>(`${base}/responsable-pesaje-muelle`, "PUT", { rol, cuenta_id: cuentaId }),
      () => { setAviso("Responsable del peso de muelle asignado por Jefe de Bahía."); recargar(); },
      setAviso,
    );
  };

  const iniciarDescarga = () => {
    if (!seleccionada) return;
    void manejar(
      () => enviarJson<Operacion>(`${base}/iniciar-descarga`, "POST"),
      () => { setAviso("Documentos verificados; descarga autorizada."); listar(); }, setAviso,
    );
  };

  const registrarFactura = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!seleccionada) return;
    const form = new FormData(event.currentTarget);
    void manejar(
      () => enviarJson<Operacion>(`${base}/factura`, "POST", {
        serie: form.get("factura_serie"), correlativo: form.get("factura_correlativo"),
      }),
      () => { setAviso("Factura registrada. Adjunta el comprobante para completar el paquete de pago."); listar(); }, setAviso,
    );
  };

  const agregarEmbarcacion = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!seleccionada) return;
    const formulario = event.currentTarget;
    const form = new FormData(formulario);
    void manejar(
      () => enviarJson<Descarga>(`${base}/embarcaciones`, "POST", {
        matricula: form.get("matricula"), nombre: form.get("nombre"), armador: form.get("armador"), patron: form.get("patron"),
        peso_declarado_kg: form.get("peso_declarado_t") ? Number(form.get("peso_declarado_t")) * 1000 : null,
        inicio_descarga: form.get("inicio_descarga") ? new Date(String(form.get("inicio_descarga"))).toISOString() : null,
        fin_descarga: form.get("fin_descarga") ? new Date(String(form.get("fin_descarga"))).toISOString() : null,
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

  const guardarHorasDescarga = (event: FormEvent<HTMLFormElement>, descargaId: string) => {
    event.preventDefault();
    const formulario = event.currentTarget;
    const form = new FormData(formulario);
    const payload: Record<string, unknown> = { observacion: form.get("observacion") };
    const inicio = form.get("inicio_descarga");
    const fin = form.get("fin_descarga");
    if (inicio) payload.inicio_descarga = new Date(String(inicio)).toISOString();
    if (fin) payload.fin_descarga = new Date(String(fin)).toISOString();
    void manejar(
      () => enviarJson(`/api/v1/pesca/descargas/${descargaId}/fechas`, "PATCH", payload),
      () => { setAviso("Horas reales de descarga actualizadas."); refrescarDetalle(); }, setAviso,
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
    data.append("etapa", String(form.get("etapa")));
    const reemplazaId = String(form.get("reemplaza_documento_id"));
    if (reemplazaId) data.append("reemplaza_documento_id", reemplazaId);
    const idVehiculo = String(form.get("vehiculo"));
    if (idVehiculo) data.append("vehiculo_ids", idVehiculo);
    const idEmbarcacion = String(form.get("embarcacion"));
    if (idEmbarcacion) data.append("embarcacion_ids", idEmbarcacion);
    void manejar(
      () => enviarFormulario(`${base}/documentos`, data),
      () => { setAviso("Documento guardado."); formulario.reset(); refrescarDetalle(); recargar(); }, setAviso,
    );
  };

  const revisarArchivo = (event: FormEvent<HTMLFormElement>, documentoId: string) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    const estado = submitter?.value ?? String(form.get("estado"));
    const observacion = estado === "OBSERVADO" ? String(form.get("observacion") ?? "").trim() : "";
    if (estado === "OBSERVADO" && !observacion) { setAviso("Escribe el motivo de la observación."); return; }
    void manejar(
      () => enviarJson(`/api/v1/pesca/documentos/${documentoId}/revision`, "PUT", { estado, observacion: observacion || null }),
      () => { setAviso(estado === "VERIFICADO" ? "Documento verificado." : "Documento observado; indica la corrección y sube una nueva versión."); refrescarDetalle(); },
      setAviso,
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
      {esAdministrador && <section className="pesca-panel pesca-roles-admin">
        <h3>Accesos operativos S.P.T.</h3>
        <p>Asigna a cada cuenta del tenant el actor pesquero que le corresponde. La administración de accesos no autoriza a ver ni decidir precios.</p>
        <form className="pesca-form pesca-form-horizontal" onSubmit={(event) => void guardarRol(event)}>
          <label>Cuenta<select required value={cuentaAsignar} onChange={(event) => setCuentaAsignar(event.target.value)}><option value="">Seleccionar cuenta…</option>{candidatos.datos?.map((cuenta) => <option key={cuenta.cuenta_id} value={cuenta.cuenta_id}>{cuenta.codigo} · {cuenta.nombre}</option>)}</select></label>
          <label>Actor S.P.T.<select value={rolAsignar} onChange={(event) => setRolAsignar(event.target.value as RolPesca)}>{ROLES_PESCA.map(([id, nombre]) => <option key={id} value={id}>{nombre}</option>)}</select></label>
          <button type="submit" disabled={!cuentaAsignar}>Asignar actor</button>
        </form>
        {candidatos.error && <p className="pesca-error">{candidatos.error}</p>}
        {asignaciones.datos?.length ? <ul className="pesca-chips">{asignaciones.datos.map((fila) => <li key={fila.id}><strong>{ROLES_PESCA.find(([id]) => id === fila.rol)?.[1] ?? fila.rol}</strong><small>{fila.codigo} · {fila.nombre} · {fila.activa ? "Activo" : "Inactivo"}</small><button type="button" onClick={() => void cambiarEstadoRol(fila, !fila.activa)}>{fila.activa ? "Desactivar" : "Reactivar"}</button></li>)}</ul> : <p className="muted">Aún no hay actores pesqueros asignados.</p>}
      </section>}
      {!esAdministrador && !puedeOperar && <p className="pesca-aviso">Esta cuenta aún no tiene un actor S.P.T. asignado. Solicita al Administrador del tenant que asigne tu función pesquera.</p>}
      {puedeOperar && <>
      {roles.includes("JEFE_BAHIA") && <details className="pesca-prestamos-personales">
        <summary>Préstamos personales del jefe de bahía <span>Separados de las operaciones y liquidaciones</span></summary>
        <form className="pesca-form pesca-prestamo-form" onSubmit={registrarMovimiento}>
          <input type="hidden" name="clase" value="prestamo_personal_bahia" />
          <label>Prestamista (jefe de bahía)<input name="pagador" required /></label>
          <label>Armador o patrón que recibió<input name="beneficiario" required /></label>
          <label>Motivo<input name="concepto" required /></label>
          <label>Importe<input name="importe" type="number" min="0.01" step="0.01" required /></label>
          <input type="hidden" name="moneda" value="PEN" />
          <button type="submit">Registrar préstamo personal</button>
        </form>
        <div className="pesca-movimientos">
          {!prestamos?.length ? <p className="muted">No hay préstamos personales registrados.</p> : prestamos.map((item) => <article className="pesca-movimiento" key={item.id}>
            <div><strong>{item.beneficiario}</strong><small>{item.concepto} · prestamista: {item.pagador}</small></div>
            <span>{item.moneda} {Number(item.importe).toFixed(2)} · abonado {Number(item.abonado).toFixed(2)} · saldo {Number(item.saldo).toFixed(2)}</span>
            {item.comprobante_documento_id ? <a href={`/api/v1/pesca/documentos/${item.comprobante_documento_id}/archivo`} target="_blank" rel="noreferrer">Ver constancia del préstamo</a> : <form className="pesca-abono-form" onSubmit={(event) => adjuntarComprobante(event, item.id, recargarPrestamos)}><label>Constancia (opcional)<input name="archivo" type="file" accept="application/pdf,image/jpeg,image/png,image/webp" required /></label><button type="submit">Adjuntar constancia</button></form>}
            {item.saldo > 0 && <form className="pesca-abono-form" onSubmit={(event) => registrarAbono(event, item.id, recargarPrestamos)}>
              <label>Registrar abono<input name="importe" type="number" min="0.01" max={item.saldo} step="0.01" required /></label>
              <label>Nota<input name="observacion" /></label><button type="submit">Guardar devolución</button>
            </form>}
          </article>)}
        </div>
      </details>}
      <div className="pesca-columnas">
        <div className="pesca-panel">
          {puedeProponerPrecio && <h3>Nueva operación</h3>}
          {puedeProponerPrecio && <form className="pesca-form" onSubmit={crearOperacion}>
            <label>Puerto<input name="puerto" required placeholder="Paita" /></label>
            <label>Muelle<input name="muelle" required placeholder="Nombre del muelle" /></label>
            <label>Planta de destino<input name="planta" required placeholder="Planta procesadora" /></label>
            <details className="pesca-datos-iniciales"><summary>Datos comerciales y preparación</summary>
              <label>Armador que reporta<input name="armador_reportante" /></label>
              <label>Comprador<input name="comprador" /></label>
              <label>Remitente<input name="remitente" placeholder="Quién emite la guía remitente" /></label>
              <label>Destinatario<input name="destinatario" /></label>
              <label>Facturador (si es distinto)<input name="facturador" /></label>
              <label>Toneladas declaradas<input name="toneladas_declaradas" type="number" min="0" step="0.001" /></label>
              {puedeProponerPrecio && <label>Precio acordado por tonelada (S/), según conversación con Jefe de Bahía o Gerente<input name="precio_propuesto" type="number" min="0.01" step="0.01" /></label>}
              <label>Descarga prevista<input name="descarga_prevista" type="datetime-local" /></label>
              <label>Llegada prevista a planta<input name="llegada_planta_prevista" type="datetime-local" /></label>
              <label>Jefe de bahía<input name="jefe_bahia" /></label>
              <label>Encargado de muelle<input name="encargado_muelle" /></label>
              <label>Apuntador<input name="apuntador" /></label>
            </details>
            <button type="submit">Crear operación de hoy</button>
          </form>}
          <h3>Operaciones recientes</h3>
          {cargando && <p>Cargando operaciones…</p>}
          {error && <p className="pesca-error">{error}</p>}
          {!cargando && !error && !operaciones?.length && <p>Aún no hay operaciones registradas.</p>}
          <div className="pesca-lista">
            {operaciones?.map((item) => (
              <button className={`pesca-op ${seleccionada === item.id ? "seleccionada" : ""}`} type="button" key={item.id} onClick={() => { setSeleccionada(item.id); setModoPagoCuadrilla(null); setResponsablePesajeId(""); setResponsablePesajeRol(""); setAviso(""); }}>
                <span><strong>{item.muelle}</strong><small>{item.puerto} · {new Date(`${item.fecha_reporte}T12:00:00`).toLocaleDateString("es-PE")}</small></span>
                <span className="pesca-estado">{item.estado === "cerrada" ? "Cerrada" : item.estado === "preparacion" ? "Preparación" : "En descarga"}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="pesca-detalle">
          {!op ? <div className="pesca-vacio"><h3>Selecciona una operación</h3><p>Verás aquí sus embarcaciones, vehículos y registro de planta.</p></div> : <>
            <div className="pesca-titulo-detalle"><div><p className="sobrelinea">{op.puerto} · {op.muelle}</p><h3>{op.planta}</h3></div><span className="pesca-estado grande">{op.estado === "cerrada" ? "Cerrada" : op.estado === "preparacion" ? "Preparación" : "En descarga"}</span></div>
            {roles.includes("JEFE_CUADRILLA") && <section className="pesca-control-gastos">
              <h4>Organización de cuadrilla</h4>
              <p>El Jefe de Cuadrilla es el único acceso digital de la cuadrilla: coordina, registra a sus integrantes y controla sus labores. Lavador, Cajeador y Estibador no necesitan cuentas en el sistema.</p>
              <form className="pesca-form pesca-form-horizontal" onSubmit={(event) => void guardarAsignacionCuadrilla(event)}>
                <label>Actividad<select value={actividadAsignar} onChange={(event) => setActividadAsignar(event.target.value as ActividadCuadrilla)}>
                  <option value="LAVADO">Lavador</option><option value="CAJEO">Cajeador</option><option value="ESTIBA">Estibador</option>
                </select></label>
                <label>Nombre del integrante<input required value={nombreIntegrante} onChange={(event) => setNombreIntegrante(event.target.value)} /></label>
                {modalidadCuadrillaActual === "DESGLOSE" && <label>Pago en efectivo asignado (S/)<input name="monto_pago" type="number" min="0.01" step="0.01" required /></label>}
                <button type="submit" disabled={!nombreIntegrante.trim() || op.estado === "cerrada"}>Registrar integrante</button>
              </form>
              <form className="pesca-form pesca-form-horizontal" onSubmit={(event) => void configurarPagoCuadrilla(event)}>
                <label>Forma de pago<select value={modalidadCuadrillaActual} onChange={(event) => setModoPagoCuadrilla(event.target.value as "UNICO" | "DESGLOSE")}><option value="UNICO">Pago único al Jefe de Cuadrilla</option><option value="DESGLOSE">Desglose por Lavador, Cajeador y Estibador</option></select></label>
                {modalidadCuadrillaActual === "UNICO" && <label>Monto único en efectivo (S/)<input name="monto_pago_unico" type="number" min="0.01" step="0.01" defaultValue={op.monto_pago_cuadrilla ?? ""} required /></label>}
                <p>En ambas modalidades, el efectivo se entrega al Jefe de Cuadrilla, quien distribuye según la modalidad elegida.</p>
                <button type="submit" disabled={op.estado === "cerrada"}>Guardar forma de pago</button>
              </form>
              {asignacionesCuadrilla.datos?.length ? <ul className="pesca-chips">{asignacionesCuadrilla.datos.map((fila) => <li key={fila.id}><strong>{fila.actividad}</strong><small>{fila.nombre_integrante} · {fila.activa ? "Activo" : "Inactivo"}{modalidadCuadrillaActual === "DESGLOSE" && fila.monto_pago != null ? ` · S/ ${Number(fila.monto_pago).toFixed(2)} en efectivo` : ""}</small><button type="button" disabled={op.estado === "cerrada"} onClick={() => void cambiarAsignacionCuadrilla(fila, !fila.activa)}>{fila.activa ? "Retirar" : "Reactivar"}</button></li>)}</ul> : <p className="muted">Todavía no hay integrantes registrados.</p>}
            </section>}
            <section className="pesca-resumen-comercial" aria-label="Datos comerciales y responsables">
              <p><strong>Armador reportante:</strong> {op.armador_reportante || "Pendiente"} · <strong>Comprador:</strong> {op.comprador || "Pendiente"}</p>
              <p><strong>Remitente:</strong> {op.remitente || "Pendiente"} · <strong>Destinatario:</strong> {op.destinatario || "Pendiente"} · <strong>Facturador:</strong> {op.facturador || "Mismo remitente"}</p>
              <p><strong>Toneladas declaradas:</strong> {op.toneladas_declaradas ?? "Pendiente"}{puedeVerPrecios && <> · <strong>Precio ingresado por embarcación:</strong> {op.precio_propuesto == null ? "Pendiente" : `S/ ${Number(op.precio_propuesto).toFixed(2)}/t`}</>}</p>
              <p><strong>Descarga prevista:</strong> {op.descarga_prevista ? new Date(op.descarga_prevista).toLocaleString("es-PE") : "Pendiente"} · <strong>Llegada prevista a planta:</strong> {op.llegada_planta_prevista ? new Date(op.llegada_planta_prevista).toLocaleString("es-PE") : "Pendiente"}</p>
              <p><strong>Jefe de bahía:</strong> {op.jefe_bahia || "—"} · <strong>Encargado:</strong> {op.encargado_muelle || "—"} · <strong>Apuntador:</strong> {op.apuntador || "—"}</p>
            </section>
            {roles.includes("JEFE_BAHIA") && <form className="pesca-form pesca-form-horizontal" onSubmit={asignarPesajeMuelle}>
              <label>Persona responsable del peso de cajas en muelle<select required value={`${responsablePesajeId || op.responsable_pesaje_muelle_cuenta_id || ""}|${responsablePesajeRol || op.responsable_pesaje_muelle || ""}`} onChange={(event) => {
                const [cuentaId, rol] = event.target.value.split("|");
                setResponsablePesajeId(cuentaId ?? "");
                setResponsablePesajeRol((rol === "APUNTADOR_MUELLE" || rol === "ENCARGADO_MUELLE") ? rol : "");
              }}><option value="|">Seleccionar responsable…</option>{(candidatosPesajeMuelle.datos ?? []).map((item) => <option key={`${item.cuenta_id}-${item.rol}`} value={`${item.cuenta_id}|${item.rol}`}>{item.codigo} · {item.nombre} · {item.rol === "APUNTADOR_MUELLE" ? "Apuntador de Muelle" : "Encargado de Muelle"}</option>)}</select></label>
              <button type="submit" disabled={!(responsablePesajeId || op.responsable_pesaje_muelle_cuenta_id) || !(responsablePesajeRol || op.responsable_pesaje_muelle)}>Asignar responsable de pesaje</button>
              {candidatosPesajeMuelle.error && <p className="pesca-error">{candidatosPesajeMuelle.error}</p>}
              <small>Solo la cuenta elegida por Jefe de Bahía podrá registrar pesos y totales de la embarcación en muelle.</small>
            </form>}
            {puedeProponerPrecio && op.estado === "preparacion" && !op.precio_acuerdo_embarcacion_confirmado && <div className="pesca-autorizacion-descarga">
              <strong>Confirmación de la embarcación</strong>
              <span>Después de acordar el precio con Jefe de Bahía o Gerente, confirma que el precio que ingresaste corresponde a ese acuerdo.</span>
              <button type="button" disabled={op.precio_propuesto == null || op.precio_propuesto <= 0} onClick={confirmarAcuerdoEmbarcacion}>Confirmar precio acordado</button>
            </div>}
            {puedeProponerPrecio && op.precio_acuerdo_embarcacion_confirmado && <p className="pesca-precio-bloqueado">{op.precio_ajuste_pendiente ? "Ajuste de precio confirmado por la embarcación; pendiente de aceptación de Jefe de Bahía o Gerente." : op.precio_acuerdo_aceptado ? "El Jefe de Bahía o Gerente aceptó el precio acordado." : "La embarcación confirmó el precio acordado. Pendiente de aceptación del Jefe de Bahía o Gerente."}</p>}
            {puedeProponerPrecio && op.precio_acuerdo_aceptado && op.estado === "preparacion" && !op.precio_ajuste_pendiente && <form className="pesca-form pesca-confirmar-precio" onSubmit={solicitarAjustePrecio}>
              <h4>Solicitar ajuste del precio</h4>
              <p>Si luego de coordinar un nuevo monto con Jefe de Bahía o Gerente se debe corregir el precio, ingresa el nuevo acuerdo y su motivo. El precio vigente seguirá siendo el aceptado hasta que la jefatura apruebe el cambio.</p>
              <label>Nuevo precio acordado por tonelada (S/)<input name="precio_acordado" type="number" min="0.01" step="0.01" required /></label>
              <label>Motivo del ajuste<textarea name="motivo" minLength={5} maxLength={1000} required /></label>
              <button type="submit">Confirmar y solicitar ajuste</button>
            </form>}
            {puedeVerPrecios && op.estado === "preparacion" && (op.precio_ajuste_pendiente || (!op.precio_acuerdo_aceptado && op.precio_acuerdo_embarcacion_confirmado)) && <form className="pesca-form pesca-confirmar-precio" onSubmit={confirmarPrecio}>
              <h4>{op.precio_ajuste_pendiente ? "Aceptar ajuste de precio" : "Aceptar acuerdo de precio"}</h4>
              <p>{op.precio_ajuste_pendiente ? <>La embarcación solicita cambiar de S/ {Number(op.precio_confirmado).toFixed(2)}/t a S/ {Number(op.precio_propuesto).toFixed(2)}/t.</> : <>La embarcación ingresó y confirmó S/ {op.precio_propuesto == null ? "—" : `${Number(op.precio_propuesto).toFixed(2)}/t`} después de coordinarlo con Jefe de Bahía o Gerente.</>}</p>
              <label><input name="acepta_acuerdo" type="checkbox" required /> Acepto el mismo precio acordado y confirmado por la embarcación</label>
              <button type="submit">{op.precio_ajuste_pendiente ? "Aceptar ajuste de precio" : "Aceptar acuerdo de precio"}</button>
            </form>}
            {puedeVerPrecios && op.estado === "preparacion" && !op.precio_acuerdo_embarcacion_confirmado && !op.precio_acuerdo_aceptado && <p className="pesca-precio-bloqueado">A la espera de que el Patrón o Armador ingrese y confirme el precio acordado.</p>}
            {puedeVerPrecios && op.precio_acuerdo_aceptado && !op.precio_ajuste_pendiente && <p className="pesca-precio-bloqueado"><strong>Precio aceptado:</strong> S/ {Number(op.precio_confirmado).toFixed(2)}/t · aceptó: {op.precio_confirmado_por} · {op.precio_confirmado_at ? new Date(op.precio_confirmado_at).toLocaleString("es-PE") : ""}</p>}
            {puedeControlarMuelle && op.estado === "preparacion" && <div className="pesca-autorizacion-descarga">
              <strong>Antes de iniciar la descarga, sube:</strong>
              <span>matrícula · permiso de pesca · SANIPES · satelital · visto bueno PRODUCE · guía remitente</span>
              <button type="button" onClick={iniciarDescarga}>Verificar documentos e iniciar descarga</button>
            </div>}
            <div className="pesca-metricas"><div><small>Peso declarado</small><strong>{op.toneladas_declaradas == null ? "—" : `${Number(op.toneladas_declaradas).toFixed(3)} t`}</strong></div><div><small>Peso muelle</small><strong>{((resumen?.total_peso_muelle_kg ?? 0) / 1000).toFixed(3)} t</strong></div><div><small>Peso aceptado planta</small><strong>{((resumen?.total_peso_aceptado_planta_kg ?? 0) / 1000).toFixed(3)} t</strong></div><div><small>Vehículos</small><strong>{vehiculos?.length ?? 0}</strong></div></div>
            {Boolean(resumen?.embarcaciones?.length) && <section className="pesca-resumen-comercial" aria-label="Totales de peso apuntados por embarcación">
              <h4>Totales de muelle por embarcación</h4>
              {resumen?.embarcaciones.map((item) => <p key={item.descarga_id}><strong>{item.nombre} · {item.matricula}</strong> — Declarado: {item.peso_declarado_kg == null ? "—" : `${(Number(item.peso_declarado_kg) / 1000).toFixed(3)} t`} · Apuntado en muelle: {(Number(item.peso_muelle_total_kg) / 1000).toFixed(3)} t · Cajas: {item.cajas_total}</p>)}
            </section>}
            {roles.includes("JEFE_BAHIA") && <section className="pesca-control-gastos">
              <h4>Gastos y adelantos de esta operación</h4>
              <p>Los gastos pagados por la empresa, los montos que el jefe de bahía puso de su bolsillo y los adelantos al armador se concilian aquí. Los préstamos personales se controlan en su registro independiente.</p>
              <form className="pesca-form pesca-movimiento-form" onSubmit={registrarMovimiento}>
                <label>Tipo<select name="clase"><option value="gasto_empresa">Gasto pagado por la empresa</option><option value="gasto_bahia_reembolsable">Gasto de operación pagado por jefe de bahía</option><option value="adelanto_armador_empresa">Adelanto de la empresa al armador</option></select></label>
                <label>Concepto del gasto<select value={tipoGasto} onChange={(event) => {
                  const valor = event.target.value;
                  setTipoGasto(valor);
                  setTipoComprobanteGasto(valor === "CUADRILLA" || valor === "APUNTADOR" ? "recibo_honorarios" : "factura");
                }}><option value="MUELLE">Servicio de muelle</option><option value="HIELO">Hielo</option><option value="FLETE">Flete</option><option value="CUADRILLA">Cuadrilla</option><option value="APUNTADOR">Apuntador</option><option value="OTRO">Otro servicio</option></select></label>
                <label>CPE de respaldo<select value={tipoComprobanteGasto} onChange={(event) => setTipoComprobanteGasto(event.target.value)}>
                  {(tipoGasto === "CUADRILLA" || tipoGasto === "APUNTADOR") ? <option value="recibo_honorarios">Recibo por Honorarios Electrónico</option> : tipoGasto === "MUELLE" ? <><option value="factura">Factura</option><option value="boleta">Boleta (solo si el muelle no emite factura)</option></> : tipoGasto === "OTRO" ? <><option value="factura">Factura</option><option value="recibo_honorarios">Recibo por Honorarios Electrónico</option></> : <option value="factura">Factura</option>}
                </select></label>
                {tipoGasto === "MUELLE" && tipoComprobanteGasto === "boleta" && <label>Motivo por el que el muelle no emite factura<input name="motivo_boleta_muelle" required /></label>}
                <label>Pagador<input name="pagador" required placeholder="Empresa o jefe de bahía" /></label>
                <label>Beneficiario / proveedor<input name="beneficiario" required /></label>
                <label>Concepto<input name="concepto" required placeholder="Hielo, cuadrilla, flete…" /></label>
                <label>Importe<input name="importe" type="number" min="0.01" step="0.01" required /></label>
                <label>Moneda<select name="moneda"><option value="PEN">Soles</option><option value="USD">Dólares</option></select></label>
                <label>Cantidad (opcional)<input name="cantidad" type="number" min="0.001" step="0.001" /></label>
                <label>Tarifa unitaria (opcional)<input name="tarifa_unitaria" type="number" min="0" step="0.01" /></label>
                <button type="submit">Guardar movimiento de la operación</button>
              </form>
              <div className="pesca-movimientos">
                {!movimientos?.length ? <p className="muted">Aún no hay gastos ni adelantos registrados.</p> : movimientos.map((item) => <article className="pesca-movimiento" key={item.id}>
                  <div><strong>{item.concepto}</strong><small>{item.clase.replaceAll("_", " ")} · {item.beneficiario} · pagó: {item.pagador}</small></div>
                  <span>{item.moneda} {Number(item.importe).toFixed(2)} · saldo {Number(item.saldo).toFixed(2)} · {item.estado.replaceAll("_", " ")}</span>
                  {item.comprobante_documento_id ? <a href={`/api/v1/pesca/documentos/${item.comprobante_documento_id}/archivo`} target="_blank" rel="noreferrer">Ver CPE ({item.tipo_comprobante?.replaceAll("_", " ") ?? "constancia"})</a> : <form className="pesca-abono-form" onSubmit={(event) => adjuntarComprobante(event, item.id, recargarMovimientos)}><label>{item.tipo_comprobante ? `Adjuntar CPE requerido (${item.tipo_comprobante.replaceAll("_", " ")})` : "Constancia o documento de sustento"}<input name="archivo" type="file" accept="application/pdf,image/jpeg,image/png,image/webp" required /></label><button type="submit">Adjuntar documento</button></form>}
                  {item.clase !== "prestamo_personal_bahia" && (item.voucher_documento_id ? <a href={`/api/v1/pesca/documentos/${item.voucher_documento_id}/archivo`} target="_blank" rel="noreferrer">Ver evidencia del pago</a> : <form className="pesca-abono-form" onSubmit={(event) => adjuntarVoucherMovimiento(event, item.id, recargarMovimientos)}><label>Voucher de pago requerido<input name="archivo" type="file" accept="application/pdf,image/jpeg,image/png,image/webp" required /></label><button type="submit">Adjuntar voucher</button></form>)}
                  {item.saldo > 0 && item.clase !== "gasto_empresa" && (item.clase !== "gasto_bahia_reembolsable" || item.comprobante_documento_id) && <form className="pesca-abono-form" onSubmit={(event) => registrarAbono(event, item.id, recargarMovimientos)}>
                    <label>Devolución / reembolso<input name="importe" type="number" min="0.01" max={item.saldo} step="0.01" required /></label>
                    {item.clase !== "prestamo_personal_bahia" && <label>Voucher de este abono<input name="archivo_voucher" type="file" accept="application/pdf,image/jpeg,image/png,image/webp" required /></label>}
                    <label>Nota de conciliación<input name="observacion" /></label><button type="submit">Registrar abono</button>
                  </form>}
                </article>)}
              </div>
            </section>}
            <div className="pesca-subpaneles">
              {puedeProponerPrecio && op.estado === "preparacion" && <form className="pesca-form pesca-form-horizontal" onSubmit={agregarEmbarcacion}>
                <h4>Vincular embarcación</h4>
                <label>Matrícula<input name="matricula" required /></label><label>Nombre<input name="nombre" required /></label>
                <label>Armador<input name="armador" required /></label><label>Patrón<input name="patron" required /></label>
                <label>Peso declarado (ton)<input name="peso_declarado_t" type="number" min="0" step="0.001" /></label>
                <label>Inicio real de descarga<input name="inicio_descarga" type="datetime-local" /></label>
                <label>Fin real de descarga<input name="fin_descarga" type="datetime-local" /></label>
                <label>Intermediario (opcional)<input name="intermediario" /></label>
                <button type="submit">Agregar embarcación</button>
              </form>}
              {puedeControlarMuelle && ["preparacion", "en_descarga"].includes(op.estado) && <form className="pesca-form pesca-form-horizontal" onSubmit={agregarVehiculo}>
                <h4>Agregar vehículo</h4><label>Placa<input name="placa" required /></label>
                <label>Tipo<input name="tipo" required placeholder="3 ejes, carreta…" /></label><label>Chofer<input name="chofer" required /></label>
                <label>Turno de planta (si existe)<input name="turno" /></label><button type="submit">Agregar vehículo</button>
              </form>}
            </div>

            <h4>Embarcaciones vinculadas</h4>
            {descargas?.length ? <ul className="pesca-chips">{descargas.map((d) => <li key={d.descarga_id}><strong>{d.nombre}</strong><small>{d.matricula} · Armador: {d.armador || "—"} · Patrón: {d.patron || "—"} · Declarado: {d.peso_declarado_kg == null ? "—" : `${(Number(d.peso_declarado_kg) / 1000).toFixed(3)} t`}</small><small>Descarga real: {d.inicio_descarga ? new Date(d.inicio_descarga).toLocaleString("es-PE") : "—"} a {d.fin_descarga ? new Date(d.fin_descarga).toLocaleString("es-PE") : "—"}</small>{(roles.includes("ENCARGADO_MUELLE") || roles.includes("APUNTADOR_MUELLE")) && <details><summary>Editar horas reales (requiere motivo)</summary><form className="pesca-form" onSubmit={(event) => guardarHorasDescarga(event, d.descarga_id)}><label>Inicio real<input name="inicio_descarga" type="datetime-local" defaultValue={aFechaHoraLocal(d.inicio_descarga)} /></label><label>Fin real<input name="fin_descarga" type="datetime-local" defaultValue={aFechaHoraLocal(d.fin_descarga)} /></label><label>Motivo / nota<input name="observacion" required /></label><button type="submit">Guardar horas</button></form></details>}</li>)}</ul> : <p className="muted">Agrega la primera embarcación.</p>}

            <h4>Vehículos y recepción en planta</h4>
            {!vehiculos?.length ? <p className="muted">Agrega un vehículo para iniciar el seguimiento.</p> : <div className="pesca-vehiculos">{vehiculos.map((v) => {
              const linea = resumen?.vehiculos.find((x) => x.vehiculo_id === v.id);
              const paquete = paquetes?.find((x) => x.vehiculo_id === v.id);
              return <VehiculoCard key={v.id} operationId={seleccionada} vehicle={v} descargas={descargas ?? []} linea={linea} paquete={paquete} puedeCapturarMuelle={puedeCapturarMuelle} puedeCapturarPlanta={puedeCapturarPlanta} puedeEditarFechasPlanta={puedeEditarFechasPlanta} puedeControlarPlanta={puedeControlarPlanta} puedeControlarMuelle={puedeControlarMuelle} puedeLavar={puedeLavar} puedeCajear={puedeCajear} puedeEstibar={puedeEstibar} alGuardar={() => { setAviso("Datos de vehículo actualizados."); refrescarDetalle(); }} alError={setAviso} />;
            })}</div>}

            {puedeSubirDocumentos && <form className="pesca-form pesca-doc-upload" onSubmit={subirArchivo}>
              <h4>Documentación de la operación</h4>
              <label>Tipo de documento<select name="tipo" value={tipoDocumentoCarga} onChange={(event) => { const tipo = event.target.value; setTipoDocumentoCarga(tipo); setEtapaDocumentoCarga(ETAPA_TIPO_DOCUMENTO[tipo] ?? "GENERAL"); }}>{DOCUMENTOS.map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>
              <label>Etapa<select name="etapa" value={etapaDocumentoCarga} onChange={(event) => setEtapaDocumentoCarga(event.target.value)}>{ETAPAS_DOCUMENTO.map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>
              <label>Vincular a<select name="vehiculo"><option value="">Toda la operación</option>{vehiculos?.map((v) => <option key={v.id} value={v.id}>{v.placa} · {v.chofer}</option>)}</select></label>
              <label>Vincular certificado a embarcación<select name="embarcacion"><option value="">Documento general / del vehículo</option>{descargas?.map((d) => <option key={d.descarga_id} value={d.embarcacion_id}>{d.nombre} · {d.matricula}</option>)}</select></label>
              <label>Reemplaza documento vigente (opcional)<select name="reemplaza_documento_id"><option value="">Es un documento nuevo</option>{archivos?.filter((a) => a.vigente).map((a) => <option key={a.id} value={a.id}>{a.tipo.replaceAll("_", " ")} · {a.nombre} · v{a.version}</option>)}</select></label>
              <small>El certificado de procedencia debe subirse para toda la operación, sin vincularlo a un vehículo ni a una embarcación.</small>
              <label>Foto o archivo (PDF/JPG/PNG/WEBP)<input name="archivo" type="file" accept="application/pdf,image/jpeg,image/png,image/webp" required /></label>
              <button type="submit">Subir documento</button>
            </form>}
            <div className="pesca-documentacion"><strong>Documentación por vehículo</strong>{paquetes?.map((p) => <p key={p.vehiculo_id}><span>{p.placa}</span>{p.documentacion_lista ? <b className="texto-verde">Lista para presentar</b> : <small>Falta: {p.faltantes.join(", ")}</small>}</p>)}</div>
            {op.estado === "cerrada" && <section className="pesca-facturacion">
              <h4>Factura y expediente para pago</h4>
              {roles.includes("SECRETARIA") && op.estado_facturacion === "pendiente" ? <form className="pesca-form pesca-factura-form" onSubmit={registrarFactura}>
                <label>Serie<input name="factura_serie" required placeholder="F001" /></label>
                <label>Correlativo<input name="factura_correlativo" required /></label>
                <button type="submit">Registrar factura emitida</button>
              </form> : <p>Factura {op.factura_serie}-{op.factura_correlativo} · {op.estado_facturacion.replaceAll("_", " ")}</p>}
              {roles.includes("SECRETARIA") && op.estado_facturacion === "pendiente_documento" && <p className="pesca-pendiente-doc">Sube ahora el archivo de la factura en “Documentación de la operación”, con tipo “Factura emitida”.</p>}
              {op.estado_facturacion === "lista_para_pago" && <p className="texto-verde"><strong>Paquete listo para presentar a pago.</strong></p>}
            </section>}
            <details className="pesca-archivos"><summary>Expediente documental · {archivos?.filter((a) => a.vigente).length ?? 0} vigentes</summary><ul>{archivos?.map((a) => <li key={a.id} className={a.vigente ? "" : "pesca-documento-reemplazado"}>
              <div><strong>{a.tipo.replaceAll("_", " ")}</strong> · {ETAPAS_DOCUMENTO.find(([id]) => id === a.etapa)?.[1] ?? a.etapa} · v{a.version}{!a.vigente && " · reemplazado"}<br /><a href={`/api/v1/pesca/documentos/${a.id}/archivo`} target="_blank" rel="noreferrer">{a.nombre}</a><br /><small>Estado: {a.vigente ? a.estado_revision.toLowerCase() : "versión anterior"}{a.revisado_por ? ` · revisó ${a.revisado_por}` : ""}{a.observacion_revision ? ` · Observación: ${a.observacion_revision}` : ""}</small></div>
              {roles.includes("JEFE_BAHIA") && a.vigente && <form className="pesca-revision-documento" onSubmit={(event) => revisarArchivo(event, a.id)}>
                <input name="observacion" aria-label="Motivo de observación" placeholder="Motivo si se observa" />
                <button type="submit" name="estado" value="VERIFICADO">Verificar</button>
                <button type="submit" name="estado" value="OBSERVADO">Observar</button>
              </form>}
            </li>)}</ul></details>
            {roles.includes("JEFE_BAHIA") && op.estado !== "cerrada" && <button className="pesca-cerrar-op" type="button" disabled={!vehiculos?.length || vehiculos.some((v) => v.estado !== "cerrado")} onClick={cerrarOperacion}>Cerrar operación del día</button>}
          </>}
        </div>
      </div>
      </>}
    </section>
  );
}

type VehiculoLinea = Resumen["vehiculos"][number];
function VehiculoCard({ operationId, vehicle, descargas, linea, paquete, puedeCapturarMuelle, puedeCapturarPlanta, puedeEditarFechasPlanta, puedeControlarPlanta, puedeControlarMuelle, puedeLavar, puedeCajear, puedeEstibar, alGuardar, alError }: {
  operationId: string; vehicle: Vehiculo; descargas: Descarga[]; linea?: VehiculoLinea; paquete?: Paquete;
  puedeCapturarMuelle: boolean; puedeCapturarPlanta: boolean; puedeEditarFechasPlanta: boolean; puedeControlarPlanta: boolean; puedeControlarMuelle: boolean;
  puedeLavar: boolean; puedeCajear: boolean; puedeEstibar: boolean;
  alGuardar: () => void; alError: (mensaje: string) => void;
}) {
  const [peso, setPeso] = useState(linea?.peso_aceptado?.toString() ?? "");
  const [unidad, setUnidad] = useState(linea?.unidad ?? "ton");
  const [resultado, setResultado] = useState(linea?.resultado_planta === "pendiente" ? "completo" : linea?.resultado_planta ?? "completo");
  const [cajas, setCajas] = useState("0");
  const [motivo, setMotivo] = useState("");
  const [observacionPeso, setObservacionPeso] = useState("");
  const [foto, setFoto] = useState<File | null>(null);
  const [esperando, setEsperando] = useState(false);
  const [sinFechaFinal, setSinFechaFinal] = useState(false);
  const [descargaId, setDescargaId] = useState(descargas[0]?.descarga_id ?? "");
  const [pesoMuelle, setPesoMuelle] = useState("");
  const [cajasMuelle, setCajasMuelle] = useState("");
  const [inicio, setInicio] = useState(false);
  const [fechaReporte, setFechaReporte] = useState(vehicle.fecha_reporte_planta ?? "");
  const [llegadaManual, setLlegadaManual] = useState(aFechaHoraLocal(vehicle.llegada_planta));
  const [inicioManual, setInicioManual] = useState(aFechaHoraLocal(vehicle.inicio_planta));
  const [finManual, setFinManual] = useState(aFechaHoraLocal(vehicle.fin_planta));
  const [observacionFechas, setObservacionFechas] = useState("");
  const [fechaFinalPeso, setFechaFinalPeso] = useState(fechaHoraLocalActual);
  const { datos: actividades, recargar: recargarActividades } = useDatos<RegistroActividad[]>(
    (puedeLavar || puedeCajear || puedeEstibar) ? `/api/v1/pesca/vehiculos/${vehicle.id}/actividades` : null,
  );
  const registroActividad = (actividad: string) => actividades?.find((item) => item.actividad === actividad);
  const guardarActividad = (event: FormEvent<HTMLFormElement>, actividad: "LAVADO" | "CAJEO" | "ESTIBA") => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const existente = registroActividad(actividad);
    if (existente && !form.get("observacion")) { alError("Explica el cambio de la tarea en observaciones."); return; }
    void manejar(
      () => enviarJson(`/api/v1/pesca/vehiculos/${vehicle.id}/actividades`, "PUT", {
        actividad,
        estado: form.get("estado"),
        cajas: form.get("cajas") ? Number(form.get("cajas")) : null,
        hielo_kg: form.get("hielo_kg") ? Number(form.get("hielo_kg")) : null,
        verificacion_visual: actividad === "LAVADO" ? form.has("verificacion_visual") : null,
        contaminacion_detectada: actividad === "CAJEO" ? form.has("contaminacion_detectada") : null,
        revision_final: actividad === "ESTIBA" ? form.has("revision_final") : null,
        observacion: form.get("observacion") || null,
      }),
      () => { alGuardar(); recargarActividades(); },
      alError,
    );
  };
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
  const iniciarTraslado = async () => {
    setInicio(true);
    try { await enviarJson(`/api/v1/pesca/vehiculos/${vehicle.id}/traslado/iniciar`, "POST"); alGuardar(); }
    catch (error) { alError(error instanceof Error ? error.message : String(error)); }
    finally { setInicio(false); }
  };
  const iniciarPlanta = async () => {
    setInicio(true);
    try { await enviarJson(`/api/v1/pesca/vehiculos/${vehicle.id}/planta/iniciar`, "POST"); alGuardar(); }
    catch (error) { alError(error instanceof Error ? error.message : String(error)); }
    finally { setInicio(false); }
  };
  const iniciarDescargaPlanta = async () => {
    setInicio(true);
    try { await enviarJson(`/api/v1/pesca/vehiculos/${vehicle.id}/planta/descarga/iniciar`, "POST"); alGuardar(); }
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
        llegada_planta: llegadaManual ? new Date(llegadaManual).toISOString() : null,
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
        observacion: observacionPeso || null,
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
    <div className="pesca-vehiculo-meta">
      <span>Turno: {vehicle.turno || "Sin turno"}</span><span>{descargas.length} embarcaciones vinculadas</span>
      {vehicle.salida_muelle && <span>Salió del muelle: {new Date(vehicle.salida_muelle).toLocaleString("es-PE")}</span>}
      {vehicle.llegada_planta && <span>Llegó a planta: {new Date(vehicle.llegada_planta).toLocaleString("es-PE")}</span>}
      {vehicle.inicio_planta && <span>Inició descarga: {new Date(vehicle.inicio_planta).toLocaleString("es-PE")}</span>}
      {vehicle.fin_planta && <span>Terminó descarga: {new Date(vehicle.fin_planta).toLocaleString("es-PE")}</span>}
    </div>
    {actividades?.length ? <ul className="pesca-chips">{actividades.map((item) => <li key={item.id}><strong>{item.actividad} · {item.estado.replaceAll("_", " ")}</strong><small>{item.cajas == null ? "" : `${item.cajas} cajas · `}{item.hielo_kg == null ? "" : `${item.hielo_kg} kg de hielo · `}{item.observacion || "Sin observación"}</small></li>)}</ul> : null}
    {puedeLavar && <form key={registroActividad("LAVADO")?.updated_at ?? "lavado-nuevo"} className="pesca-form pesca-form-horizontal" onSubmit={(event) => guardarActividad(event, "LAVADO")}>
      <h4>Lavado y revisión visual</h4><label>Estado<select name="estado" defaultValue={registroActividad("LAVADO")?.estado ?? "EN_PROCESO"}><option value="EN_PROCESO">En proceso</option><option value="COMPLETA">Completa</option><option value="INCIDENCIA">Incidencia</option></select></label>
      <label>Hielo utilizado (kg)<input name="hielo_kg" type="number" min="0" step="0.001" defaultValue={registroActividad("LAVADO")?.hielo_kg ?? ""} /></label>
      <label className="pesca-checkbox"><input name="verificacion_visual" type="checkbox" defaultChecked={registroActividad("LAVADO")?.verificacion_visual ?? false} /> Revisión visual satisfactoria</label>
      <label>Observación<input name="observacion" required={Boolean(registroActividad("LAVADO"))} /></label><button type="submit">Guardar tarea de lavado</button>
    </form>}
    {puedeCajear && <form key={registroActividad("CAJEO")?.updated_at ?? "cajeo-nuevo"} className="pesca-form pesca-form-horizontal" onSubmit={(event) => guardarActividad(event, "CAJEO")}>
      <h4>Cajeo y control de contaminación</h4><label>Estado<select name="estado" defaultValue={registroActividad("CAJEO")?.estado ?? "EN_PROCESO"}><option value="EN_PROCESO">En proceso</option><option value="COMPLETA">Completa</option><option value="INCIDENCIA">Incidencia</option></select></label>
      <label>Cajas cargadas<input name="cajas" type="number" min="0" step="1" required defaultValue={registroActividad("CAJEO")?.cajas ?? ""} /></label>
      <label className="pesca-checkbox"><input name="contaminacion_detectada" type="checkbox" defaultChecked={registroActividad("CAJEO")?.contaminacion_detectada ?? false} /> Se detectó contaminación</label>
      <label>Observación<input name="observacion" required={Boolean(registroActividad("CAJEO"))} /></label><button type="submit">Guardar cajeo</button>
    </form>}
    {puedeEstibar && <form key={registroActividad("ESTIBA")?.updated_at ?? "estiba-nueva"} className="pesca-form pesca-form-horizontal" onSubmit={(event) => guardarActividad(event, "ESTIBA")}>
      <h4>Estiba y revisión final</h4><label>Estado<select name="estado" defaultValue={registroActividad("ESTIBA")?.estado ?? "EN_PROCESO"}><option value="EN_PROCESO">En proceso</option><option value="COMPLETA">Completa</option><option value="INCIDENCIA">Incidencia</option></select></label>
      <label>Cajas estibadas<input name="cajas" type="number" min="0" step="1" required defaultValue={registroActividad("ESTIBA")?.cajas ?? ""} /></label>
      <label>Hielo utilizado (kg)<input name="hielo_kg" type="number" min="0" step="0.001" required defaultValue={registroActividad("ESTIBA")?.hielo_kg ?? ""} /></label>
      <label className="pesca-checkbox"><input name="revision_final" type="checkbox" defaultChecked={registroActividad("ESTIBA")?.revision_final ?? false} /> Revisión final satisfactoria</label>
      <label>Observación<input name="observacion" required={Boolean(registroActividad("ESTIBA"))} /></label><button type="submit">Guardar estiba</button>
    </form>}
    {puedeControlarMuelle && vehicle.estado === "pendiente_muelle" && <button type="button" className="pesca-secundario" disabled={inicio} onClick={() => void iniciarTraslado()}>{inicio ? "Registrando…" : "Despachar a planta (verificar carga y documentos)"}</button>}
    {puedeControlarPlanta && vehicle.estado === "en_traslado" && <button type="button" className="pesca-secundario" disabled={inicio} onClick={() => void iniciarPlanta()}>{inicio ? "Registrando…" : "Registrar llegada real a planta"}</button>}
    {puedeControlarPlanta && vehicle.estado === "en_planta" && !vehicle.inicio_planta && <button type="button" className="pesca-secundario" disabled={inicio} onClick={() => void iniciarDescargaPlanta()}>{inicio ? "Registrando…" : "Iniciar descarga real en planta"}</button>}
    {puedeEditarFechasPlanta && ["en_planta", "pendiente_evidencia"].includes(vehicle.estado) && <details className="pesca-fechas"><summary>Fechas y horas de planta</summary><form className="pesca-form pesca-fechas-form" onSubmit={(event) => void guardarFechas(event)}>
      <label>Fecha de reporte<input type="date" value={fechaReporte} onChange={(e) => setFechaReporte(e.target.value)} /></label>
      <label>Llegada real a planta<input type="datetime-local" value={llegadaManual} onChange={(e) => setLlegadaManual(e.target.value)} /></label>
      <label>Inicio real de descarga<input type="datetime-local" value={inicioManual} onChange={(e) => setInicioManual(e.target.value)} /></label>
      <label>Fin de descarga<input type="datetime-local" value={finManual} onChange={(e) => setFinManual(e.target.value)} /></label>
      <label>Motivo del ajuste<input value={observacionFechas} onChange={(e) => setObservacionFechas(e.target.value)} required /></label>
      <button type="submit" disabled={esperando}>Guardar fechas</button>
    </form></details>}
    {puedeCapturarMuelle && vehicle.estado === "pendiente_muelle" && <form className="pesca-form pesca-carga-form" onSubmit={(event) => void asignarCarga(event)}>
      <strong>Asignar carga desde muelle</strong>
      <label>Embarcación<select value={descargaId} onChange={(e) => setDescargaId(e.target.value)} required><option value="">Seleccionar…</option>{descargas.map((d) => <option key={d.descarga_id} value={d.descarga_id}>{d.nombre} · {d.matricula}</option>)}</select></label>
      <label>Peso de muelle (kg)<input type="number" min="0" step="0.001" value={pesoMuelle} onChange={(e) => setPesoMuelle(e.target.value)} /></label>
      <label>Cajas (si se registran)<input type="number" min="0" step="1" value={cajasMuelle} onChange={(e) => setCajasMuelle(e.target.value)} /></label>
      <button type="submit" disabled={esperando || !descargaId}>Guardar carga</button>
    </form>}
    {linea?.peso_aceptado != null && <p className={`pesca-diferencia ${colorPeso}`}>Aceptado en planta: {linea.peso_aceptado} {linea.unidad} · comparación muelle: {colorPeso || "pendiente"}</p>}
    {paquete && !paquete.documentacion_lista && <p className="pesca-pendiente-doc">Pendiente: {paquete.faltantes.join(", ")}</p>}
    {puedeCapturarPlanta && ["en_planta", "pendiente_evidencia"].includes(vehicle.estado) && Boolean(vehicle.inicio_planta) && <div className="pesca-form pesca-peso-form">
      <label>Resultado<select value={resultado} onChange={(e) => setResultado(e.target.value)}><option value="completo">Completo</option><option value="parcial">Parcial</option><option value="rechazado">Rechazado</option></select></label>
      <label>Peso aceptado<input type="number" min="0" step="0.001" value={peso} onChange={(e) => setPeso(e.target.value)} /></label>
      <label>Unidad<select value={unidad} onChange={(e) => setUnidad(e.target.value)}><option value="ton">Toneladas</option><option value="kg">Kilogramos</option><option value="lb">Libras</option><option value="oz">Onzas</option></select></label>
      {resultado !== "completo" && <label>Cajas rechazadas<input type="number" min="0" step="1" value={cajas} onChange={(e) => setCajas(e.target.value)} /></label>}
      {resultado === "rechazado" && <label>Motivo<select value={motivo} onChange={(e) => setMotivo(e.target.value)}><option value="">Seleccionar…</option><option value="calidad">Calidad</option><option value="contaminacion_quimica">Contaminación química</option><option value="excedente">Excedente</option><option value="otro">Otro</option></select></label>}
      {vehicle.estado === "pendiente_evidencia" && <label>Motivo para corregir o completar el registro<input value={observacionPeso} onChange={(e) => setObservacionPeso(e.target.value)} required /></label>}
      {!sinFechaFinal && <label>Fecha/hora final<input type="datetime-local" value={fechaFinalPeso} onChange={(e) => setFechaFinalPeso(e.target.value)} /></label>}
      <label>Evidencia de peso<input type="file" accept="application/pdf,image/jpeg,image/png,image/webp" onChange={(e) => setFoto(e.target.files?.[0] ?? null)} /></label>
      <label className="pesca-checkbox"><input type="checkbox" checked={sinFechaFinal} onChange={(e) => setSinFechaFinal(e.target.checked)} /> No registrar fecha final</label>
      <button type="button" disabled={esperando || (!peso && resultado !== "rechazado") || (resultado === "rechazado" && !motivo)} onClick={() => void cerrar()}>{esperando ? "Guardando…" : vehicle.estado === "pendiente_evidencia" ? "Completar peso, evidencia y cierre" : "Guardar peso y evidencia"}</button>
    </div>}
  </article>;
}
