import { useState } from "react";
import { enviarJson, useDatos } from "../api";
import { formatearMonto } from "../formato";

interface Gestor { id: string; codigo: string; nombre: string }
interface Partida {
  tipo: "GESTOR" | "EXTERNO";
  gestor_id: string;
  beneficiario: string;
  base: string;
  porcentaje: string;
}
interface Resultado {
  total: string;
  moneda: "PEN" | "USD";
  estado: string;
  partidas: { beneficiario: string; tipo: string; base: string; porcentaje: string; importe: string }[];
}
const nueva = (): Partida => ({ tipo: "GESTOR", gestor_id: "", beneficiario: "", base: "", porcentaje: "" });

export default function RepartoMultiple() {
  const { datos: gestores } = useDatos<Gestor[]>("/api/v1/gestores");
  const [desde, setDesde] = useState("2026-10-01");
  const [hasta, setHasta] = useState("2026-10-31");
  const [moneda, setMoneda] = useState<"PEN" | "USD">("PEN");
  const [partidas, setPartidas] = useState<Partida[]>([nueva()]);
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);
  const cambiar = (i: number, cambios: Partial<Partida>) => {
    setPartidas((actuales) => actuales.map((p, n) => n === i ? { ...p, ...cambios } : p));
    setResultado(null);
  };
  const cotizar = async () => {
    setError(""); setResultado(null); setCargando(true);
    try {
      setResultado(await enviarJson<Resultado>("/api/v1/pagos-gestores/cotizar-multiple", "POST", {
        desde, hasta, moneda, partidas: partidas.map((p) => ({
          tipo: p.tipo,
          gestor_id: p.tipo === "GESTOR" ? p.gestor_id : null,
          beneficiario: p.beneficiario,
          base: p.base,
          porcentaje: p.porcentaje,
        })),
      }));
    } catch (e) { setError(String(e)); }
    finally { setCargando(false); }
  };
  return <section>
    <h2>Reparto múltiple de comisiones</h2>
    <p className="tenue">Vista previa privada del Usuario. No registra, transfiere ni confirma dinero. La base de cada Gestor debe coincidir con su producción documentada.</p>
    <div className="filtros">
      <label>Desde <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} /></label>
      <label>Hasta <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} /></label>
      <label>Moneda <select value={moneda} onChange={(e) => setMoneda(e.target.value as "PEN" | "USD")}><option value="PEN">Soles</option><option value="USD">Dólares</option></select></label>
    </div>
    {partidas.map((p, i) => <div className="panel-configuracion" key={i}>
      <h3>Beneficiario {i + 1}</h3>
      <div className="filtros">
        <label>Tipo <select value={p.tipo} onChange={(e) => cambiar(i, { tipo: e.target.value as Partida["tipo"], gestor_id: "", beneficiario: "" })}>
          <option value="GESTOR">Gestor</option><option value="EXTERNO">Otro beneficiario</option>
        </select></label>
        {p.tipo === "GESTOR" && <label>Gestor
          <select value={p.gestor_id} onChange={(e) => { const g = gestores?.find((x) => x.id === e.target.value); cambiar(i, { gestor_id: e.target.value, beneficiario: g?.nombre ?? "" }); }}>
            <option value="">Seleccionar</option>
            {gestores?.map((g) => <option key={g.id} value={g.id}>{g.codigo} · {g.nombre}</option>)}
          </select>
        </label>}
        <label>Nombre <input value={p.beneficiario} onChange={(e) => cambiar(i, { beneficiario: e.target.value })} readOnly={p.tipo === "GESTOR"} /></label>
        <label>Base atribuible <input type="number" min="0" step="0.01" value={p.base} onChange={(e) => cambiar(i, { base: e.target.value })}/></label>
        <label>Comisión % <input type="number" min="0" max="100" step="0.0001" value={p.porcentaje} onChange={(e) => cambiar(i, { porcentaje: e.target.value })}/></label>
        <button type="button" disabled={partidas.length === 1} onClick={() => { setPartidas((v) => v.filter((_, n) => n !== i)); setResultado(null); }}>Quitar</button>
      </div>
    </div>)}
    <div className="filtros">
      <button type="button" onClick={() => { setPartidas((v) => [...v, nueva()]); setResultado(null); }}>Agregar destinatario</button>
      <button type="button" disabled={cargando || partidas.some((p) => !p.beneficiario.trim() || !p.base || !p.porcentaje || (p.tipo === "GESTOR" && !p.gestor_id))} onClick={() => void cotizar()}>Calcular reparto</button>
    </div>
    {error && <p role="alert">{error}</p>}
    {resultado && <>
      <h3>Total simulado: {formatearMonto(resultado.moneda, resultado.total)}</h3>
      <table><thead><tr><th>Beneficiario</th><th>Tipo</th><th>Base</th><th>%</th><th>Comisión</th></tr></thead>
        <tbody>{resultado.partidas.map((p, i) => <tr key={i}><td>{p.beneficiario}</td><td>{p.tipo}</td><td>{formatearMonto(resultado.moneda, p.base)}</td><td>{p.porcentaje}%</td><td>{formatearMonto(resultado.moneda, p.importe)}</td></tr>)}</tbody>
      </table>
      <p className="tenue">Simulación no programada. La confirmación y los vouchers estarán disponibles tras implementar el libro de liquidaciones.</p>
    </>}
  </section>;
}
