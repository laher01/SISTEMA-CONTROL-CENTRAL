import { useState, type FormEvent } from "react";

const campos = ["importe_minimo", "importe_maximo", "importe_minimo_estricto", "importe_moneda"] as const;

export function parametrosImportes(parametros: URLSearchParams) {
  return Object.fromEntries(campos.map((campo) => [campo, parametros.get(campo) ?? ""]));
}

type Props = {
  parametros: URLSearchParams;
  aplicar: (parametros: URLSearchParams) => void;
};

export default function FiltroImportes(props: Props) {
  const clave = JSON.stringify(parametrosImportes(props.parametros));
  return <FormularioImportes key={clave} {...props} />;
}

function FormularioImportes({ parametros, aplicar }: Props) {
  const [error, setError] = useState("");
  const activo = parametros.has("importe_minimo") || parametros.has("importe_maximo");
  const actualizar = (evento: FormEvent<HTMLFormElement>) => {
    evento.preventDefault();
    const datos = new FormData(evento.currentTarget);
    const minimo = String(datos.get("importe_minimo") ?? "");
    const maximo = String(datos.get("importe_maximo") ?? "");
    const estricto = datos.get("importe_minimo_estricto") === "true";
    if (minimo && maximo && (Number(minimo) > Number(maximo) || (estricto && Number(minimo) === Number(maximo)))) {
      setError("El importe máximo debe admitir al menos un valor del rango.");
      return;
    }
    setError("");
    const siguiente = sinImportes();
    if (minimo || maximo) {
      siguiente.set("importe_moneda", String(datos.get("importe_moneda")));
      if (minimo) siguiente.set("importe_minimo", minimo);
      if (maximo) siguiente.set("importe_maximo", maximo);
      if (minimo && estricto) siguiente.set("importe_minimo_estricto", "true");
    }
    aplicar(siguiente);
  };

  const sinImportes = () => {
    const siguiente = new URLSearchParams(parametros);
    campos.forEach((campo) => siguiente.delete(campo));
    siguiente.delete("pagina");
    return siguiente;
  };

  return <form onSubmit={actualizar} className="filtros" aria-label="Rango de importes">
    <label>Moneda <select name="importe_moneda" defaultValue={parametros.get("importe_moneda") ?? "PEN"}>
      <option value="PEN">Soles (S/)</option>
      <option value="USD">Dólares (US$)</option>
    </select></label>
    <label>Comparación del mínimo <select name="importe_minimo_estricto" defaultValue={parametros.get("importe_minimo_estricto") ?? "false"}>
      <option value="false">Desde (≥)</option>
      <option value="true">Mayor que (&gt;)</option>
    </select></label>
    <label>Importe mínimo <input name="importe_minimo" type="number" step="0.01"
      min="-999999999999.99" max="999999999999.99" defaultValue={parametros.get("importe_minimo") ?? ""} /></label>
    <label>Importe máximo (inclusive) <input name="importe_maximo" type="number" step="0.01"
      min="-999999999999.99" max="999999999999.99" defaultValue={parametros.get("importe_maximo") ?? ""} /></label>
    <button type="submit">Aplicar importe</button>
    {activo && <button type="button" className="secundario" onClick={() => aplicar(sinImportes())}>Quitar rango</button>}
    {error && <span role="alert">{error}</span>}
  </form>;
}
