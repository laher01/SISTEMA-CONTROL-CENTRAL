import { useEffect, useState } from "react";

const BASE = import.meta.env.VITE_API_URL ?? "";

export class ErrorApi extends Error {
  readonly status: number;
  readonly detalle: unknown;

  constructor(status: number, detalle: unknown) {
    super(mensajeDeDetalle(status, detalle));
    this.status = status;
    this.detalle = detalle;
  }
}

export function mensajeDeDetalle(status: number, detalle: unknown): string {
  if (typeof detalle === "string") return detalle;
  if (detalle && typeof detalle === "object" && "mensaje" in detalle) {
    return String(detalle.mensaje);
  }
  if (Array.isArray(detalle) && detalle.length > 0) {
    const primero: unknown = detalle[0];
    if (primero && typeof primero === "object" && "msg" in primero) return String(primero.msg);
  }
  return `Error ${status}`;
}

async function solicitar<T>(ruta: string, init?: RequestInit): Promise<T> {
  const respuesta = await fetch(`${BASE}${ruta}`, { credentials: "include", ...init });
  const cuerpo: unknown = respuesta.headers.get("content-type")?.includes("json")
    ? await respuesta.json()
    : await respuesta.text();
  if (!respuesta.ok) {
    const detalle = cuerpo && typeof cuerpo === "object" && "detail" in cuerpo ? cuerpo.detail : cuerpo;
    throw new ErrorApi(respuesta.status, detalle);
  }
  return cuerpo as T;
}

export function obtener<T>(ruta: string): Promise<T> {
  return solicitar<T>(ruta);
}

export function enviarJson<T>(
  ruta: string,
  metodo: "POST" | "PUT" | "PATCH",
  datos?: unknown,
): Promise<T> {
  return solicitar<T>(ruta, {
    method: metodo,
    headers: { "Content-Type": "application/json" },
    body: datos === undefined ? undefined : JSON.stringify(datos),
  });
}

export function enviarFormulario<T>(ruta: string, formulario: FormData): Promise<T> {
  return solicitar<T>(ruta, { method: "POST", body: formulario });
}

export function eliminar(ruta: string): Promise<unknown> {
  return solicitar<unknown>(ruta, { method: "DELETE" });
}

export function urlAdjuntoChat(mensajeId: string): string {
  return `${BASE}/api/v1/chat/mensajes/${mensajeId}/archivo`;
}

export function urlPdfExpediente(expedienteId: string): string {
  return `${BASE}/api/v1/expedientes/${expedienteId}/descargar-pdf`;
}

export function urlZipExpediente(expedienteId: string): string {
  return `${BASE}/api/v1/expedientes/${expedienteId}/descargar-zip`;
}

export function urlArchivo(documentoId: string): string {
  return `${BASE}/api/v1/documentos/${documentoId}/archivo`;
}

export function conParametros(ruta: string, parametros: Record<string, string | undefined>): string {
  const busqueda = new URLSearchParams();
  for (const [clave, valor] of Object.entries(parametros)) {
    if (valor !== undefined && valor !== "") busqueda.set(clave, valor);
  }
  const texto = busqueda.toString();
  return texto ? `${ruta}?${texto}` : ruta;
}

interface Estado<T> {
  ruta: string;
  version: number;
  datos?: T;
  error?: string;
}

export function useDatos<T>(ruta: string) {
  const [version, setVersion] = useState(0);
  const [estado, setEstado] = useState<Estado<T>>({ ruta: "", version: -1 });

  useEffect(() => {
    let vigente = true;
    obtener<T>(ruta).then(
      (datos) => vigente && setEstado({ ruta, version, datos }),
      (error: unknown) =>
        vigente &&
        setEstado({ ruta, version, error: error instanceof Error ? error.message : String(error) }),
    );
    return () => {
      vigente = false;
    };
  }, [ruta, version]);

  const actual = estado.ruta === ruta;
  return {
    datos: actual ? estado.datos : undefined,
    error: actual ? estado.error : undefined,
    cargando: !actual || estado.version !== version,
    recargar: () => setVersion((v) => v + 1),
  };
}


export async function imprimirExpedientes(
  expedienteIds: string[],
): Promise<{ expedientes: number; pdfs: number; sinPdf: number }> {
  const ventana = window.open("", "_blank");
  if (ventana) {
    ventana.document.title = "Preparando impresión · FACT CENTRAL";
    ventana.document.body.innerHTML = "<p>Preparando documentos para impresión…</p>";
  }

  try {
    const respuesta = await fetch(`${BASE}/api/v1/expedientes/imprimir-lote`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expediente_ids: expedienteIds }),
    });
    if (!respuesta.ok) {
      const cuerpo: unknown = respuesta.headers.get("content-type")?.includes("json")
        ? await respuesta.json()
        : await respuesta.text();
      const detalle =
        cuerpo && typeof cuerpo === "object" && "detail" in cuerpo ? cuerpo.detail : cuerpo;
      throw new ErrorApi(respuesta.status, detalle);
    }

    const blob = await respuesta.blob();
    const url = URL.createObjectURL(blob);
    const expedientes = Number(respuesta.headers.get("X-Expedientes-Impresos") ?? "0");
    const pdfs = Number(respuesta.headers.get("X-Pdfs-Impresos") ?? "0");
    const sinPdf = Number(respuesta.headers.get("X-Expedientes-Sin-Pdf") ?? "0");

    if (ventana) {
      ventana.location.href = url;
      window.setTimeout(() => {
        try {
          ventana.print();
        } catch {
          // El visor PDF del navegador conserva igualmente el documento abierto para imprimir.
        }
      }, 1500);
      window.setTimeout(() => URL.revokeObjectURL(url), 120000);
    } else {
      const enlace = document.createElement("a");
      enlace.href = url;
      enlace.target = "_blank";
      enlace.rel = "noopener";
      enlace.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 120000);
    }

    return { expedientes, pdfs, sinPdf };
  } catch (error) {
    ventana?.close();
    throw error;
  }
}
