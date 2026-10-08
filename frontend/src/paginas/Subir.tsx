import { useRef, useState, type DragEvent } from "react";
import { Link } from "react-router-dom";

import { ErrorApi, enviarFormulario } from "../api";
import { ETIQUETA_TIPO_DOCUMENTO, formatearFecha, formatearMonto } from "../formato";
import type { Documento, SesionActual } from "../tipos";

// La VPS de pruebas tiene 1 GB de RAM. El procesamiento secuencial evita que
// varios OCR compitan por memoria; el backend también aplica este límite.
const CONCURRENCIA = 1;

type Resultado =
  | { estado: "en_cola" | "subiendo" }
  | { estado: "ok"; documento: Documento }
  | { estado: "duplicado"; mensaje: string }
  | { estado: "error"; mensaje: string };

interface Fila {
  clave: string;
  archivo: File;
  resultado: Resultado;
}

export default function Subir({ sesion }: { sesion: SesionActual }) {
  const [filas, setFilas] = useState<Fila[]>([]);
  const [arrastrando, setArrastrando] = useState(false);
  const entrada = useRef<HTMLInputElement>(null);
  const cola = useRef<Fila[]>([]);
  const activos = useRef(0);
  const actualizar = (clave: string, resultado: Resultado) =>
    setFilas((actuales) => actuales.map((f) => (f.clave === clave ? { ...f, resultado } : f)));

  const subirUno = async (fila: Fila) => {
    actualizar(fila.clave, { estado: "subiendo" });
    const formulario = new FormData();
    formulario.append("archivo", fila.archivo);
    try {
      const documento = await enviarFormulario<Documento>("/api/v1/documentos", formulario);
      actualizar(fila.clave, { estado: "ok", documento });
    } catch (error) {
      const mensaje = error instanceof Error ? error.message : String(error);
      const duplicado = error instanceof ErrorApi && esDuplicado(error);
      actualizar(fila.clave, { estado: duplicado ? "duplicado" : "error", mensaje });
    }
  };

  const agregar = (lista: FileList | null) => {
    if (!lista || lista.length === 0) return;
    const nuevas: Fila[] = Array.from(lista).map((archivo, i) => ({
      clave: `${Date.now()}-${i}-${archivo.name}`,
      archivo,
      resultado: { estado: "en_cola" },
    }));
    setFilas((actuales) => [...nuevas, ...actuales]);
    cola.current.push(...nuevas);
    despachar();
  };

  const despachar = () => {
    while (activos.current < CONCURRENCIA) {
      const fila = cola.current.shift();
      if (!fila) return;
      activos.current += 1;
      void subirUno(fila).finally(() => {
        activos.current -= 1;
        despachar();
      });
    }
  };

  const soltar = (evento: DragEvent) => {
    evento.preventDefault();
    setArrastrando(false);
    agregar(evento.dataTransfer.files);
  };

  const conteo = (estado: Resultado["estado"]) =>
    filas.filter((f) => f.resultado.estado === estado).length;

  const totales = filas.reduce(
    (acumulado, fila) => {
      if (fila.resultado.estado !== "ok") return acumulado;
      const documento = fila.resultado.documento;
      if (!documento.importe_total || !documento.moneda) return acumulado;
      const valor = Number(documento.importe_total);
      if (documento.moneda === "USD") acumulado.usd += valor;
      else acumulado.pen += valor;
      return acumulado;
    },
    { pen: 0, usd: 0 },
  );

  return (
    <>
      <h2>Subir documentos</h2>
      <div className="resumen-carga">
        <strong>Origen identificado por sesión:</strong>{" "}
        {sesion.rol === "GESTOR" ? "Gestor " : "Usuario "}
        {sesion.codigo} · {sesion.nombre}
        {sesion.rol === "GESTOR" && (
          <span> · Usuario propietario enlazado automáticamente</span>
        )}
      </div>
      <div
        className={`zona-carga ${arrastrando ? "activa" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setArrastrando(true);
        }}
        onDragLeave={() => setArrastrando(false)}
        onDrop={soltar}
        onClick={() => entrada.current?.click()}
      >
        <p>
          Arrastra aquí XML, PDF o imágenes, o <strong>haz clic para elegir</strong>.
        </p>
        <p className="tenue">
          El sistema extrae y relaciona automáticamente XML, PDF e imágenes. Solo los casos
          incompletos o ambiguos quedan en Pendientes para revisión.
        </p>
        <input
          ref={entrada}
          type="file"
          multiple
          hidden
          accept=".xml,.pdf,image/*"
          onChange={(e) => {
            agregar(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {filas.length > 0 && (
        <>
          <div className="resumen-lote">
            <p className="resumen-carga">
              {conteo("ok")} subidos · {conteo("duplicado")} duplicados · {conteo("error")} con error ·{" "}
              {conteo("en_cola") + conteo("subiendo")} en proceso
            </p>
            <strong>Total del lote: {formatearMonto("PEN", String(totales.pen))}</strong>
            {totales.usd > 0 && (
              <strong> · {formatearMonto("USD", String(totales.usd))}</strong>
            )}
          </div>
          <table>
            <thead>
              <tr>
                <th>Archivo</th>
                <th>Resultado</th>
                <th>Tipo</th>
                <th>Fecha</th>
                <th>Correlativo</th>
                <th>Emisor</th>
                <th>Receptor</th>
                <th className="num">Monto</th>
                <th>Expediente</th>
              </tr>
            </thead>
            <tbody>
              {filas.map((fila) => (
                <FilaCarga key={fila.clave} fila={fila} />
              ))}
            </tbody>
          </table>
        </>
      )}
    </>
  );
}

function FilaCarga({ fila }: { fila: Fila }) {
  const { resultado } = fila;
  const documento = resultado.estado === "ok" ? resultado.documento : undefined;
  return (
    <tr>
      <td>{fila.archivo.name}</td>
      <td className={`resultado-${resultado.estado}`}>
        {resultado.estado === "en_cola" && "En cola"}
        {resultado.estado === "subiendo" && "Subiendo…"}
        {resultado.estado === "ok" &&
          (documento?.expediente_id ? "Procesado y relacionado" : "Subido · requiere revisión")}
        {(resultado.estado === "duplicado" || resultado.estado === "error") && resultado.mensaje}
        {resultado.estado === "duplicado" && (
          <button type="button" className="secundario" onClick={() => void navigator.clipboard.writeText(resultado.mensaje)}>
            Copiar aviso para WhatsApp
          </button>
        )}
      </td>
      <td>{documento?.tipo_documento ? ETIQUETA_TIPO_DOCUMENTO[documento.tipo_documento] : ""}</td>
      <td>{documento?.fecha_emision ? formatearFecha(documento.fecha_emision) : ""}</td>
      <td>{documento?.serie && documento?.correlativo ? documento.serie + "-" + documento.correlativo : ""}</td>
      <td>
        {documento?.emisor ? (
          <>
            <strong>{documento.emisor.razon_social}</strong>
            <small className="bloque tenue">RUC {documento.emisor.ruc}</small>
          </>
        ) : null}
      </td>
      <td>
        {documento?.receptor ? (
          <>
            <strong>{documento.receptor.razon_social}</strong>
            <small className="bloque tenue">RUC {documento.receptor.ruc}</small>
          </>
        ) : null}
      </td>
      <td className="num">
        {documento?.moneda && documento?.importe_total
          ? formatearMonto(documento.moneda, documento.importe_total)
          : ""}
      </td>
      <td>
        {documento?.expediente_id ? (
          <Link to={`/expedientes/${documento.expediente_id}`}>Ver expediente</Link>
        ) : documento ? (
          <Link to="/pendientes">Revisar</Link>
        ) : null}
      </td>
    </tr>
  );
}

function esDuplicado(error: ErrorApi): boolean {
  const { detalle } = error;
  return error.status === 409 && typeof detalle === "object" && detalle !== null && "duplicado" in detalle;
}
