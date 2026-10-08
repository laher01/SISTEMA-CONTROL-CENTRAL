import { useMemo, useState, type ChangeEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { conParametros, eliminar, enviarFormulario, useDatos } from "../api";
import { Estado, Paginacion, Semaforo } from "../componentes";
import { ETIQUETA_TIPO_DOCUMENTO, formatearFecha, formatearMonto } from "../formato";
import type {
  Documento,
  RegistroFila,
  RegistroOpciones,
  RegistroResumen,
  SesionActual,
  TipoDocumento,
} from "../tipos";

const POR_PAGINA = 100;

export default function Registros({ sesion }: { sesion: SesionActual }) {
  const [parametros, setParametros] = useSearchParams();
  const tipoEmpresa = parametros.get("tipo_empresa") ?? "";
  const usuarioId = parametros.get("usuario_id") ?? "";
  const gestorId = parametros.get("gestor_id") ?? "";
  const emisor = parametros.get("emisor") ?? "";
  const receptor = parametros.get("receptor") ?? "";
  const dia = parametros.get("dia") ?? "";
  const desde = parametros.get("fecha_desde") ?? "";
  const hasta = parametros.get("fecha_hasta") ?? "";
  const mes = parametros.get("mes") ?? "";
  const pagina = Number(parametros.get("pagina") ?? "0");

  const ruta = conParametros("/api/v1/registros", {
    usuario_id: usuarioId,
    gestor_id: gestorId,
    tipo_empresa: tipoEmpresa,
    emisor,
    receptor,
    dia,
    fecha_desde: desde,
    fecha_hasta: hasta,
    mes,
    limit: String(POR_PAGINA),
    offset: String(pagina * POR_PAGINA),
  });
  const { datos, error, cargando, recargar } = useDatos<RegistroResumen>(ruta);
  const { datos: opciones } = useDatos<RegistroOpciones>("/api/v1/registros/opciones");

  const puedeVerJerarquia = ["SUPERADMIN", "ADMINISTRADOR", "GERENTE", "SECRETARIA"].includes(
    sesion.rol,
  );
  const mostrarUsuario = puedeVerJerarquia;
  const mostrarGestor = sesion.rol !== "GESTOR";
  const filtrarUsuario = puedeVerJerarquia;
  const filtrarGestor = puedeVerJerarquia || sesion.rol === "USUARIO";

  const gestoresDisponibles = useMemo(() => {
    const gestores = opciones?.gestores ?? [];
    if (sesion.rol === "USUARIO") return gestores;
    if (!usuarioId) return gestores;
    return gestores.filter((gestor) => gestor.usuario_id === usuarioId);
  }, [opciones?.gestores, sesion.rol, usuarioId]);

  const etiquetaFiltro = useMemo(() => {
    const partes: string[] = [];
    if (usuarioId) {
      const usuario = opciones?.usuarios.find((item) => item.id === usuarioId);
      if (usuario) partes.push(`Usuario: ${usuario.codigo} · ${usuario.nombre}`);
    }
    if (gestorId) {
      const gestor = opciones?.gestores.find((item) => item.id === gestorId);
      if (gestor) partes.push(`Gestor: ${gestor.codigo} · ${gestor.nombre}`);
    }
    if (tipoEmpresa) partes.push(`Empresa tipo ${tipoEmpresa}`);
    if (emisor) partes.push(`Emisor: ${emisor}`);
    if (receptor) partes.push(`Receptor: ${receptor}`);
    if (dia) partes.push(`Día: ${dia}`);
    else if (mes) partes.push(`Mes: ${mes}`);
    else if (desde || hasta) partes.push(`Periodo: ${desde || "inicio"} → ${hasta || "hoy"}`);
    return partes.length > 0 ? partes.join(" · ") : "Todos los registros visibles para este rol";
  }, [desde, dia, emisor, gestorId, hasta, mes, opciones, receptor, tipoEmpresa, usuarioId]);

  const cambiar = (clave: string, valor: string) => {
    const siguiente = new URLSearchParams(parametros);
    if (valor) siguiente.set(clave, valor);
    else siguiente.delete(clave);

    if (clave === "usuario_id") {
      const gestorActual = opciones?.gestores.find((item) => item.id === gestorId);
      if (!valor || (gestorActual && gestorActual.usuario_id !== valor)) {
        siguiente.delete("gestor_id");
      }
    }

    if (clave === "dia" && valor) {
      siguiente.delete("fecha_desde");
      siguiente.delete("fecha_hasta");
      siguiente.delete("mes");
    }
    if ((clave === "fecha_desde" || clave === "fecha_hasta") && valor) {
      siguiente.delete("dia");
      siguiente.delete("mes");
    }
    if (clave === "mes" && valor) {
      siguiente.delete("dia");
      siguiente.delete("fecha_desde");
      siguiente.delete("fecha_hasta");
    }

    if (clave !== "pagina") siguiente.delete("pagina");
    setParametros(siguiente);
  };

  const limpiar = () => setParametros({});

  return (
    <>
      <div className="encabezado-pagina">
        <div>
          <h2>Base de registros</h2>
          <p className="tenue">
            Compras con totales, propiedad, emisor, receptor y documentación del expediente.
          </p>
        </div>
      </div>

      <section className="panel-configuracion">
        <strong>Resumen del filtro actual</strong>
        <p className="tenue">{etiquetaFiltro}</p>
        <div className="tarjetas registros-resumen">
          <div className="tarjeta borde-verde">
            <span className="cifra">{datos?.total_registros ?? 0}</span>
            <span>Registros filtrados</span>
          </div>
          <div className="tarjeta borde-verde">
            <span className="cifra">{formatearMonto("PEN", datos?.total_pen ?? "0")}</span>
            <span>Total PEN del filtro</span>
          </div>
          <div className="tarjeta borde-verde">
            <span className="cifra">{formatearMonto("USD", datos?.total_usd ?? "0")}</span>
            <span>Total USD del filtro</span>
          </div>
        </div>
      </section>

      <div className="filtros filtros-documentos">
        <select aria-label="Tipo de empresa" value={tipoEmpresa} onChange={(e) => cambiar("tipo_empresa", e.target.value)}>
          <option value="">Todas las empresas</option>
          <option value="A">Tipo A</option>
          <option value="B">Tipo B</option>
        </select>
        {filtrarUsuario && (
          <select value={usuarioId} onChange={(e) => cambiar("usuario_id", e.target.value)}>
            <option value="">Todos los usuarios</option>
            {opciones?.usuarios.map((u) => (
              <option key={u.id} value={u.id}>{u.codigo} · {u.nombre}</option>
            ))}
          </select>
        )}
        {filtrarGestor && (
          <select value={gestorId} onChange={(e) => cambiar("gestor_id", e.target.value)}>
            <option value="">Todos los gestores</option>
            {gestoresDisponibles.map((g) => (
              <option key={g.id} value={g.id}>{g.codigo} · {g.nombre}</option>
            ))}
          </select>
        )}
        <input
          placeholder="Emisor: RUC o razón social"
          value={emisor}
          onChange={(e) => cambiar("emisor", e.target.value)}
        />
        <input
          placeholder="Receptor: RUC o razón social"
          value={receptor}
          onChange={(e) => cambiar("receptor", e.target.value)}
        />
        <label className="filtro-fecha">
          Día
          <input type="date" value={dia} onChange={(e) => cambiar("dia", e.target.value)} />
        </label>
        <label className="filtro-fecha">
          Desde
          <input type="date" value={desde} onChange={(e) => cambiar("fecha_desde", e.target.value)} />
        </label>
        <label className="filtro-fecha">
          Hasta
          <input type="date" value={hasta} onChange={(e) => cambiar("fecha_hasta", e.target.value)} />
        </label>
        <label className="filtro-fecha">
          Mes
          <input type="month" value={mes} onChange={(e) => cambiar("mes", e.target.value)} />
        </label>
        <button className="secundario" onClick={limpiar}>Limpiar filtros</button>
      </div>

      <Estado cargando={cargando} error={error} vacio={datos?.filas.length === 0}>
        <div className="tabla-responsive">
          <table className="tabla-registros">
            <thead>
              <tr>
                <th>Estado</th>
                {mostrarUsuario && <th>Usuario</th>}
                {mostrarGestor && <th>Gestor</th>}
                <th>Fecha</th>
                <th>Tipo empresa</th>
                <th>Correlativo</th>
                <th>RUC emisor</th>
                <th>Razón social emisor</th>
                <th>RUC receptor</th>
                <th>Razón social receptor</th>
                <th className="num">Monto</th>
                <th>Documentación / opciones</th>
              </tr>
            </thead>
            <tbody>
              {datos?.filas.map((fila) => (
                <FilaRegistro
                  key={fila.expediente_id}
                  fila={fila}
                  sesion={sesion}
                  mostrarUsuario={mostrarUsuario}
                  mostrarGestor={mostrarGestor}
                  alCambiar={recargar}
                />
              ))}
            </tbody>
          </table>
        </div>
      </Estado>

      <Paginacion
        pagina={pagina}
        hayMas={(datos?.filas.length ?? 0) === POR_PAGINA}
        alCambiar={(p) => cambiar("pagina", String(p))}
      />
    </>
  );
}

function FilaRegistro({
  fila,
  sesion,
  mostrarUsuario,
  mostrarGestor,
  alCambiar,
}: {
  fila: RegistroFila;
  sesion: SesionActual;
  mostrarUsuario: boolean;
  mostrarGestor: boolean;
  alCambiar: () => void;
}) {
  const [tipo, setTipo] = useState<TipoDocumento>("COT");
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState("");
  const puedeAdjuntar =
    sesion.rol === "GESTOR" || sesion.rol === "USUARIO" || sesion.rol === "SECRETARIA";

  const opciones = useMemo(() => {
    const todos = [...fila.documentos_requeridos, ...fila.documentos_opcionales];
    return [...new Set(todos)].filter((t) => t !== "FACT" && t !== "RHE");
  }, [fila.documentos_requeridos, fila.documentos_opcionales]);

  const adjuntar = async (e: ChangeEvent<HTMLInputElement>) => {
    const archivo = e.target.files?.[0];
    e.target.value = "";
    if (!archivo) return;
    setOcupado(true);
    setError("");
    try {
      const form = new FormData();
      form.append("archivo", archivo);
      form.append("tipo_documento", tipo);
      form.append("expediente_id", fila.expediente_id);
      await enviarFormulario<Documento>("/api/v1/documentos", form);
      alCambiar();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setOcupado(false);
    }
  };

  const retirar = async () => {
    if (!window.confirm("¿Eliminar lógicamente este registro? Los originales se conservarán.")) return;
    setOcupado(true);
    setError("");
    try {
      await eliminar("/api/v1/expedientes/" + fila.expediente_id);
      alCambiar();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setOcupado(false);
    }
  };

  return (
    <tr>
      <td><Semaforo estado={fila.estado} /></td>
      {mostrarUsuario && (
        <td>
          {fila.usuario_codigo
            ? fila.usuario_codigo + " · " + (fila.usuario_nombre ?? "")
            : "—"}
        </td>
      )}
      {mostrarGestor && (
        <td>
          {fila.gestor_codigo
            ? fila.gestor_codigo + " · " + (fila.gestor_nombre ?? "")
            : "Sin gestor"}
        </td>
      )}
      <td>{formatearFecha(fila.fecha_emision)}</td>
      <td>{fila.tipo_empresa ? `Tipo ${fila.tipo_empresa}` : "Sin clasificar"}</td>
      <td>
        <Link to={"/expedientes/" + fila.expediente_id}>
          {fila.tipo_comprobante + " " + fila.serie + "-" + fila.correlativo}
        </Link>
      </td>
      <td>{fila.emisor_ruc}</td>
      <td>{fila.emisor_razon_social}</td>
      <td>{fila.receptor_ruc}</td>
      <td>{fila.receptor_razon_social}</td>
      <td className="num">{formatearMonto(fila.moneda, fila.importe_total)}</td>
      <td>
        <div className="acciones-registro">
          <small>
            Presentes: {fila.documentos_presentes.map((t) => ETIQUETA_TIPO_DOCUMENTO[t]).join(", ") || "ninguno"}
          </small>
          {fila.documentos_faltantes.length > 0 && (
            <small className="resultado-error">
              Faltan: {fila.documentos_faltantes.map((t) => ETIQUETA_TIPO_DOCUMENTO[t]).join(", ")}
            </small>
          )}
          {puedeAdjuntar && opciones.length > 0 && (
            <div className="adjuntar-registro">
              <select value={tipo} onChange={(e) => setTipo(e.target.value as TipoDocumento)}>
                {opciones.map((t) => {
                  const obligatorio = fila.documentos_requeridos.includes(t);
                  return (
                    <option key={t} value={t}>
                      {ETIQUETA_TIPO_DOCUMENTO[t]} · {obligatorio ? "obligatorio" : "opcional"}
                    </option>
                  );
                })}
              </select>
              <label className="boton-enlace">
                {ocupado ? "Procesando…" : "Adjuntar"}
                <input type="file" hidden disabled={ocupado} onChange={adjuntar} />
              </label>
            </div>
          )}
          <div>
            <Link to={"/expedientes/" + fila.expediente_id}>Ver expediente</Link>
            {fila.puede_eliminar && (
              <>
                {" · "}
                <button className="peligro enlace-boton" disabled={ocupado} onClick={retirar}>
                  Eliminar
                </button>
              </>
            )}
          </div>
          {error && <small className="error bloque">{error}</small>}
        </div>
      </td>
    </tr>
  );
}
