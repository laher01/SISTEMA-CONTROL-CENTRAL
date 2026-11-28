import { obtener } from "./api";
import type { Empresa } from "./tipos";

type Coactiva = { estado: string; monto?: string };
type SSCO = { estado: string; corte?: string; desactualizado?: boolean };
export type HallazgoEmpresa = { ruc: string; razon: string; deuda?: string; ssco?: string };
export type AvisoEmpresas = { hallazgos: HallazgoEmpresa[]; incompleta: boolean };

export async function consultarAvisoEmpresas(signal: AbortSignal): Promise<AvisoEmpresas> {
  const aviso: AvisoEmpresas = { hallazgos: [], incompleta: false };
  try {
    const visibles = await obtener<Empresa[]>("/api/v1/empresas", signal);
    const empresas = [...new Map(visibles.map(empresa => [empresa.ruc, empresa])).values()];
    for (let i = 0; i < empresas.length && !signal.aborted; i += 2) {
      await Promise.all(empresas.slice(i, i + 2).map(async empresa => {
        const ruta = "/api/v1/empresas/consultas";
        const ruc = encodeURIComponent(empresa.ruc);
        const [deuda, ssco] = await Promise.allSettled([
          obtener<Coactiva>(`${ruta}/coactiva/${ruc}`, signal),
          obtener<SSCO>(`${ruta}/ssco/${ruc}`, signal),
        ]);
        const d = deuda.status === "fulfilled" ? deuda.value : undefined;
        const s = ssco.status === "fulfilled" ? ssco.value : undefined;
        aviso.incompleta ||= !d || !s || Boolean(s.desactualizado);
        const hallazgo: HallazgoEmpresa = { ruc: empresa.ruc, razon: empresa.razon_social };
        if (d?.estado === "Con deuda") hallazgo.deuda = d.monto ?? "";
        if (s?.estado === "Figura en el padrón") hallazgo.ssco = s.corte ?? "";
        if (hallazgo.deuda !== undefined || hallazgo.ssco !== undefined) aviso.hallazgos.push(hallazgo);
      }));
    }
  } catch {
    aviso.incompleta = true;
  }
  aviso.hallazgos.sort((a, b) => a.razon.localeCompare(b.razon, "es") || a.ruc.localeCompare(b.ruc));
  return aviso;
}
