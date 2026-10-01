import { useRef, useState, type DragEvent } from "react";
import { Link } from "react-router-dom";

import { ErrorApi, enviarFormulario } from "../api";
import { ETIQUETA_TIPO_DOCUMENTO } from "../formato";
import type { Documento } from "../tipos";

const CONCURRENCIA = 3;

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

export default function Subir() {
  const [filas, setFilas] = useState<Fila[]>([]);
  const [arrastrando, setArrastrando] = useState(false);
  const entrada = useRef<HTMLInputElement>(null);

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
      const duplicado = error instanceof ErrorApi && error.status === 409;
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
    const cola = [...nuevas];
    const trabajador = async () => {
      for (let fila = cola.shift(); fila; fila = cola.shift()) await subirUno(fila);
    };
    for (let i = 0; i < CONCURRENCIA; i++) void trabajador();
  };

  const soltar = (evento: DragEvent) => {
    evento.preventDefault();
    setArrastrando(false);
    agregar(evento.dataTransfer.files);
  };

  const conteo = (estado: Resultado["estado"]) => filas.filter((f) => f.resultado.estado === estado).length;

  return (
    <>
      <h2>Subir documentos</h2>
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
          Los XML de factura y guía SUNAT se asocian solos a su expediente. Los demás quedan en
          Pendientes para vincularlos.
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
          <p className="resumen-carga">
            {conteo("ok")} subidos · {conteo("duplicado")} duplicados · {conteo("error")} con error ·{" "}
            {conteo("en_cola") + conteo("subiendo")} en proceso
          </p>
          <table>
            <thead>
              <tr>
                <th>Archivo</th>
                <th>Resultado</th>
                <th>Tipo</th>
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
        {resultado.estado === "ok" && "Subido"}
        {(resultado.estado === "duplicado" || resultado.estado === "error") && resultado.mensaje}
      </td>
      <td>{documento?.tipo_documento ? ETIQUETA_TIPO_DOCUMENTO[documento.tipo_documento] : ""}</td>
      <td>
        {documento?.expediente_id ? (
          <Link to={`/expedientes/${documento.expediente_id}`}>Ver expediente</Link>
        ) : documento ? (
          <Link to="/pendientes">Vincular</Link>
        ) : null}
      </td>
    </tr>
  );
}
