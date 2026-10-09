import ConsolidadoGerencia from "./ConsolidadoGerencia";
import { useMemo, useState, type FormEvent } from "react";

import { conParametros, eliminar, enviarJson, useDatos } from "../api";
import { formatearFecha, formatearMonto } from "../formato";
import LiquidacionMultimes from "./LiquidacionMultimes";
import ComisionesResponsables from "./ComisionesResponsables";
import type {
  AbonoClienteERP,
  AdelantoERP,
  CarteraClientesResumen,
  CuentaPagoERP,
  FiltroOpcion,
  Miembro,
  PagoERP,
  PedidoGerencia,
  PlanLiquidacion,
  SesionActual,
} from "../tipos";

type PestanaPagos = "PEDIDOS" | "COBROS" | "LIQUIDACIONES" | "RESPONSABLES";

function mesActual(): string {
  return new Date().toISOString().slice(0, 7);
}

export default function Pagos({ sesion }: { sesion: SesionActual }) {
  const [pestana, setPestana] = useState<PestanaPagos>("PEDIDOS");
  const [mesLiquidacion, setMesLiquidacion] = useState(mesActual());
  const [mes, setMes] = useState(mesActual());
  const [moneda, setMoneda] = useState<"PEN" | "USD">("PEN");
  const [usuarioId, setUsuarioId] = useState("");
  const [mensaje, setMensaje] = useState("");

  const usuarios = useDatos<FiltroOpcion[]>("/api/v1/pagos/usuarios");
  const responsables = useDatos<FiltroOpcion[]>("/api/v1/pagos/responsables");
  const clientes = useDatos<FiltroOpcion[]>("/api/v1/pagos/clientes");
  const proveedores = useDatos<FiltroOpcion[]>("/api/v1/pagos/proveedores");
  const gestores = useDatos<FiltroOpcion[]>("/api/v1/pagos/gestores");
  const miembros = useDatos<Miembro[]>(sesion.rol === "GERENTE" ? null : "/api/v1/miembros");
  const planes = useDatos<PlanLiquidacion[]>(sesion.rol === "GERENTE" ? null : "/api/v1/pagos/planes");
  const cuentas = useDatos<CuentaPagoERP[]>(sesion.rol === "GERENTE" ? null : "/api/v1/pagos/cuentas");
  const adelantos = useDatos<AdelantoERP[]>(sesion.rol === "GERENTE" ? null : "/api/v1/pagos/adelantos");
  const pagos = useDatos<PagoERP[]>(sesion.rol === "GERENTE" ? null : "/api/v1/pagos");
  const pedidos = useDatos<PedidoGerencia[]>(
    conParametros("/api/v1/pagos/pedidos", { mes, moneda }),
  );
  const cartera = useDatos<CarteraClientesResumen>(
    sesion.rol === "GERENTE" ? null : conParametros("/api/v1/pagos/clientes/resumen", { mes, moneda }),
  );

  const usuarioSeleccionado = usuarios.datos?.find((u) => u.id === usuarioId);
  const porcentajePredeterminado = usuarioSeleccionado?.porcentaje_produccion ?? "0";

  const nombreUsuario = (id: string) => {
    const u = usuarios.datos?.find((x) => x.id === id);
    return u ? u.codigo + " · " + u.nombre : id;
  };

  const recargarPedidosYCobros = () => {
    pedidos.recargar();
    cartera.recargar();
  };

  return (
    <>
      <h2>Pagos ERP</h2>
      <p className="tenue">
        Pedidos de Gerencia, cartera de Clientes y liquidación de producción son procesos
        independientes, pero comparten la misma fuente de verdad: los Expedientes procesados.
      </p>

      <div className="acciones">
        <button
          className={pestana === "PEDIDOS" ? "activo" : undefined}
          onClick={() => setPestana("PEDIDOS")}
        >
          Pedidos de Gerencia
        </button>
        <button
          className={pestana === "COBROS" ? "activo" : undefined}
          onClick={() => setPestana("COBROS")}
        >
          Consolidado
        </button>
        <button
          className={pestana === "RESPONSABLES" ? "activo" : undefined}
          onClick={() => setPestana("RESPONSABLES")}
        >
          Pago a Responsables
        </button>
        {sesion.rol !== "GERENTE" && <button
          className={pestana === "LIQUIDACIONES" ? "activo" : undefined}
          onClick={() => setPestana("LIQUIDACIONES")}
        >
          Liquidación de usuarios
        </button>}
      </div>

      {pestana === "PEDIDOS" && (
        <div className="filtros">
          <label>
            Mes
            <input type="month" value={mes} onChange={(e) => setMes(e.target.value)} />
          </label>
          <label>
            Moneda
            <select value={moneda} onChange={(e) => setMoneda(e.target.value as "PEN" | "USD")}>
              <option value="PEN">PEN</option>
              <option value="USD">USD</option>
            </select>
          </label>
        </div>
      )}

      {mensaje && <p className="resumen-carga">{mensaje}</p>}

      {pestana === "PEDIDOS" && (
        <PedidosGerencia
          gerentes={(miembros.datos ?? []).filter((m) => m.rol === "GERENTE").map((m) => ({ id: m.id, codigo: m.codigo, nombre: m.nombre, usuario_id: null, porcentaje_produccion: null }))}
          esGerente={sesion.rol === "GERENTE"}
          mes={mes}
          moneda={moneda}
          pedidos={pedidos.datos ?? []}
          clientes={clientes.datos ?? []}
          responsables={responsables.datos ?? []}
          usuarios={usuarios.datos ?? []}
          gestores={gestores.datos ?? []}
          proveedores={proveedores.datos ?? []}
          error={pedidos.error}
          alCambiar={() => {
            recargarPedidosYCobros();
            setMensaje("Pedido de Gerencia actualizado.");
          }}
          alMensaje={setMensaje}
        />
      )}

      {pestana === "COBROS" && sesion.rol === "ADMINISTRADOR" && (
        <CobrosClientes
          mes={mes}
          moneda={moneda}
          resumen={cartera.datos}
          clientes={clientes.datos ?? []}
          error={cartera.error}
          alCambiar={() => {
            recargarPedidosYCobros();
            setMensaje("Cartera de clientes actualizada.");
          }}
          alMensaje={setMensaje}
        />
      )}

      {pestana === "COBROS" && <ConsolidadoGerencia />}

      {pestana === "RESPONSABLES" && <ComisionesResponsables sesion={sesion} />}

      {pestana === "LIQUIDACIONES" && sesion.rol !== "GERENTE" && (
        <>
          <label>Mes a liquidar <input type="month" value={mesLiquidacion} onChange={(e) => setMesLiquidacion(e.target.value)} /></label>
          <div className="filtros">
            <select value={usuarioId} onChange={(e) => setUsuarioId(e.target.value)}>
              <option value="">Selecciona un Usuario</option>
              {usuarios.datos?.map((u) => (
                <option key={u.id} value={u.id}>{u.codigo} · {u.nombre}</option>
              ))}
            </select>
            {usuarioSeleccionado && (
              <span className="tenue">
                % predeterminado: {usuarioSeleccionado.porcentaje_produccion ?? "Sin definir"}%
              </span>
            )}
          </div>

          {usuarioId && <LiquidacionMultimes
            key={usuarioId + moneda}
            usuarioId={usuarioId}
            moneda={moneda}
            porcentajeInicial={porcentajePredeterminado}
            alCambiar={() => { pagos.recargar(); adelantos.recargar(); }}
          />}

          {usuarioId && (
            <div className="columnas">
              <PlanForm
                key={usuarioId + porcentajePredeterminado}
                usuarioId={usuarioId}
                porcentajeInicial={porcentajePredeterminado}
                alCrear={() => {
                  planes.recargar();
                  setMensaje("Plan creado.");
                }}
              />
              <AdelantoForm
                usuarioId={usuarioId}
                alCrear={() => {
                  adelantos.recargar();
                  setMensaje("Adelanto registrado.");
                }}
              />
              <CuentaForm
                usuarioId={usuarioId}
                alCrear={() => {
                  cuentas.recargar();
                  setMensaje("Cuenta registrada.");
                }}
              />
            </div>
          )}

          <Liquidaciones
            pagos={(pagos.datos ?? []).filter((p) => p.periodo_desde.startsWith(mesLiquidacion) || p.periodo_hasta.startsWith(mesLiquidacion))}
            planes={planes.datos ?? []}
            adelantos={adelantos.datos ?? []}
            sesion={sesion}
            nombreUsuario={nombreUsuario}
            alCambiar={pagos.recargar}
          />
        </>
      )}
    </>
  );
}

