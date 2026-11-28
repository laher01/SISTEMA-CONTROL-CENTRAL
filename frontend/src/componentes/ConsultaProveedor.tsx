import { useRef, useState } from "react";

import { ErrorApi, obtener } from "../api";
import "./ConsultaRucSunat.css";

type Tipo = "coactiva" | "ssco";
type Coincidencia = {
  razon_social?: string | null;
  resolucion?: string | null;
  firme?: string | null;
  publicacion?: string | null;
};
type Resultado = {
  estado: string;
  monto?: string;
  registros?: number;
  corte?: string;
  fuente?: string;
  desactualizado?: boolean;
  coincidencias?: Coincidencia[];
};

const titulos = { coactiva: "Deuda coactiva", ssco: "Consulta SSCO" };

export default function ConsultaProveedor({ ruc, razon }: { ruc: string; razon: string }) {
  const dialogo = useRef<HTMLDialogElement>(null);
  const [tipo, setTipo] = useState<Tipo>("coactiva");
  const [resultado, setResultado] = useState<Resultado>();
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");

  const consultar = async (consulta: Tipo) => {
    dialogo.current?.showModal();
    setTipo(consulta);
    setResultado(undefined);
    setError("");
    setCargando(true);
    try {
      const origen = consulta === "ssco" ? "?ssco_apiperu=true" : "";
      setResultado(await obtener<Resultado>(
        `/api/v1/empresas/consultas/${consulta}/${encodeURIComponent(ruc)}${origen}`,
      ));
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo conectar con FACT CENTRAL.");
    } finally {
      setCargando(false);
    }
  };

  return <>
    <button type="button" disabled={cargando} onClick={() => void consultar("coactiva")}>Consultar Coactiva</button>
    <button type="button" disabled={cargando} onClick={() => void consultar("ssco")}>Consultar SSCO</button>
    <dialog ref={dialogo} className="ficha-ruc" aria-label={`${titulos[tipo]} · ${ruc}`}>
      <h3>{titulos[tipo]} · {ruc}</h3>
      <p className="ficha-ruc__razon">{razon}</p>
      {cargando && <p role="status">Consultando…</p>}
      {error && <p role="alert">{error}</p>}
      {resultado && <>
        <dl className="ficha-ruc__datos">
          <div><dt>Estado</dt><dd>{resultado.estado}</dd></div>
          {tipo === "coactiva" && <>
            <div><dt>Total de deuda</dt><dd>{resultado.monto == null ? "—"
              : Number(resultado.monto).toLocaleString("es-PE", { style: "currency", currency: "PEN" })}</dd></div>
            <div><dt>Registros devueltos</dt><dd>{resultado.registros ?? "—"}</dd></div>
          </>}
          <div><dt>Fuente</dt><dd>{resultado.fuente ?? "APIPERU"}</dd></div>
          {resultado.corte && <div><dt>Corte del padrón</dt><dd>{resultado.corte}</dd></div>}
        </dl>
        {resultado.desactualizado && <p role="status">Se muestra la última copia disponible del padrón.</p>}
        {!!resultado.coincidencias?.length && <table className="ficha-ruc__actividades">
          <caption>Coincidencias en el padrón SSCO</caption>
          <thead><tr>
            <th scope="col">Razón social</th><th scope="col">Resolución</th>
            <th scope="col">Fecha firme</th><th scope="col">Publicación</th>
          </tr></thead>
          <tbody>{resultado.coincidencias.map((fila, indice) => <tr key={indice}>
            <td>{fila.razon_social || "—"}</td><td>{fila.resolucion || "—"}</td>
            <td>{fila.firme || "—"}</td><td>{fila.publicacion || "—"}</td>
          </tr>)}</tbody>
        </table>}
      </>}
      <button type="button" onClick={() => dialogo.current?.close()}>Cerrar</button>
    </dialog>
  </>;
}
