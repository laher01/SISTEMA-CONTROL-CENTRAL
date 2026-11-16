import { useState } from "react";

type Listado = "expedientes" | "documentos" | "registros";

export default function ExportarExcel({ listado, ruta }: { listado: Listado; ruta: string }) {
  const [exportando, setExportando] = useState(false);
  const [fallo, setFallo] = useState<{ ruta: string; texto: string }>();
  const filtros = new URLSearchParams(ruta.split("?")[1]);
  filtros.delete("limit");
  filtros.delete("offset");
  const filtrado = filtros.size > 0;

  async function descargar() {
    setExportando(true);
    setFallo(undefined);
    filtros.set("formato", "xlsx");
    try {
      const respuesta = await fetch(
        `${import.meta.env.VITE_API_URL ?? ""}/api/v1/${listado}?${filtros}`,
        { credentials: "include" },
      );
      if (!respuesta.ok || !respuesta.headers.get("content-type")?.includes("spreadsheetml.sheet")) {
        throw new Error("No se pudo exportar el listado. Actualiza la página e inténtalo de nuevo.");
      }
      const enlace = document.createElement("a");
      const objeto = URL.createObjectURL(await respuesta.blob());
      enlace.href = objeto;
      enlace.download = `${listado}-filtrados.xlsx`;
      enlace.click();
      window.setTimeout(() => URL.revokeObjectURL(objeto), 1000);
    } catch (error) {
      setFallo({ ruta, texto: error instanceof Error ? error.message : String(error) });
    } finally {
      setExportando(false);
    }
  }

  return <div className="acciones">
    <button type="button" disabled={!filtrado || exportando} onClick={() => void descargar()}>
      <svg width="19" height="19" viewBox="0 0 24 24" aria-hidden="true"
        style={{ verticalAlign: "middle", marginRight: 6 }}>
        <rect x="9" y="3" width="13" height="18" rx="2" fill="#107c41" />
        <path d="M13 7h6m-6 5h6m-6 5h6" stroke="#a9dfbf" />
        <rect x="2" y="6" width="13" height="12" rx="1" fill="#185c37" />
        <path d="m6 9 5 6m0-6-5 6" stroke="white" strokeWidth="1.6" />
      </svg>
      {exportando ? "Exportando…" : "Exportar a Excel"}
    </button>
    {!filtrado && <small>Aplica un filtro para exportar.</small>}
    {fallo?.ruta === ruta && <p role="alert">{fallo.texto}</p>}
  </div>;
}
