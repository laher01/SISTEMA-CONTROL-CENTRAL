import { useDatos } from "../api";

type Mensaje = {
  id: string;
  buzon_id: string;
  remitente: string;
  estado: string;
  fecha: string;
};

type Recepcion = {
  gestor: string;
  remitentes: string[];
  mensajes: Mensaje[];
};

export default function RecepcionGestor() {
  const { datos, error, cargando, recargar } = useDatos<Recepcion>(
    "/api/v1/correo/mi-recepcion",
  );
  return <section className="panel-configuracion">
    <h2>Recepción Automática</h2>
    <p className="tenue">
      Consulta los correos registrados por Administración para tu gestoría y su
      historial de recepción. Los buzones se conectan exclusivamente desde Administración.
    </p>
    <button type="button" onClick={recargar}>Actualizar historial</button>
    {cargando && <p>Cargando recepción…</p>}
    {error && <p role="alert">{error}</p>}
    {datos && <>
      <h3>Mis remitentes autorizados</h3>
      {datos.remitentes.length === 0
        ? <p>Administración todavía no ha registrado remitentes para tu gestoría.</p>
        : <ul>{datos.remitentes.map((r) => <li key={r}>{r}</li>)}</ul>}
      <h3>Correos identificados a mi nombre</h3>
      <table>
        <thead><tr><th>Fecha</th><th>Remitente</th><th>Estado</th></tr></thead>
        <tbody>{datos.mensajes.map((m) =>
          <tr key={m.id}>
            <td>{new Date(m.fecha).toLocaleString("es-PE")}</td>
            <td>{m.remitente}</td>
            <td>{m.estado}</td>
          </tr>)}</tbody>
      </table>
      {datos.mensajes.length === 0 && <p>No hay mensajes identificados todavía.</p>}
    </>}
  </section>;
}
