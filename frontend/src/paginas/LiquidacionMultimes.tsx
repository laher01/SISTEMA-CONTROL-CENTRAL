import { useState } from "react";

import { conParametros, eliminar, enviarJson, useDatos } from "../api";
import { formatearMonto } from "../formato";

type Moneda = "PEN" | "USD";
type Saldo = { id: string; periodo_mes: string; moneda: string; monto: string; detalle: string };
type Adelanto = { id: string; fecha: string; moneda: string; monto: string; descripcion: string };
type Liquidacion = {
  id: string; periodo_desde: string; periodo_hasta: string; moneda: string;
  produccion_total: string; porcentaje: string; bruto: string; adelantos: string;
  saldo: string; estado: string; observacion_adelantos: string; referencia_pago: string;
};
type Cotizacion = {
  produccion: string; saldos_agregados: string; base_global: string;
  porcentaje: string; bruto: string; adelantos: string; neto: string;
  adelantos_pendientes: number; moneda: string;
};

function inicial() {
  const fecha = new Date();
  const anio = fecha.getFullYear();
  const mes = fecha.getMonth();
  const yyyyMM = `${anio}-${String(mes + 1).padStart(2, "0")}`;
  const ultimo = new Date(anio, mes + 1, 0).getDate();
  return { mes: yyyyMM, desde: yyyyMM + "-01", hasta: yyyyMM + "-" + ultimo };
}

