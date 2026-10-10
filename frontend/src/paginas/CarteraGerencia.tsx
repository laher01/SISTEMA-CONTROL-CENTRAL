import { useState, type FormEvent } from "react";

import { enviarJson, useDatos } from "../api";
import type { Empresa } from "../tipos";

type Cartera = { id: string; empresa_id: string; gerente_id: string; activo: boolean };

export default function CarteraGerencia() {
  const { datos: cartera, recargar } = useDatos<Cartera[]>("/api/v1/gerencias/empresas");
  const { datos: empresas, recargar: recargarEmpresas } = useDatos<Empresa[]>("/api/v1/empresas");
  const [ruc, setRuc] = useState("");
  const [razon, setRazon] = useState("");
  const [tipo, setTipo] = useState("CLIENTE");
  const [csv, setCsv] = useState("");
  const [mensaje, setMensaje] = useState("");
  const actualizar = () => { recargar(); recargarEmpresas(); };
  const alta = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    try {
      const resultado = await enviarJson<{ resultado: string }>("/api/v1/gerencias/empresas/alta", "POST", {
        ruc, razon_social: razon, tipo_relacion: tipo,
      });
      setMensaje(resultado.resultado === "CREADA" ? "Empresa creada y vinculada." : "RUC existente vinculado.");
      setRuc(""); setRazon(""); actualizar();
    } catch (error) { setMensaje(String(error)); }
  };
  const importar = async () => {
    const filas = csv.split(/\r?\n/).map((x) => x.trim()).filter(Boolean);
    const lote = filas.map((linea) => {
      const [nuevoRuc, razon_social, tipo_relacion = "SIN_CLASIFICAR"] = linea.split(";").map((x) => x.trim());
      return { ruc: nuevoRuc, razon_social, tipo_relacion: tipo_relacion.toUpperCase() };
    });
    try {
      const res = await enviarJson<{ creadas: number; vinculadas: number }>(
        "/api/v1/gerencias/empresas/importar", "POST", { empresas: lote },
      );
      setMensaje(`Nuevas: ${res.creadas}. Vinculadas existentes: ${res.vinculadas}.`);
      setCsv(""); actualizar();
    } catch (error) { setMensaje(String(error)); }
  };
  const vinculadas = (cartera ?? []).filter((x) => x.activo);
  return <main className="panel-configuracion">
    <h2>Mi cartera comercial</h2>
    <p>Clientes y proveedores vinculados a tu Gerencia. Un RUC existente en tu Administración
      se reutiliza sin duplicarlo ni sobrescribir sus datos fiscales.</p>
    {mensaje && <p role="status">{mensaje}</p>}
    <h3>Empresas vinculadas</h3>
    <table><thead><tr><th>RUC</th><th>Razón social</th><th>Relación</th></tr></thead>
      <tbody>{vinculadas.map((v) => {
        const empresa = (empresas ?? []).find((e) => e.id === v.empresa_id);
        return empresa ? <tr key={v.id}><td>{empresa.ruc}</td>
          <td>{empresa.razon_social}</td><td>{empresa.tipo_relacion}</td></tr> : null;
      })}</tbody>
    </table>
    <h3>Registrar o incorporar empresa existente</h3>
    <form className="filtros" onSubmit={(e) => void alta(e)}>
      <label>RUC <input value={ruc} onChange={(e) => setRuc(e.target.value)}
        required pattern="[0-9]{11}" maxLength={11} /></label>
      <label>Razón social <input value={razon} onChange={(e) => setRazon(e.target.value)}
        required minLength={3} maxLength={300} /></label>
      <label>Tipo <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
        <option value="CLIENTE">Cliente</option><option value="PROVEEDOR">Proveedor</option>
        <option value="AMBOS">Ambos</option><option value="SIN_CLASIFICAR">Sin clasificar</option>
      </select></label>
      <button type="submit">Guardar en mi cartera</button>
    </form>
    <h3>Importar CSV</h3>
    <p>Formato: RUC;RAZÓN SOCIAL;TIPO, una empresa por línea (máximo 500).</p>
    <textarea rows={5} value={csv} onChange={(e) => setCsv(e.target.value)} />
    <label>Seleccionar CSV
      <input type="file" accept=".csv,.txt,text/csv" onChange={(e) => {
        const archivo = e.target.files?.[0];
        if (archivo) void archivo.text().then(setCsv);
      }} />
    </label>
    <button type="button" disabled={!csv.trim()} onClick={() => void importar()}>Importar</button>
  </main>;
}
