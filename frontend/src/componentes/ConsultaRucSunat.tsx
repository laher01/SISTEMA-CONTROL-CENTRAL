import { useRef, useState } from "react";
import { obtener } from "../api";

const etiquetas: [string, string][] = [
  ["ruc", "RUC"], ["nombre_o_razon_social", "Razón social"], ["estado", "Estado"],
  ["condicion", "Condición fiscal"], ["direccion_completa", "Domicilio fiscal"],
  ["tipo_contribuyente", "Tipo de contribuyente"], ["fecha_inscripcion", "Fecha de inscripción"],
  ["actividades_economicas", "Actividades económicas"],
];

export default function ConsultaRucSunat({ ruc }: { ruc: string }) {
  const dialogo = useRef<HTMLDialogElement>(null);
  const [ficha, setFicha] = useState<Record<string, unknown>>();
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);

  const abrir = async () => {
    dialogo.current?.showModal();
    setCargando(true);
    setFicha(undefined);
    setError("");
    try {
      setFicha(await obtener(`/api/v1/empresas/consultas/sunat/${encodeURIComponent(ruc)}`));
    } catch {
      setError("Consulta no disponible");
    } finally {
      setCargando(false);
    }
  };

  return <>
    <button type="button" disabled={cargando} onClick={() => void abrir()}>Consultar RUC SUNAT</button>
    <dialog ref={dialogo} aria-label={`Ficha RUC SUNAT ${ruc}`}>
      <h3>Ficha RUC SUNAT · {ruc}</h3>
      {cargando && <p role="status">Consultando…</p>}
      {error && <p role="alert">{error}</p>}
      {ficha?.estado_consulta === "Sin resultados" && <p>Sin resultados para este RUC.</p>}
      {ficha && <dl>{etiquetas.map(([clave, etiqueta]) => {
        const valor = ficha[clave];
        const texto = typeof valor === "string" ? valor
          : Array.isArray(valor) ? valor.filter(v => typeof v === "string").join(" · ") : "";
        return texto ? <div key={clave}><dt>{etiqueta}</dt><dd>{texto}</dd></div> : null;
      })}</dl>}
      <button type="button" onClick={() => dialogo.current?.close()}>Cerrar</button>
    </dialog>
  </>;
}
