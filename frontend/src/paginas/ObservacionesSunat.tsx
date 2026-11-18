import { useState } from "react";
import { enviarFormulario } from "../api";

interface Resumen {
  estado: string;
  filas_leidas: number;
  filas_no_leidas: number;
  proveedores: number;
  periodos: Record<string, number>;
  base_observada: string;
  igv_observado: string;
  total_observado: string;
  filas_con_diferencia_aritmetica: number;
  lectura_requiere_revision: boolean;
}

export default function ObservacionesSunat() {
  const [archivo, setArchivo] = useState<File | null>(null);
  const [resultado, setResultado] = useState<Resumen | null>(null);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);
  async function revisar() {
    if (!archivo || cargando) return;
    setError("");
    setResultado(null);
    if (archivo.size > 20 * 1024 * 1024) {
      setError("El PDF supera el límite de 20 MB.");
      return;
    }
    setCargando(true);
    try {
      const formulario = new FormData();
      formulario.append("archivo", archivo);
      setResultado(await enviarFormulario<Resumen>("/api/v1/registros/sunat/observaciones", formulario));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "No se pudo revisar el PDF.");
    } finally {
      setCargando(false);
    }
  }
  return (
    <section>
      <h2>Fiscalización SUNAT — Observaciones</h2>
      <p>Revisión de solo lectura del Anexo 01.2. El archivo no se incorpora a los registros contables.</p>
      <label htmlFor="sunat-pdf">PDF del requerimiento (máximo 20 MB)</label>
      <input id="sunat-pdf" type="file" accept=".pdf,application/pdf" disabled={cargando} onChange={(e) => {
        setArchivo(e.target.files?.[0] ?? null);
        setResultado(null);
        setError("");
      }} />
      <button type="button" disabled={!archivo || cargando} onClick={() => void revisar()}>
        {cargando ? "Revisando…" : "Revisar observaciones"}
      </button>
      {error && <p role="alert">{error}</p>}
      {resultado && (
        <div aria-live="polite">
          <h3>Observado — pendiente de verificación</h3>
          <p>La lectura no acredita operaciones ni determina crédito fiscal. Contraste con el original.</p>
          <dl>
            <dt>Filas leídas</dt><dd>{resultado.filas_leidas}</dd>
            <dt>Filas no leídas detectadas</dt><dd>{resultado.filas_no_leidas}</dd>
            <dt>Proveedores</dt><dd>{resultado.proveedores}</dd>
            <dt>Base observada</dt><dd>{resultado.base_observada}</dd>
            <dt>IGV observado</dt><dd>{resultado.igv_observado}</dd>
            <dt>Total observado</dt><dd>{resultado.total_observado}</dd>
            <dt>Filas con diferencia aritmética</dt><dd>{resultado.filas_con_diferencia_aritmetica}</dd>
          </dl>
          <table>
            <thead><tr><th>Periodo</th><th>Filas leídas</th></tr></thead>
            <tbody>{Object.entries(resultado.periodos).sort(([a], [b]) => a.localeCompare(b)).map(([periodo, filas]) => (
              <tr key={periodo}><td>{periodo}</td><td>{filas}</td></tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </section>
  );
}
