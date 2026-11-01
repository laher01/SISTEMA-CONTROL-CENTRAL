import { formatearMonto } from "../formato";
import type { Moneda } from "../tipos";

export type FilaClasificacion = {
  agente_retencion: boolean;
  moneda: Moneda;
  bancarizable: boolean;
  cantidad: number;
  monto: string;
};

export default function ResumenClasificacion({
  filas,
}: {
  filas: FilaClasificacion[];
}) {
  const combinaciones = [
    { agente: true, bancarizable: true, titulo: "Agente · bancarizable" },
    { agente: true, bancarizable: false, titulo: "Agente · no bancarizable" },
    { agente: false, bancarizable: true, titulo: "Sin agente · bancarizable" },
    { agente: false, bancarizable: false, titulo: "Sin agente · no bancarizable" },
  ];

  return (
    <section className="resumen-clasificacion" aria-label="Resumen por retención y bancarización">
      {combinaciones.map((grupo) => {
        const importes = filas.filter(
          (fila) => fila.agente_retencion === grupo.agente && fila.bancarizable === grupo.bancarizable,
        );
        const monedas: Moneda[] = ["PEN", "USD"];
        return (
          <div className="resumen-clasificacion__grupo" key={grupo.titulo}>
            <strong>{grupo.titulo}</strong>
            {monedas.map((moneda) => {
              const coincidencias = importes.filter((fila) => fila.moneda === moneda);
              const total = coincidencias.reduce((suma, fila) => suma + Number(fila.monto), 0);
              const cantidad = coincidencias.reduce((suma, fila) => suma + fila.cantidad, 0);
              return (
                <span key={moneda}>
                  {moneda} {formatearMonto(moneda, String(total))} · {cantidad} exp.
                </span>
              );
            })}
          </div>
        );
      })}
    </section>
  );
}
