import { useState, type FormEvent } from "react";

import { enviarJson, useDatos } from "../api";
import { formatearMonto } from "../formato";
import type { Gestor, Miembro, SesionActual } from "../tipos";

interface Receptor {
  id: string;
  ruc: string;
  nombre: string;
}

interface SimulacionComisiones {
  usuario_id: string;
  gestor_id: string | null;
  moneda: "PEN" | "USD";
  total_produccion: string;
  comision_total: string;
  detalle: { receptor_id: string; produccion: string; porcentaje: string; comision: string }[];
  aviso: string;
}

function hoyMes(): [string, string] {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const ultimo = new Date(y, d.getMonth() + 1, 0).getDate();
  return [`${y}-${m}-01`, `${y}-${m}-${ultimo}`];
}

export default function Comisiones({ sesion }: { sesion: SesionActual }) {
  const esUsuario = sesion.rol === "USUARIO";
  const esResponsable = sesion.rol === "RESPONSABLE";
  const ruta = esResponsable ? "/api/v1/miembros/mis-usuarios" : "/api/v1/miembros?rol=USUARIO";
  const { datos: disponibles } = useDatos<Miembro[]>(esUsuario ? "" : ruta);
  const [usuarioElegido, setUsuarioElegido] = useState("");
  const usuarioId = esUsuario ? (sesion.usuario_id ?? "") : usuarioElegido;
  const { datos: receptores } = useDatos<Receptor[]>(
    usuarioId ? `/api/v1/comisiones/receptores?usuario_id=${usuarioId}` : "",
  );
  const { datos: gestores } = useDatos<Gestor[]>(
    usuarioId && !esResponsable ? `/api/v1/gestores?usuario_id=${usuarioId}` : "",
  );
  const [gestorId, setGestorId] = useState("");
  const [desde, setDesde] = useState(hoyMes()[0]);
  const [hasta, setHasta] = useState(hoyMes()[1]);
  const [moneda, setMoneda] = useState<"PEN" | "USD">("PEN");
  const [tipoTasa, setTipoTasa] = useState<"GLOBAL" | "RECEPTOR">("GLOBAL");
  const [tasaGlobal, setTasaGlobal] = useState("1.5");
  const [tasas, setTasas] = useState<Record<string, string>>({});
  const [resultado, setResultado] = useState<SimulacionComisiones | null>(null);
  const [mensaje, setMensaje] = useState("");
  const [cargando, setCargando] = useState(false);

  const calcular = async (e: FormEvent) => {
    e.preventDefault();
    setCargando(true);
    setMensaje("");
    setResultado(null);
    try {
      const porReceptor: Record<string, string> = {};
      if (tipoTasa === "RECEPTOR") {
        for (const receptor of receptores ?? []) {
          porReceptor[receptor.id] = tasas[receptor.id] ?? "";
        }
      }
      const datos = await enviarJson<SimulacionComisiones>("/api/v1/comisiones/simular", "POST", {
        usuario_id: usuarioId,
        gestor_id: esResponsable ? null : gestorId || null,
        desde,
        hasta,
        moneda,
        porcentaje_global: tipoTasa === "GLOBAL" ? tasaGlobal : null,
        porcentajes_por_receptor: porReceptor,
      });
      setResultado(datos);
    } catch (error) {
      setMensaje(error instanceof Error ? error.message : String(error));
    } finally {
      setCargando(false);
    }
  };

  return (
    <>
      <h2>Simulación de comisiones por Cliente/Receptor</h2>
      <p className="tenue">
        Cálculo provisional sin generar ni autorizar un pago. Las tasas ingresadas aquí
        no modifican planes contractuales. La fórmula especial Jonatan/Javier se mantiene aparte.
      </p>
      <form onSubmit={(e) => void calcular(e)} className="panel-configuracion">
        <div className="filtros">
          {!esUsuario && <label>Usuario
            <select value={usuarioId} onChange={(e) => {
              setUsuarioElegido(e.target.value);
              setGestorId("");
              setResultado(null);
            }} required>
              <option value="">Seleccionar Usuario</option>
              {(disponibles ?? []).map((u) => (
                <option key={u.id} value={u.id}>{u.codigo} · {u.nombre}</option>
              ))}
            </select>
          </label>}
          {!esResponsable && <label>Gestor
            <select value={gestorId} onChange={(e) => setGestorId(e.target.value)} disabled={!usuarioId}>
              <option value="">Todos los Gestores del Usuario</option>
              {(gestores ?? []).map((g) => (
                <option key={g.id} value={g.id}>{g.codigo} · {g.nombre}</option>
              ))}
            </select>
          </label>}
          <label>Desde <input type="date" required value={desde} onChange={(e) => setDesde(e.target.value)} /></label>
          <label>Hasta <input type="date" required value={hasta} onChange={(e) => setHasta(e.target.value)} /></label>
          <label>Moneda
            <select value={moneda} onChange={(e) => setMoneda(e.target.value as "PEN" | "USD")}>
              <option value="PEN">Soles</option><option value="USD">Dólares</option>
            </select>
          </label>
          <label>Modalidad de comisión
            <select value={tipoTasa} onChange={(e) => setTipoTasa(e.target.value as "GLOBAL" | "RECEPTOR")}>
              <option value="GLOBAL">Porcentaje global</option>
              <option value="RECEPTOR">Por Cliente/Receptor</option>
            </select>
          </label>
          {tipoTasa === "GLOBAL" && <label>Porcentaje global (%)
            <input type="number" min="0" max="100" step="0.0001" required value={tasaGlobal} onChange={(e) => setTasaGlobal(e.target.value)} />
          </label>}
        </div>
        {tipoTasa === "RECEPTOR" && (
          <table>
            <thead><tr><th>RUC</th><th>Cliente/Receptor con producción</th><th>% aplicado</th></tr></thead>
            <tbody>{(receptores ?? []).map((r) => (
              <tr key={r.id}>
                <td>{r.ruc}</td><td>{r.nombre}</td>
                <td><input type="number" min="0" max="100" step="0.0001" required
                  value={tasas[r.id] ?? ""} onChange={(e) => setTasas((prev) => ({ ...prev, [r.id]: e.target.value }))} /></td>
              </tr>
            ))}</tbody>
          </table>
        )}
        <button type="submit" disabled={cargando || !usuarioId}>Calcular sin registrar pago</button>
      </form>
      {mensaje && <p role="alert">{mensaje}</p>}
      {resultado && <section className="panel-configuracion">
        <h3>Resultado provisional</h3>
        <p>Producción documentada: <strong>{formatearMonto(resultado.moneda, resultado.total_produccion)}</strong></p>
        <p>Comisión calculada: <strong>{formatearMonto(resultado.moneda, resultado.comision_total)}</strong></p>
        <table>
          <thead><tr><th>Receptor</th><th>Producción</th><th>Tasa</th><th>Comisión</th></tr></thead>
          <tbody>{resultado.detalle.map((d) => (
            <tr key={d.receptor_id}>
              <td>{receptores?.find((r) => r.id === d.receptor_id)?.nombre ?? d.receptor_id}</td>
              <td>{formatearMonto(resultado.moneda, d.produccion)}</td>
              <td>{d.porcentaje} %</td>
              <td>{formatearMonto(resultado.moneda, d.comision)}</td>
            </tr>
          ))}</tbody>
        </table>
        <p className="tenue">{resultado.aviso}</p>
      </section>}
    </>
  );
}
