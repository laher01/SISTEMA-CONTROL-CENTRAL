import { useEffect, useRef, useState } from "react";
import { conParametros, enviarJson } from "../api";

type Resultado = {
  finalizado: boolean;
  expediente_id?: string;
  estado?: string;
  pausa?: string | null;
};

export default function VerificarCpeHistorico({ recargar }: { recargar: () => void }) {
  const [limite, setLimite] = useState(25);
  const [ocupado, setOcupado] = useState(false);
  const [mensaje, setMensaje] = useState("");
  const [error, setError] = useState("");
  const detener = useRef(false);
  const cursor = useRef<string | undefined>(undefined);

  useEffect(() => () => { detener.current = true; }, []);

  const verificar = async () => {
    if (ocupado || !Number.isInteger(limite) || limite < 1 || limite > 1000) return;
    if (!window.confirm(
      `¿Verificar hasta ${limite} facturas sin resultado CPE en esta empresa, en todas las páginas y sin aplicar los filtros? Cada consulta puede consumir una unidad de APIPERU.`,
    )) return;

    detener.current = false;
    setOcupado(true);
    setMensaje("");
    setError("");
    let revisadas = 0;
    let validas = 0;
    let invalidas = 0;
    let pendientes = 0;
    let finalizado = false;
    const resumen = () =>
      `${revisadas} revisadas · ${validas} válidas · ${invalidas} no válidas · ${pendientes} pendientes`;

    try {
      while (!detener.current && revisadas < limite) {
        const ruta = conParametros("/api/v1/expedientes/verificar-cpe-pendiente", {
          despues_de: cursor.current ?? "",
        });
        const resultado = await enviarJson<Resultado>(ruta, "POST", {});
        if (resultado.finalizado) {
          cursor.current = undefined;
          finalizado = true;
          break;
        }
        if (resultado.pausa) {
          setError(resultado.pausa);
          break;
        }
        if (!resultado.expediente_id) throw new Error("Respuesta CPE incompleta.");
        cursor.current = resultado.expediente_id;
        revisadas++;
        if (resultado.estado === "VALIDO") validas++;
        else if (resultado.estado === "INVALIDO") invalidas++;
        else pendientes++;
        setMensaje(resumen());
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setMensaje(finalizado ? `Recorrido terminado · ${resumen()}` : resumen());
      setOcupado(false);
      if (revisadas) recargar();
    }
  };

  return <div className="acciones">
    <label>Máximo de facturas
      <input type="number" min={1} max={1000} value={limite} disabled={ocupado}
        onChange={e => setLimite(Number(e.target.value))} />
    </label>
    <button type="button" disabled={ocupado} onClick={() => void verificar()}>
      Verificar facturas sin CPE
    </button>
    {ocupado && <button type="button" onClick={() => { detener.current = true; }}>Pausar</button>}
    {mensaje && <span role="status">{mensaje}</span>}
    {error && <span role="alert">{error}</span>}
  </div>;
}
