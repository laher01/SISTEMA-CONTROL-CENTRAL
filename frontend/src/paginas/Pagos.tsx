import { useMemo, useState, type FormEvent } from "react";

import { eliminar, enviarJson, useDatos } from "../api";
import { formatearFecha, formatearMonto } from "../formato";
import type {
  AdelantoERP,
  CuentaPagoERP,
  FiltroOpcion,
  PagoERP,
  PlanLiquidacion,
  SesionActual,
} from "../tipos";

export default function Pagos({ sesion }: { sesion: SesionActual }) {
  const usuarios = useDatos<FiltroOpcion[]>("/api/v1/pagos/usuarios");
  const planes = useDatos<PlanLiquidacion[]>("/api/v1/pagos/planes");
  const cuentas = useDatos<CuentaPagoERP[]>("/api/v1/pagos/cuentas");
  const adelantos = useDatos<AdelantoERP[]>("/api/v1/pagos/adelantos");
  const pagos = useDatos<PagoERP[]>("/api/v1/pagos");

  const [usuarioId, setUsuarioId] = useState("");
  const [mensaje, setMensaje] = useState("");

  const nombreUsuario = (id: string) => {
    const u = usuarios.datos?.find((x) => x.id === id);
    return u ? u.codigo + " · " + u.nombre : id;
  };

  const recargarTodo = () => {
    planes.recargar();
    cuentas.recargar();
    adelantos.recargar();
    pagos.recargar();
  };

  return (
    <>
      <h2>Pagos ERP</h2>
      <p className="tenue">
        Liquidaciones separadas de Billing SaaS. Producción por Usuario, planes,
        adelantos, programación, pago y conciliación.
      </p>

      <div className="filtros">
        <select value={usuarioId} onChange={(e) => setUsuarioId(e.target.value)}>
          <option value="">Selecciona un Usuario</option>
          {usuarios.datos?.map((u) => (
            <option key={u.id} value={u.id}>{u.codigo} · {u.nombre}</option>
          ))}
        </select>
      </div>

      {usuarioId && (
        <div className="columnas">
          <PlanForm usuarioId={usuarioId} alCrear={() => { planes.recargar(); setMensaje("Plan creado."); }} />
          <AdelantoForm usuarioId={usuarioId} alCrear={() => { adelantos.recargar(); setMensaje("Adelanto registrado."); }} />
          <CuentaForm usuarioId={usuarioId} alCrear={() => { cuentas.recargar(); setMensaje("Cuenta registrada."); }} />
          <ProgramarPagoForm
            usuarioId={usuarioId}
            alCrear={() => {
              recargarTodo();
              setMensaje("Pago programado con producción y adelantos calculados.");
            }}
          />
        </div>
      )}

      {mensaje && <p className="resumen-carga">{mensaje}</p>}

      <h3>Pagos programados</h3>
      <div className="tabla-responsive">
        <table>
          <thead>
            <tr>
              <th>Usuario</th>
              <th>Periodo</th>
              <th>Moneda</th>
              <th className="num">Producción</th>
              <th className="num">%</th>
              <th className="num">Bruto</th>
              <th className="num">Adelantos</th>
              <th className="num">Ajustes</th>
              <th className="num">Saldo</th>
              <th>Estado</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {pagos.datos?.map((pago) => (
              <tr key={pago.id}>
                <td>{nombreUsuario(pago.usuario_id)}</td>
                <td>{formatearFecha(pago.periodo_desde)} – {formatearFecha(pago.periodo_hasta)}</td>
                <td>{pago.moneda}</td>
                <td className="num">{formatearMonto(pago.moneda, pago.produccion_total)}</td>
                <td className="num">{pago.porcentaje}%</td>
                <td className="num">{formatearMonto(pago.moneda, pago.bruto)}</td>
                <td className="num">{formatearMonto(pago.moneda, pago.adelantos)}</td>
                <td className="num">{formatearMonto(pago.moneda, pago.ajustes)}</td>
                <td className="num">{formatearMonto(pago.moneda, pago.saldo)}</td>
                <td>{pago.estado}</td>
                <td>
                  <AccionesPago pago={pago} sesion={sesion} alCambiar={pagos.recargar} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="columnas">
        <section>
          <h3>Planes vigentes</h3>
          <table>
            <thead><tr><th>Usuario</th><th>Plan</th><th>%</th><th>Desde</th></tr></thead>
            <tbody>
              {planes.datos?.map((p) => (
                <tr key={p.id}>
                  <td>{nombreUsuario(p.usuario_id)}</td>
                  <td>{p.nombre}</td>
                  <td>{p.porcentaje}%</td>
                  <td>{formatearFecha(p.vigencia_desde)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section>
          <h3>Adelantos</h3>
          <table>
            <thead><tr><th>Usuario</th><th>Fecha</th><th>Monto</th><th>Aplicado</th></tr></thead>
            <tbody>
              {adelantos.datos?.map((a) => (
                <tr key={a.id}>
                  <td>{nombreUsuario(a.usuario_id)}</td>
                  <td>{formatearFecha(a.fecha)}</td>
                  <td>{formatearMonto(a.moneda, a.monto)}</td>
                  <td>{a.aplicado ? "Sí" : "No"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </>
  );
}

function PlanForm({ usuarioId, alCrear }: { usuarioId: string; alCrear: () => void }) {
  const [nombre, setNombre] = useState("Plan base");
  const [porcentaje, setPorcentaje] = useState("1.5");
  const [desde, setDesde] = useState(new Date().toISOString().slice(0, 10));

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    await enviarJson<PlanLiquidacion>("/api/v1/pagos/planes", "POST", {
      usuario_id: usuarioId,
      nombre,
      porcentaje,
      vigencia_desde: desde,
      vigencia_hasta: null,
    });
    alCrear();
  };

  return (
    <section>
      <h3>Plan de liquidación</h3>
      <form onSubmit={enviar} className="formulario-pagos">
        <input value={nombre} onChange={(e) => setNombre(e.target.value)} required />
        <input
          type="number"
          step="0.0001"
          min="0"
          max="100"
          value={porcentaje}
          onChange={(e) => setPorcentaje(e.target.value)}
          required
        />
        <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} required />
        <button type="submit">Crear plan</button>
      </form>
    </section>
  );
}

function AdelantoForm({ usuarioId, alCrear }: { usuarioId: string; alCrear: () => void }) {
  const [fecha, setFecha] = useState(new Date().toISOString().slice(0, 10));
  const [monto, setMonto] = useState("");
  const [moneda, setMoneda] = useState<"PEN" | "USD">("PEN");
  const [descripcion, setDescripcion] = useState("");

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    await enviarJson<AdelantoERP>("/api/v1/pagos/adelantos", "POST", {
      usuario_id: usuarioId,
      fecha,
      moneda,
      monto,
      descripcion: descripcion || null,
    });
    setMonto("");
    setDescripcion("");
    alCrear();
  };

  return (
    <section>
      <h3>Registrar adelanto</h3>
      <form onSubmit={enviar} className="formulario-pagos">
        <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} required />
        <select value={moneda} onChange={(e) => setMoneda(e.target.value as "PEN" | "USD")}>
          <option value="PEN">PEN</option>
          <option value="USD">USD</option>
        </select>
        <input
          type="number"
          step="0.01"
          min="0.01"
          placeholder="Monto"
          value={monto}
          onChange={(e) => setMonto(e.target.value)}
          required
        />
        <input
          placeholder="Descripción"
          value={descripcion}
          onChange={(e) => setDescripcion(e.target.value)}
        />
        <button type="submit">Registrar adelanto</button>
      </form>
    </section>
  );
}

function CuentaForm({ usuarioId, alCrear }: { usuarioId: string; alCrear: () => void }) {
  const [titular, setTitular] = useState("");
  const [banco, setBanco] = useState("");
  const [tipo, setTipo] = useState("AHORROS");
  const [moneda, setMoneda] = useState<"PEN" | "USD">("PEN");
  const [cuenta, setCuenta] = useState("");
  const [cci, setCci] = useState("");

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    await enviarJson<CuentaPagoERP>("/api/v1/pagos/cuentas", "POST", {
      usuario_id: usuarioId,
      titular,
      banco,
      tipo_cuenta: tipo,
      moneda,
      numero_cuenta: cuenta || null,
      cci: cci || null,
      porcentaje_distribucion: "100",
    });
    alCrear();
  };

  return (
    <section>
      <h3>Cuenta de pago</h3>
      <form onSubmit={enviar} className="formulario-pagos">
        <input placeholder="Titular" value={titular} onChange={(e) => setTitular(e.target.value)} required />
        <input placeholder="Banco" value={banco} onChange={(e) => setBanco(e.target.value)} required />
        <input placeholder="Tipo de cuenta" value={tipo} onChange={(e) => setTipo(e.target.value)} required />
        <select value={moneda} onChange={(e) => setMoneda(e.target.value as "PEN" | "USD")}>
          <option value="PEN">PEN</option>
          <option value="USD">USD</option>
        </select>
        <input placeholder="N.º cuenta" value={cuenta} onChange={(e) => setCuenta(e.target.value)} />
        <input placeholder="CCI" value={cci} onChange={(e) => setCci(e.target.value)} />
        <button type="submit">Guardar cuenta</button>
      </form>
    </section>
  );
}

function ProgramarPagoForm({
  usuarioId,
  alCrear,
}: {
  usuarioId: string;
  alCrear: () => void;
}) {
  const hoy = new Date();
  const primero = new Date(hoy.getFullYear(), hoy.getMonth(), 1).toISOString().slice(0, 10);
  const [desde, setDesde] = useState(primero);
  const [hasta, setHasta] = useState(hoy.toISOString().slice(0, 10));
  const [moneda, setMoneda] = useState<"PEN" | "USD">("PEN");
  const [ajustes, setAjustes] = useState("0");

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    await enviarJson<PagoERP>("/api/v1/pagos", "POST", {
      usuario_id: usuarioId,
      periodo_desde: desde,
      periodo_hasta: hasta,
      moneda,
      ajustes,
      fecha_programada: null,
    });
    alCrear();
  };

  return (
    <section>
      <h3>Programar liquidación</h3>
      <form onSubmit={enviar} className="formulario-pagos">
        <label>Desde<input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} /></label>
        <label>Hasta<input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} /></label>
        <select value={moneda} onChange={(e) => setMoneda(e.target.value as "PEN" | "USD")}>
          <option value="PEN">PEN</option>
          <option value="USD">USD</option>
        </select>
        <input
          type="number"
          step="0.01"
          value={ajustes}
          onChange={(e) => setAjustes(e.target.value)}
          placeholder="Ajustes"
        />
        <button type="submit">Calcular y programar</button>
      </form>
    </section>
  );
}

function AccionesPago({
  pago,
  sesion,
  alCambiar,
}: {
  pago: PagoERP;
  sesion: SesionActual;
  alCambiar: () => void;
}) {
  const acciones = useMemo(() => {
    const a: string[] = [];
    if (pago.estado === "PROGRAMADO") a.push("APROBADO");
    if (sesion.rol === "GERENTE" && pago.estado === "APROBADO") a.push("PAGADO");
    if (sesion.rol === "GERENTE" && pago.estado === "PAGADO") a.push("CONCILIADO");
    return a;
  }, [pago.estado, sesion.rol]);

  return (
    <div className="acciones-documento">
      {acciones.map((estado) => (
        <button
          key={estado}
          onClick={async () => {
            await enviarJson<PagoERP>("/api/v1/pagos/" + pago.id, "PATCH", {
              estado,
              fecha_pago: estado === "PAGADO" ? new Date().toISOString().slice(0, 10) : null,
              conciliado: estado === "CONCILIADO" ? true : null,
            });
            alCambiar();
          }}
        >
          {estado}
        </button>
      ))}

      {(sesion.rol === "SUPERADMIN" || sesion.rol === "ADMINISTRADOR") &&
        pago.estado !== "PAGADO" &&
        pago.estado !== "CONCILIADO" &&
        !pago.conciliado && (
          <button
            onClick={async () => {
              const confirmar = window.confirm(
                "¿Eliminar esta programación de pago? Esta acción quedará registrada en auditoría.",
              );
              if (!confirmar) return;
              await eliminar("/api/v1/pagos/" + pago.id);
              alCambiar();
            }}
          >
            Eliminar
          </button>
        )}
    </div>
  );
}