function PedidosGerencia({
  gerentes,
  esGerente,
  mes,
  moneda,
  pedidos,
  clientes,
  responsables,
  usuarios,
  gestores,
  proveedores,
  error,
  alCambiar,
  alMensaje,
}: {
  gerentes: FiltroOpcion[];
  esGerente: boolean;
  mes: string;
  moneda: "PEN" | "USD";
  pedidos: PedidoGerencia[];
  clientes: FiltroOpcion[];
  responsables: FiltroOpcion[];
  usuarios: FiltroOpcion[];
  gestores: FiltroOpcion[];
  proveedores: FiltroOpcion[];
  error?: string;
  alCambiar: () => void;
  alMensaje: (mensaje: string) => void;
}) {
  const [gerenteId, setGerenteId] = useState("");
  const [clienteId, setClienteId] = useState("");
  const [responsableId, setResponsableId] = useState("");
  const [monto, setMonto] = useState("");
  const [modalidad, setModalidad] = useState<"POR_PEDIDO" | "SIN_RESTRICCION">("POR_PEDIDO");
  const [modo, setModo] = useState<"MANUAL" | "SEMIASISTIDA" | "AUTOMATICA">("MANUAL");
  const [observacion, setObservacion] = useState("");
  const [seleccionado, setSeleccionado] = useState("");

  const pedidoSeleccionado = pedidos.find((p) => p.id === seleccionado) ?? pedidos[0];

  const crear = async (e: FormEvent) => {
    e.preventDefault();
    await enviarJson<PedidoGerencia>("/api/v1/pagos/pedidos", "POST", {
      cliente_id: clienteId,
      gerente_id: esGerente ? null : gerenteId,
      responsable_id: responsableId || null,
      periodo_mes: mes + "-01",
      moneda,
      monto_solicitado: monto,
      modalidad,
      modo_distribucion: responsableId ? "MANUAL" : modo,
      observacion: observacion || null,
    });
    setMonto("");
    setObservacion("");
    alCambiar();
  };

  return (
    <>
      <section>
        <h3>Nuevo Pedido de Gerencia</h3>
        <form onSubmit={crear} className="formulario-linea">
          {!esGerente && <select value={gerenteId} onChange={(e) => setGerenteId(e.target.value)} required>
            <option value="">Seleccionar Gerente</option>
            {gerentes.map((g) => <option key={g.id} value={g.id}>{g.codigo} · {g.nombre}</option>)}
          </select>}
          <select value={clienteId} onChange={(e) => setClienteId(e.target.value)} required>
            <option value="">Cliente receptor</option>
            {clientes.map((c) => (
              <option key={c.id} value={c.id}>{c.codigo} · {c.nombre}</option>
            ))}
          </select>
          <select value={responsableId} onChange={(e) => {
            setResponsableId(e.target.value);
            if (e.target.value) setModo("MANUAL");
          }} required>
            <option value="">Seleccionar Responsable</option>
            {responsables.map((r) => <option key={r.id} value={r.id}>{r.codigo} · {r.nombre}</option>)}
          </select>
          <input
            type="number"
            min="0.01"
            step="0.01"
            placeholder="Presupuesto bruto para Responsable"
            value={monto}
            onChange={(e) => setMonto(e.target.value)}
            required
          />
          <select value={modalidad} onChange={(e) => setModalidad(e.target.value as typeof modalidad)}>
            <option value="POR_PEDIDO">Por pedido</option>
            <option value="SIN_RESTRICCION">Sin restricción</option>
          </select>
          <select value={modo} disabled={Boolean(responsableId)} onChange={(e) => setModo(e.target.value as typeof modo)}>
            <option value="MANUAL">Distribución manual</option>
            <option value="SEMIASISTIDA">Semiasistida</option>
            <option value="AUTOMATICA">Automática inicial</option>
          </select>
          <input
            placeholder="Observación"
            value={observacion}
            onChange={(e) => setObservacion(e.target.value)}
          />
          <button type="submit">Crear pedido</button>
        </form>
        <p className="tenue">
          Gerencia asigna un presupuesto bruto al Responsable; el Responsable decide la distribución por Usuario.
          No se realiza una distribución automática al registrar el pedido.
        </p>
      </section>

      {error && <p className="error">{error}</p>}

      <h3>Pedidos del mes</h3>
      <div className="tabla-responsive">
        <table>
          <thead>
            <tr>
              <th>Cliente</th>
              <th>Modalidad</th>
              <th className="num">Solicitado</th>
              <th className="num">Asignado</th>
              <th className="num">Ejecutado</th>
              <th className="num">Pendiente</th>
              <th className="num">Exceso</th>
              <th className="num">Avance</th>
              <th>Concentración</th>
              <th>Estado</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {pedidos.map((p) => (
              <tr key={p.id}>
                <td>{p.cliente_ruc} · {p.cliente_razon_social}</td>
                <td>{p.modalidad} / {p.modo_distribucion}</td>
                <td className="num">{formatearMonto(p.moneda, p.monto_solicitado)}</td>
                <td className="num">{formatearMonto(p.moneda, p.monto_asignado)}</td>
                <td className="num">{formatearMonto(p.moneda, p.monto_ejecutado)}</td>
                <td className="num">{formatearMonto(p.moneda, p.saldo_pendiente)}</td>
                <td className="num">{formatearMonto(p.moneda, p.exceso)}</td>
                <td className="num">{p.avance_porcentaje}%</td>
                <td>
                  {p.concentracion_maxima_proveedor}%
                  {p.proveedor_mayor_concentracion && (
                    <small> · {p.proveedor_mayor_concentracion}</small>
                  )}
                </td>
                <td>{p.estado}</td>
                <td>
                  <button onClick={() => setSeleccionado(p.id)}>Detalle</button>{" "}
                  {p.estado !== "CANCELADO" && <button type="button" onClick={async () => {
                    const motivo = window.prompt("Motivo de anulación (mínimo 10 caracteres). No se permite anular pedidos ejecutados o con asignaciones.");
                    if (!motivo || motivo.trim().length < 10) return;
                    try {
                      await enviarJson<PedidoGerencia>(`/api/v1/pagos/pedidos/${p.id}/anular`, "POST", { motivo: motivo.trim() });
                      alMensaje("Pedido anulado con registro de auditoría.");
                      alCambiar();
                    } catch (error) {
                      alMensaje(error instanceof Error ? error.message : String(error));
                    }
                  }}>Anular</button>}{" "}
                  <button type="button" onClick={async () => {
                    if (!window.confirm(
                      "¿Eliminar este pedido? Solo se permite si no tiene asignaciones ni ejecución. La acción quedará auditada."
                    )) return;
                    try {
                      await eliminar(`/api/v1/pagos/pedidos/${p.id}`);
                      alMensaje("Pedido eliminado. Se conserva el registro de auditoría.");
                      setSeleccionado("");
                      alCambiar();
                    } catch (error) {
                      alMensaje(error instanceof Error ? error.message : String(error));
                    }
                  }}>Eliminar</button>{" "}
                  <button
                    onClick={async () => {
                      await enviarJson<PedidoGerencia>(
                        "/api/v1/pagos/pedidos/" + p.id,
                        "PATCH",
                        { estado: p.estado === "ACTIVO" ? "CERRADO" : "ACTIVO" },
                      );
                      alCambiar();
                    }}
                  >
                    {p.estado === "ACTIVO" ? "Cerrar" : "Reabrir"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {pedidoSeleccionado && !pedidoSeleccionado.responsable_id && (
        <DetallePedido
          pedido={pedidoSeleccionado}
          usuarios={usuarios}
          gestores={gestores}
          proveedores={proveedores}
          alCambiar={alCambiar}
          alMensaje={alMensaje}
        />
      )}
    </>
  );
}

function DetallePedido({
  pedido,
  usuarios,
  gestores,
  proveedores,
  alCambiar,
  alMensaje,
}: {
  pedido: PedidoGerencia;
  usuarios: FiltroOpcion[];
  gestores: FiltroOpcion[];
  proveedores: FiltroOpcion[];
  alCambiar: () => void;
  alMensaje: (mensaje: string) => void;
}) {
  const [usuarioId, setUsuarioId] = useState("");
  const [gestorId, setGestorId] = useState("");
  const [proveedorId, setProveedorId] = useState("");
  const [monto, setMonto] = useState("");

  const gestoresUsuario = gestores.filter((g) => !usuarioId || g.usuario_id === usuarioId);

  const asignar = async (e: FormEvent) => {
    e.preventDefault();
    await enviarJson<PedidoGerencia>(
      `/api/v1/pagos/pedidos/${pedido.id}/asignaciones`,
      "POST",
      {
        usuario_id: usuarioId,
        gestor_id: gestorId || null,
        proveedor_id: proveedorId || null,
        monto_asignado: monto,
      },
    );
    setMonto("");
    alMensaje("Asignación de Pedido actualizada.");
    alCambiar();
  };

  return (
    <section>
      <h3>Distribución · {pedido.cliente_razon_social}</h3>
      <form onSubmit={asignar} className="formulario-linea">
        <select
          value={usuarioId}
          onChange={(e) => {
            setUsuarioId(e.target.value);
            setGestorId("");
          }}
          required
        >
          <option value="">Usuario</option>
          {usuarios.map((u) => (
            <option key={u.id} value={u.id}>{u.codigo} · {u.nombre}</option>
          ))}
        </select>
        <select value={gestorId} onChange={(e) => setGestorId(e.target.value)}>
          <option value="">Todos sus Gestores</option>
          {gestoresUsuario.map((g) => (
            <option key={g.id} value={g.id}>{g.codigo} · {g.nombre}</option>
          ))}
        </select>
        <select value={proveedorId} onChange={(e) => setProveedorId(e.target.value)}>
          <option value="">Todos los Proveedores</option>
          {proveedores.map((p) => (
            <option key={p.id} value={p.id}>{p.codigo} · {p.nombre}</option>
          ))}
        </select>
        <input
          type="number"
          min="0.01"
          step="0.01"
          placeholder="Monto asignado"
          value={monto}
          onChange={(e) => setMonto(e.target.value)}
          required
        />
        <button type="submit">Asignar / actualizar</button>
      </form>

      <table>
        <thead>
          <tr>
            <th>Usuario</th>
            <th>Gestor</th>
            <th>Proveedor</th>
            <th className="num">Asignado</th>
            <th className="num">Ejecutado</th>
            <th className="num">Saldo</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {pedido.asignaciones.map((a) => (
            <tr key={a.id}>
              <td>{a.usuario_codigo} · {a.usuario_nombre}</td>
              <td>{a.gestor_codigo ? a.gestor_codigo + " · " + a.gestor_nombre : "Todos"}</td>
              <td>
                {a.proveedor_ruc
                  ? a.proveedor_ruc + " · " + a.proveedor_razon_social
                  : "Todos"}
              </td>
              <td className="num">{formatearMonto(pedido.moneda, a.monto_asignado)}</td>
              <td className="num">{formatearMonto(pedido.moneda, a.ejecutado)}</td>
              <td className="num">{formatearMonto(pedido.moneda, a.saldo)}</td>
              <td>
                <button
                  onClick={async () => {
                    await eliminar(
                      `/api/v1/pagos/pedidos/${pedido.id}/asignaciones/${a.id}`,
                    );
                    alCambiar();
                  }}
                >
                  Quitar
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function CobrosClientes({
  mes,
  moneda,
  resumen,
  clientes,
  error,
  alCambiar,
  alMensaje,
}: {
  mes: string;
  moneda: "PEN" | "USD";
  resumen?: CarteraClientesResumen;
  clientes: FiltroOpcion[];
  error?: string;
  alCambiar: () => void;
  alMensaje: (mensaje: string) => void;
}) {
  if (error) return <p className="error">{error}</p>;

  return (
    <>
      <div className="tarjetas registros-resumen">
        <div className="tarjeta borde-verde">
          <span className="cifra">{formatearMonto(moneda, resumen?.total_compras_mes ?? "0")}</span>
          <span>Compras del mes</span>
        </div>
        <div className="tarjeta borde-verde">
          <span className="cifra">{formatearMonto(moneda, resumen?.total_saldo_anterior ?? "0")}</span>
          <span>Saldo anterior</span>
        </div>
        <div className="tarjeta borde-verde">
          <span className="cifra">{formatearMonto(moneda, resumen?.total_abonos_mes ?? "0")}</span>
          <span>Abonos del mes</span>
        </div>
        <div className="tarjeta borde-verde">
          <span className="cifra">{formatearMonto(moneda, resumen?.total_saldo ?? "0")}</span>
          <span>Saldo por cobrar</span>
        </div>
      </div>

      <AbonoClienteForm
        mes={mes}
        moneda={moneda}
        clientes={clientes}
        alCrear={() => {
          alMensaje("Abono del Cliente registrado.");
          alCambiar();
        }}
      />

      <h3>Cartera por Cliente receptor</h3>
      <table>
        <thead>
          <tr>
            <th>Cliente</th>
            <th>Agente retención</th>
            <th className="num">Compras mes</th>
            <th className="num">Saldo anterior</th>
            <th className="num">Abonos mes</th>
            <th className="num">Saldo total</th>
          </tr>
        </thead>
        <tbody>
          {resumen?.filas.map((fila) => (
            <tr key={fila.cliente_id}>
              <td>{fila.ruc} · {fila.razon_social}</td>
              <td>
                <input
                  type="checkbox"
                  checked={fila.agente_retencion}
                  onChange={async (e) => {
                    await enviarJson<boolean>(
                      `/api/v1/pagos/clientes/${fila.cliente_id}/agente-retencion`,
                      "PATCH",
                      { agente_retencion: e.target.checked },
                    );
                    alCambiar();
                  }}
                />
              </td>
              <td className="num">{formatearMonto(fila.moneda, fila.compras_mes)}</td>
              <td className="num">{formatearMonto(fila.moneda, fila.saldo_anterior)}</td>
              <td className="num">{formatearMonto(fila.moneda, fila.abonos_mes)}</td>
              <td className="num">{formatearMonto(fila.moneda, fila.saldo_total)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

function AbonoClienteForm({
  mes,
  moneda,
  clientes,
  alCrear,
}: {
  mes: string;
  moneda: "PEN" | "USD";
  clientes: FiltroOpcion[];
  alCrear: () => void;
}) {
  const [clienteId, setClienteId] = useState("");
  const [fecha, setFecha] = useState(new Date().toISOString().slice(0, 10));
  const [monto, setMonto] = useState("");
  const [referencia, setReferencia] = useState("");
  const [descripcion, setDescripcion] = useState("");

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    await enviarJson<AbonoClienteERP>("/api/v1/pagos/clientes/abonos", "POST", {
      cliente_id: clienteId,
      fecha,
      moneda,
      monto,
      referencia: referencia || null,
      descripcion: descripcion || null,
    });
    setMonto("");
    setReferencia("");
    setDescripcion("");
    alCrear();
  };

  return (
    <section>
      <h3>Registrar abono de Cliente</h3>
      <p className="tenue">Vista actual: {mes} · {moneda}</p>
      <form onSubmit={enviar} className="formulario-linea">
        <select value={clienteId} onChange={(e) => setClienteId(e.target.value)} required>
          <option value="">Cliente</option>
          {clientes.map((c) => (
            <option key={c.id} value={c.id}>{c.codigo} · {c.nombre}</option>
          ))}
        </select>
        <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} required />
        <input
          type="number"
          min="0.01"
          step="0.01"
          placeholder="Monto"
          value={monto}
          onChange={(e) => setMonto(e.target.value)}
          required
        />
        <input
          placeholder="Referencia"
          value={referencia}
          onChange={(e) => setReferencia(e.target.value)}
        />
        <input
          placeholder="Descripción"
          value={descripcion}
          onChange={(e) => setDescripcion(e.target.value)}
        />
        <button type="submit">Registrar abono</button>
      </form>
    </section>
  );
}

function Liquidaciones({
  pagos,
  planes,
  adelantos,
  sesion,
  nombreUsuario,
  alCambiar,
}: {
  pagos: PagoERP[];
  planes: PlanLiquidacion[];
  adelantos: AdelantoERP[];
  sesion: SesionActual;
  nombreUsuario: (id: string) => string;
  alCambiar: () => void;
}) {
  return (
    <>
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
            {pagos.map((pago) => (
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
                  <AccionesPago pago={pago} sesion={sesion} alCambiar={alCambiar} />
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
              {planes.map((p) => (
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
              {adelantos.map((a) => (
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

function PlanForm({
  usuarioId,
  porcentajeInicial,
  alCrear,
}: {
  usuarioId: string;
  porcentajeInicial: string;
  alCrear: () => void;
}) {
  const [nombre, setNombre] = useState("Plan base");
  const [porcentaje, setPorcentaje] = useState(porcentajeInicial);
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
      <p className="tenue">Precargado desde el porcentaje predeterminado del Usuario.</p>
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


    </div>
  );
}
