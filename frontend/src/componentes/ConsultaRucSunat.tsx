import { useRef, useState } from "react";
import { ErrorApi, obtener } from "../api";

import "./ConsultaRucSunat.css";

const campos = [
  ["direccion_completa", "Domicilio fiscal"],
  ["tipo_contribuyente", "Tipo de contribuyente"],
  ["fecha_inscripcion", "Fecha de inscripción"],
] as const;

function texto(valor: unknown) {
  return typeof valor === "string" ? valor.trim() : "";
}

function estadoFiscal(valor: string) {
  const coincidencia = valor.match(/^(NO HABIDO|NO HALLADO|HABIDO|ACTIVO|BAJA(?: PROVISIONAL| DEFINITIVA| DE OFICIO)?|SUSPENSI[ÓO]N TEMPORAL)(?=$|[\s.,:;])/i);
  if (!coincidencia?.[0]) return { etiqueta: valor, aviso: "", tono: "neutro" };
  const etiqueta = coincidencia[0].toUpperCase();
  const tono = /^(ACTIVO|HABIDO)$/.test(etiqueta) ? "verde"
    : /^(NO HABIDO|BAJA)/.test(etiqueta) ? "rojo" : "ambar";
  return { etiqueta, aviso: valor.slice(coincidencia[0].length).trim(), tono };
}

function Actividades({ valor }: { valor: unknown }) {
  const actividades = (Array.isArray(valor) ? valor : [valor]).map(texto).filter(Boolean);
  if (!actividades.length) return null;

  return <table className="ficha-ruc__actividades">
    <caption>Actividades económicas</caption>
    <thead><tr><th scope="col">Tipo</th><th scope="col">Código</th><th scope="col">Descripción</th></tr></thead>
    <tbody>{actividades.map((actividad, indice) => {
      const partes = actividad.match(/^(?:(.+?)\s+-\s+)?(\d{4})\s+-\s+(.+)$/);
      return <tr key={`${indice}-${actividad}`}>
        <td>{partes?.[1] ?? "—"}</td>
        <td>{partes?.[2] ?? "—"}</td>
        <td>{partes?.[3] ?? actividad}</td>
      </tr>;
    })}</tbody>
  </table>;
}

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
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo conectar con FACT CENTRAL.");
    } finally {
      setCargando(false);
    }
  };

  return <>
    <button type="button" disabled={cargando} onClick={() => void abrir()}>Consultar RUC SUNAT</button>
    <dialog className="ficha-ruc" ref={dialogo} aria-label={`Ficha RUC SUNAT ${ruc}`}>
      <h3>Ficha RUC SUNAT · {ruc}</h3>
      {cargando && <p role="status">Consultando…</p>}
      {error && <p role="alert">{error}</p>}
      {ficha?.estado_consulta === "Sin resultados" && <p>Sin resultados para este RUC.</p>}
      {typeof ficha?.fuente === "string" && <p>{ficha.fuente}</p>}
      {ficha && ficha.estado_consulta !== "Sin resultados" && <>
        {texto(ficha.nombre_o_razon_social) && <p className="ficha-ruc__razon">{texto(ficha.nombre_o_razon_social)}</p>}
        <dl className="ficha-ruc__datos">
          {([["estado", "Estado del contribuyente"], ["condicion", "Condición del domicilio fiscal"]] as const)
            .map(([clave, etiqueta]) => {
              const valor = texto(ficha[clave]);
              if (!valor) return null;
              const estado = estadoFiscal(valor);
              return <div key={clave}>
                <dt>{etiqueta}</dt>
                <dd>
                  <strong data-tono={estado.tono}>{estado.etiqueta}</strong>
                  {estado.aviso && <p className="ficha-ruc__aviso">{estado.aviso}</p>}
                </dd>
              </div>;
            })}
          {campos.map(([clave, etiqueta]) => {
            const valor = texto(ficha[clave]);
            return valor ? <div key={clave}><dt>{etiqueta}</dt><dd>{valor}</dd></div> : null;
          })}
        </dl>
        <Actividades valor={ficha.actividades_economicas} />
      </>}
      <button type="button" onClick={() => dialogo.current?.close()}>Cerrar</button>
    </dialog>
  </>;
}
