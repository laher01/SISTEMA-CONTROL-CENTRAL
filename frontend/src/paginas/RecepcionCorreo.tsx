import { useState } from "react";
import { enviarJson, useDatos } from "../api";
import type { SesionActual } from "../tipos";

type Registro = { id: string; direccion: string; activo: boolean; proveedor?: string };

export default function RecepcionCorreo({ sesion }: { sesion: SesionActual }) {
  const responsable = sesion.rol === "RESPONSABLE";
  const ruta = responsable ? "/api/v1/recepcion-correo/buzones" : "/api/v1/recepcion-correo/remitentes";
  const { datos, cargando, error, recargar } = useDatos<Registro[]>(ruta);
  const [direccion, setDireccion] = useState("");
  const [proveedor, setProveedor] = useState("GMAIL");
  const [mensaje, setMensaje] = useState("");
  const [guardando, setGuardando] = useState(false);
  async function agregar() {
    setGuardando(true);
    setMensaje("");
    try {
      await enviarJson(ruta, "POST", responsable ? { direccion, proveedor } : { direccion });
      setDireccion("");
      setMensaje(responsable ? "Buzón registrado. Pendiente de autorización OAuth." : "Remitente registrado.");
      recargar();
    } catch (e) {
      setMensaje(e instanceof Error ? e.message : String(e));
    } finally {
      setGuardando(false);
    }
  }
  if (!["RESPONSABLE", "GESTOR"].includes(sesion.rol)) return <p>Sin permiso de recepción.</p>;
  return <section className="panel-configuracion">
    <h2>{responsable ? "Mis buzones Gmail / Outlook" : "Remitentes autorizados"}</h2>
    <p>{responsable
      ? "Registra las cuentas que recibirán comprobantes. Todavía no se conectan ni descargan mensajes hasta autorizar OAuth."
      : "Registra los correos de proveedores asociados a tu gestor. Los documentos entrantes deben superar la validación del RUC receptor."}</p>
    <div className="filtros">
      <label>Dirección de correo
        <input type="email" value={direccion} onChange={(e) => setDireccion(e.target.value)} placeholder="proveedor@ejemplo.com" />
      </label>
      {responsable && <label>Proveedor
        <select value={proveedor} onChange={(e) => setProveedor(e.target.value)}>
          <option value="GMAIL">Gmail</option>
          <option value="OUTLOOK">Outlook</option>
        </select>
      </label>}
      <button type="button" disabled={guardando || !direccion.includes("@")} onClick={agregar}>
        {guardando ? "Guardando…" : "Registrar"}
      </button>
    </div>
    {mensaje && <p role="status">{mensaje}</p>}
    {cargando && <p>Cargando…</p>}
    {error && <p role="alert">{error}</p>}
    <table><thead><tr><th>Correo</th><th>Proveedor</th><th>Estado</th></tr></thead>
      <tbody>{(datos ?? []).map((fila) =>
        <tr key={fila.id}><td>{fila.direccion}</td><td>{fila.proveedor ?? "Proveedor"}</td>
          <td>{responsable ? "Pendiente OAuth" : fila.activo ? "Activo" : "Inactivo"}</td></tr>
      )}</tbody>
    </table>
  </section>;
}
