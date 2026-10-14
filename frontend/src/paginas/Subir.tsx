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
  | { estado: "duplicado"; mensaje: string; expedienteId?: string }
  | { estado: "error"; mensaje: string };

interface Fila {
  clave: string;
  archivo: File;
  resultado: Resultado;
}

type InformePaquete = {
  modo: string;
  total: number;
  relacionados?: number;
  revision?: number;
  duplicados?: number;
  errores?: number;
  documentos: Array<{
    pagina_inicio: number;
    pagina_fin: number;
    tipo: string;
    serie: string;
    correlativo: string;
    ruc_emisor: string;
    estado?: string;
    detalle?: string;
  }>;
};

type EstadoPaquete = "pendiente" | "analizando" | "listo" | "importando" | "importado" | "error";
type FilaPaquete = {
  id: string;
  archivo: File;
  estado: EstadoPaquete;
  vistaPrevia?: InformePaquete;
  indicesSeleccionados?: number[];
  resultado?: InformePaquete;
  error?: string;
};

export default function Subir({ sesion }: { sesion: SesionActual }) {
  const [paquetes, setPaquetes] = useState<FilaPaquete[]>([]);
  const [analizandoPaquete, setAnalizandoPaquete] = useState(false);
  const [confirmandoPaquete, setConfirmandoPaquete] = useState(false);
  const [progresoPaquetes, setProgresoPaquetes] = useState("");
  const [errorPaquete, setErrorPaquete] = useState("");
  const paquetesRef = useRef<FilaPaquete[]>([]);
  const ocupadaRef = useRef(false);
  const actualizarPaquetes = (siguientes: FilaPaquete[]) => {
    paquetesRef.current = siguientes;
    setPaquetes(siguientes);
  };
  const [filas, setFilas] = useState<Fila[]>([]);
  const [arrastrando, setArrastrando] = useState(false);
  const entrada = useRef<HTMLInputElement>(null);
  const entradaCamara = useRef<HTMLInputElement>(null);
  const entradaEscaneos = useRef<HTMLInputElement>(null);
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
      if (duplicado) {
        const detalle = (error as ErrorApi).detalle;
        const expedienteId =
          detalle && typeof detalle === "object" && "expediente_id" in detalle &&
          typeof detalle.expediente_id === "string"
            ? detalle.expediente_id
            : undefined;
        actualizar(fila.clave, { estado: "duplicado", mensaje, expedienteId });
      } else {
        actualizar(fila.clave, { estado: "error", mensaje });
      }
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

  const seleccionarPaquetes = (lista: FileList | null) => {
    if (!lista || ocupadaRef.current) return;
    const archivos = Array.from(lista).filter((f) => f.name.toLowerCase().endsWith(".pdf"));
    actualizarPaquetes(
      archivos.map((archivo, index) => ({
        id: `${index}-${archivo.name}-${archivo.size}-${archivo.lastModified}`,
        archivo,
        estado: "pendiente" as const,
      })),
    );
    setErrorPaquete("");
    setProgresoPaquetes("");
  };

  const solicitarPaquete = async (archivo: File, confirmar: boolean, indices?: number[]): Promise<InformePaquete> => {
    const form = new FormData();
    form.append("archivo", archivo);
    form.append("confirmar", String(confirmar));
    if (confirmar && indices) form.append("indices_documentos", indices.join(","));
    return enviarFormulario<InformePaquete>("/api/v1/documentos/paquete", form);
  };

  const ejecutarPaquetes = async (confirmar: boolean) => {
    if (ocupadaRef.current) return;
    const actuales = paquetesRef.current;
    if (!actuales.length) return;
    if (confirmar && actuales.some((p) => p.estado !== "listo" && p.estado !== "error")) {
      setErrorPaquete("Analice los paquetes primero y espere a que finalice la vista previa.");
      return;
    }
    ocupadaRef.current = true;
    if (confirmar) setConfirmandoPaquete(true);
    else setAnalizandoPaquete(true);
    setErrorPaquete("");
    const candidatos = actuales.filter((p) =>
      confirmar ? p.estado === "listo" && Boolean(p.indicesSeleccionados?.length) : p.estado === "pendiente" || p.estado === "error",
    );
    for (let i = 0; i < candidatos.length; i += 1) {
      const fila = candidatos[i];
      if (!fila) continue;
      setProgresoPaquetes(`${confirmar ? "Importando" : "Analizando"} paquete ${i + 1} de ${candidatos.length}: ${fila.archivo.name}`);
      actualizarPaquetes(
        paquetesRef.current.map((p) =>
          p.id === fila.id ? { ...p, estado: confirmar ? "importando" : "analizando" } : p,
        ),
      );
      try {
        const informe = await solicitarPaquete(fila.archivo, confirmar, fila.indicesSeleccionados);
        actualizarPaquetes(
          paquetesRef.current.map((p) =>
            p.id === fila.id
              ? confirmar
                ? { ...p, estado: "importado", resultado: informe }
                : { ...p, estado: "listo", vistaPrevia: informe, indicesSeleccionados: informe.documentos.map((_, i) => i), resultado: undefined }
              : p,
          ),
        );
      } catch (error) {
        const mensaje = error instanceof Error ? error.message : String(error);
        actualizarPaquetes(
          paquetesRef.current.map((p) =>
            p.id === fila.id ? { ...p, estado: "error", error: mensaje } : p,
          ),
        );
      }
    }
    setProgresoPaquetes(`Finalizado: ${candidatos.length} paquete(s) procesados.`);
    ocupadaRef.current = false;
    setAnalizandoPaquete(false);
    setConfirmandoPaquete(false);
  };

  const listos = paquetes.filter((p) => p.estado === "listo");
  const informados = paquetes.filter((p) => p.vistaPrevia);
  const importados = paquetes.filter((p) => p.resultado);
  const totalDetectado = informados.reduce((s, p) => s + (p.vistaPrevia?.total ?? 0), 0);
  const resumenImportacion = importados.reduce(
    (s, p) => ({
      relacionados: s.relacionados + (p.resultado?.relacionados ?? 0),
      revision: s.revision + (p.resultado?.revision ?? 0),
      duplicados: s.duplicados + (p.resultado?.duplicados ?? 0),
      errores: s.errores + (p.resultado?.errores ?? 0),
    }),
    { relacionados: 0, revision: 0, duplicados: 0, errores: 0 },
  );

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
      <section className="resumen-carga" style={{ marginBottom: 20 }}>
        <h3>Importación masiva de paquetes PDF</h3>
        <p>
          Seleccione varios paquetes PDF. El análisis muestra los comprobantes antes de
          importar. Los paquetes se procesan uno por uno para proteger la memoria de la VPS.
        </p>
        <input
          type="file"
          multiple
          aria-label="Seleccionar paquetes PDF"
          accept=".pdf,application/pdf"
          disabled={analizandoPaquete || confirmandoPaquete}
          onChange={(e) => seleccionarPaquetes(e.target.files)}
        />
        <p>
          Paquetes seleccionados: {paquetes.length} · Analizados: {informados.length} ·
          Documentos detectados: {totalDetectado} · Importados: {importados.length}
        </p>
        <div className="acciones">
          <button
            type="button"
            disabled={!paquetes.length || analizandoPaquete || confirmandoPaquete}
            onClick={() => void ejecutarPaquetes(false)}
          >
            {analizandoPaquete ? "Analizando paquetes…" : "Analizar paquetes"}
          </button>
          <button
            type="button"
            disabled={!listos.length || analizandoPaquete || confirmandoPaquete}
            onClick={() => void ejecutarPaquetes(true)}
          >
            {confirmandoPaquete ? "Importando paquetes…" : `Importar selección de ${listos.length} paquete(s)`}
          </button>
        </div>
        {progresoPaquetes && <p role="status">{progresoPaquetes}</p>}
        {errorPaquete && <p role="alert">{errorPaquete}</p>}
        {importados.length > 0 && (
          <p>
            Relacionados: {resumenImportacion.relacionados} · Revisión: {resumenImportacion.revision}
            {" · "}Duplicados: {resumenImportacion.duplicados} · Errores: {resumenImportacion.errores}
          </p>
        )}
        {paquetes.length > 0 && (
          <div style={{ maxHeight: 430, overflow: "auto" }}>
            <table>
              <thead>
                <tr>
                  <th>Paquete</th><th>Estado</th><th>Comprobantes</th><th>Resultado</th>
                </tr>
              </thead>
              <tbody>
                {paquetes.map((p) => (
                  <tr key={p.id}>
                    <td>{p.archivo.name}</td>
                    <td>{p.estado}</td>
                    <td>{p.vistaPrevia?.total ?? "—"}</td>
                    <td>
                      {p.error ?? (
                        p.resultado
                          ? `Relacionados ${p.resultado.relacionados ?? 0}, revisión ${p.resultado.revision ?? 0}, duplicados ${p.resultado.duplicados ?? 0}, errores ${p.resultado.errores ?? 0}`
                          : p.vistaPrevia
                            ? (
                              <div>
                                <strong>{p.indicesSeleccionados?.length ?? 0} seleccionados</strong>
                                {p.vistaPrevia.documentos.map((d, indice) => (
                                  <label key={indice} style={{ display: "block" }}>
                                    <input
                                      type="checkbox"
                                      checked={p.indicesSeleccionados?.includes(indice) ?? false}
                                      disabled={analizandoPaquete || confirmandoPaquete}
                                      onChange={(evento) =>
                                        actualizarPaquetes(paquetesRef.current.map((fila) =>
                                          fila.id === p.id
                                            ? {
                                                ...fila,
                                                indicesSeleccionados: evento.target.checked
                                                  ? [...(fila.indicesSeleccionados ?? []), indice]
                                                  : (fila.indicesSeleccionados ?? []).filter((i) => i !== indice),
                                              }
                                            : fila,
                                        ))
                                      }
                                    />
                                    {d.tipo} {d.serie}-{d.correlativo} (páginas {d.pagina_inicio}–{d.pagina_fin})
                                  </label>
                                ))}
                              </div>
                            )
                            : "Pendiente"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

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

      <section className="resumen-carga" aria-label="Captura de documentos" style={{ marginTop: 16, marginBottom: 20 }}>
        <h3>Capturar documentos con cámara o escáner</h3>
        <p>Puede fotografiar un documento desde el celular o cargar varias páginas digitalizadas a la vez. Los originales se procesan con el mismo OCR y control de duplicados.</p>
        <div className="acciones">
          <button type="button" onClick={() => entradaCamara.current?.click()}>
            Tomar foto de un documento
          </button>
          <button type="button" onClick={() => entradaEscaneos.current?.click()}>
            Cargar varios escaneos o fotos
          </button>
        </div>
        <input
          ref={entradaCamara}
          type="file"
          accept="image/*"
          capture="environment"
          hidden
          aria-label="Tomar foto con la cámara posterior"
          onChange={(e) => { agregar(e.target.files); e.target.value = ""; }}
        />
        <input
          ref={entradaEscaneos}
          type="file"
          accept=".pdf,image/jpeg,image/png,image/tiff,image/webp"
          multiple
          hidden
          aria-label="Seleccionar varios documentos escaneados"
          onChange={(e) => { agregar(e.target.files); e.target.value = ""; }}
        />
        <p className="tenue">La cámara se abre en dispositivos compatibles. Cada archivo se conserva como evidencia independiente; la unión de páginas, recorte automático y corrección de perspectiva son mejoras posteriores.</p>
      </section>

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
        {resultado.estado === "duplicado" && resultado.expedienteId ? (
          <Link to={`/expedientes/${resultado.expedienteId}`}>Ver factura registrada</Link>
        ) : documento?.expediente_id ? (
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