export default function LiquidacionMultimes({
  usuarioId, moneda, porcentajeInicial, alCambiar,
}: {
  usuarioId: string;
  moneda: Moneda;
  porcentajeInicial: string;
  alCambiar?: () => void;
}) {
  const inicio = inicial();
  const [desde, setDesde] = useState(inicio.desde);
  const [hasta, setHasta] = useState(inicio.hasta);
  const [saldoMes, setSaldoMes] = useState(inicio.mes);
  const [saldoMonto, setSaldoMonto] = useState("");
  const [saldoDetalle, setSaldoDetalle] = useState("");
  const [porcentaje, setPorcentaje] = useState(porcentajeInicial);
  const [saldosIds, setSaldosIds] = useState<string[]>([]);
  const [adelantosIds, setAdelantosIds] = useState<string[]>([]);
  const [observacion, setObservacion] = useState("");
  const [cotizacion, setCotizacion] = useState<Cotizacion | null>(null);
  const [referencia, setReferencia] = useState("");
  const [fechaPago, setFechaPago] = useState(() => {
    const hoy = new Date();
    return `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, "0")}-${String(hoy.getDate()).padStart(2, "0")}`;
  });
  const [ocupado, setOcupado] = useState(false);
  const [mensaje, setMensaje] = useState("");

  const saldos = useDatos<Saldo[]>(
    conParametros("/api/v1/responsable/pagos/saldos", { usuario_id: usuarioId }),
  );
  const adelantos = useDatos<Adelanto[]>(
    conParametros("/api/v1/responsable/pagos/adelantos", { usuario_id: usuarioId }),
  );
  const liquidaciones = useDatos<Liquidacion[]>(
    conParametros("/api/v1/responsable/pagos/liquidaciones", { usuario_id: usuarioId }),
  );
  const disponiblesSaldos = (saldos.datos ?? []).filter((s) => s.moneda === moneda);
  const disponiblesAdelantos = (adelantos.datos ?? []).filter((a) => a.moneda === moneda);
  const seleccionadosAdelantos = disponiblesAdelantos.filter((a) => adelantosIds.includes(a.id));
  const totalSaldos = disponiblesSaldos.filter((s) => saldosIds.includes(s.id))
    .reduce((n, s) => n + Number(s.monto), 0);
  const totalAdelantos = seleccionadosAdelantos.reduce((n, a) => n + Number(a.monto), 0);
  const omitidos = disponiblesAdelantos.length - seleccionadosAdelantos.length;

  const alternar = (id: string, marcado: boolean, actual: string[], cambiar: (v: string[]) => void) => {
    cambiar(marcado ? [...actual, id] : actual.filter((x) => x !== id));
    setCotizacion(null);
  };
  const recargar = () => {
    saldos.recargar();
    adelantos.recargar();
    liquidaciones.recargar();
    alCambiar?.();
  };
  const solicitud = () => ({
    usuario_id: usuarioId, desde, hasta, moneda, saldo_ids: saldosIds,
    adelanto_ids: adelantosIds, porcentaje_manual: porcentaje || "0",
    observacion_adelantos: observacion.trim() || null,
  });
  const cotizar = async () => {
    setOcupado(true);
    setMensaje("");
    try {
      const r = await enviarJson<Cotizacion>(
        "/api/v1/responsable/pagos/cotizar", "POST", solicitud(),
      );
      setCotizacion(r);
    } catch (error) {
      setCotizacion(null);
      setMensaje(error instanceof Error ? error.message : String(error));
    } finally {
      setOcupado(false);
    }
  };
  const programar = async () => {
    if (omitidos > 0 && observacion.trim().length < 8) {
      setMensaje("Hay adelantos no seleccionados. Indique una observación de al menos 8 caracteres.");
      return;
    }
    setOcupado(true);
    setMensaje("");
    try {
      await enviarJson("/api/v1/responsable/pagos/programar", "POST", solicitud());
      setCotizacion(null);
      setSaldosIds([]);
      setAdelantosIds([]);
      setObservacion("");
      setMensaje("Liquidación programada con saldos y adelantos seleccionados.");
      recargar();
    } catch (error) {
      setMensaje(error instanceof Error ? error.message : String(error));
    } finally {
      setOcupado(false);
    }
  };
  const registrarSaldo = async () => {
    setOcupado(true);
    setMensaje("");
    try {
      await enviarJson("/api/v1/responsable/pagos/saldos", "POST", {
        usuario_id: usuarioId, periodo_mes: saldoMes + "-01", moneda,
        monto: saldoMonto, detalle: saldoDetalle.trim(),
      });
      setSaldoMonto("");
      setSaldoDetalle("");
      setMensaje("Saldo registrado; queda pendiente hasta asignarlo a una liquidación.");
      saldos.recargar();
    } catch (error) {
      setMensaje(error instanceof Error ? error.message : String(error));
    } finally {
      setOcupado(false);
    }
  };
  const confirmar = async (id: string) => {
    if (referencia.trim().length < 4 || !fechaPago) {
      setMensaje("Para registrar el pago indique fecha y referencia bancaria o documental.");
      return;
    }
    setOcupado(true);
    try {
      await enviarJson(`/api/v1/responsable/pagos/${id}/confirmar`, "POST", {
        fecha_pago: fechaPago, referencia_pago: referencia.trim(),
      });
      setReferencia("");
      setMensaje("Pago confirmado en el registro, con referencia y auditoría.");
      recargar();
    } catch (error) {
      setMensaje(error instanceof Error ? error.message : String(error));
    } finally {
      setOcupado(false);
    }
  };
  const anular = async (id: string) => {
    if (!window.confirm("¿Anular liquidación pendiente y liberar sus saldos y adelantos?")) return;
    setOcupado(true);
    try {
      await eliminar(`/api/v1/responsable/pagos/${id}`);
      setMensaje("Programación anulada; saldos y adelantos liberados.");
      recargar();
    } catch (error) {
      setMensaje(error instanceof Error ? error.message : String(error));
    } finally {
      setOcupado(false);
    }
  };

  return <section className="panel-configuracion">
    <h3>Liquidación por mes o rango y saldos pendientes</h3>
    <p className="tenue">
      La base es la producción de las fechas seleccionadas más los saldos que marques.
      El porcentaje procede del Usuario (cero si no tiene asignado) y puede editarse
      antes de programar. Los adelantos solo se descuentan cuando los seleccionas.
    </p>
    <div className="filtros">
      <label>Desde <input type="date" value={desde}
        onChange={(e) => { setDesde(e.target.value); setCotizacion(null); }}/></label>
      <label>Hasta <input type="date" value={hasta}
        onChange={(e) => { setHasta(e.target.value); setCotizacion(null); }}/></label>
      <label>% de usuario <input type="number" min="0" max="100" step="0.0001"
        value={porcentaje} onChange={(e) => { setPorcentaje(e.target.value); setCotizacion(null); }} /></label>
    </div>
    <h4>Saldos de compras de meses anteriores</h4>
    <div className="filtros">
      <label>Mes <input type="month" value={saldoMes}
        onChange={(e) => setSaldoMes(e.target.value)} /></label>
      <input aria-label="Monto saldo de compras" placeholder="Saldo a sumar" type="number"
        min="0.01" step="0.01" value={saldoMonto}
        onChange={(e) => setSaldoMonto(e.target.value)} />
      <input aria-label="Detalle saldo de compras" placeholder="Detalle / observación"
        value={saldoDetalle} onChange={(e) => setSaldoDetalle(e.target.value)} />
      <button disabled={ocupado || !saldoMonto || saldoDetalle.trim().length < 8}
        onClick={() => void registrarSaldo()}>Agregar saldo</button>
    </div>
    <table><thead><tr><th>Aplicar</th><th>Mes</th><th>Monto</th><th>Detalle</th></tr></thead>
      <tbody>{disponiblesSaldos.map((s) => <tr key={s.id}><td>
        <input type="checkbox" aria-label={`Incluir saldo ${s.id}`}
          checked={saldosIds.includes(s.id)}
          onChange={(e) => alternar(s.id, e.target.checked, saldosIds, setSaldosIds)} />
      </td><td>{s.periodo_mes.slice(0, 7)}</td><td>{formatearMonto(moneda, s.monto)}</td>
        <td>{s.detalle}</td></tr>)}</tbody>
    </table>
    <p>Importe adicional seleccionado: <strong>{formatearMonto(moneda, totalSaldos)}</strong></p>
    <h4>Adelantos registrados sin aplicar</h4>
    <table><thead><tr><th>Descontar</th><th>Fecha</th><th>Monto</th><th>Detalle</th></tr></thead>
      <tbody>{disponiblesAdelantos.map((a) => <tr key={a.id}><td>
        <input type="checkbox" aria-label={`Descontar adelanto ${a.id}`}
          checked={adelantosIds.includes(a.id)}
          onChange={(e) => alternar(a.id, e.target.checked, adelantosIds, setAdelantosIds)} />
      </td><td>{a.fecha}</td><td>{formatearMonto(moneda, a.monto)}</td>
        <td>{a.descripcion}</td></tr>)}</tbody></table>
    <p>Adelantos seleccionados: <strong>{formatearMonto(moneda, totalAdelantos)}</strong></p>
    {omitidos > 0 && <label>Justificación de los {omitidos} adelanto(s) no descontados
      <textarea value={observacion} onChange={(e) => setObservacion(e.target.value)}
        placeholder="Explica por qué se descontarán en otra liquidación" rows={2} />
    </label>}
    <div className="acciones">
      <button disabled={ocupado || !desde || !hasta} onClick={() => void cotizar()}>
        Calcular liquidación
      </button>
      <button disabled={ocupado || !cotizacion || (omitidos > 0 && observacion.trim().length < 8)}
        onClick={() => void programar()}>Programar liquidación revisada</button>
    </div>
    {cotizacion && <p role="status">
      Producción del periodo: {formatearMonto(moneda, cotizacion.produccion)} ·
      Saldos incluidos: {formatearMonto(moneda, cotizacion.saldos_agregados)} ·
      Base global: {formatearMonto(moneda, cotizacion.base_global)} ·
      {cotizacion.porcentaje}% = {formatearMonto(moneda, cotizacion.bruto)} ·
      Adelantos: {formatearMonto(moneda, cotizacion.adelantos)} ·
      <strong> Neto programable: {formatearMonto(moneda, cotizacion.neto)}</strong>
    </p>}
    {mensaje && <p role="status">{mensaje}</p>}
    {(saldos.error || adelantos.error || liquidaciones.error) &&
      <p role="alert">{saldos.error || adelantos.error || liquidaciones.error}</p>}
    <h4>Liquidaciones registradas de este Usuario</h4>
    <div className="filtros">
      <label>Fecha de pago <input type="date" value={fechaPago}
        onChange={(e) => setFechaPago(e.target.value)} /></label>
      <input aria-label="Referencia de pago de usuario" placeholder="Referencia bancaria o voucher"
        value={referencia} onChange={(e) => setReferencia(e.target.value)} />
    </div>
    <div className="tabla-responsive"><table>
      <thead><tr><th>Periodo</th><th>Base global</th><th>%</th><th>Bruto</th>
        <th>Adelantos</th><th>Neto</th><th>Estado</th><th>Acciones</th></tr></thead>
      <tbody>{(liquidaciones.datos ?? []).filter((p) => p.moneda === moneda).map((p) =>
        <tr key={p.id}><td>{p.periodo_desde} al {p.periodo_hasta}</td>
          <td>{formatearMonto(moneda, p.produccion_total)}</td><td>{p.porcentaje}%</td>
          <td>{formatearMonto(moneda, p.bruto)}</td>
          <td>{formatearMonto(moneda, p.adelantos)}</td>
          <td>{formatearMonto(moneda, p.saldo)}</td>
          <td>{p.estado}</td>
          <td>{p.estado === "PROGRAMADO" && <>
            <button disabled={ocupado || referencia.trim().length < 4}
              onClick={() => void confirmar(p.id)}>Confirmar pago</button>
            {" "}<button disabled={ocupado} onClick={() => void anular(p.id)}>Anular</button>
          </>}</td></tr>)}</tbody>
    </table></div>
  </section>;
}
