import { useState } from "react";
import { Navigate, NavLink, Route, Routes } from "react-router-dom";

import { enviarJson, useDatos } from "./api";
import NexusFlotante from "./componentes/NexusFlotante";
import Alertas from "./paginas/Alertas";
import Configuracion from "./paginas/Configuracion";
import Chat from "./paginas/Chat";
import Comisiones from "./paginas/Comisiones";
import ComisionesResponsables from "./paginas/ComisionesResponsables";
import Dashboard from "./paginas/Dashboard";
import Documentos from "./paginas/Documentos";
import Empresas from "./paginas/Empresas";
import ExpedienteDetalle from "./paginas/ExpedienteDetalle";
import Expedientes from "./paginas/Expedientes";
import { CambiarClave, Login } from "./paginas/Login";
import Presentacion from "./paginas/Presentacion";
import Organizacion from "./paginas/Organizacion";
import MiEquipoResponsable from "./paginas/MiEquipoResponsable";
import Pagos from "./paginas/Pagos";
import PagoGestores from "./paginas/PagoGestores";
import Pendientes from "./paginas/Pendientes";
import Produccion from "./paginas/Produccion";
import Registros from "./paginas/Registros";
import Secretaria from "./paginas/Secretaria";
import Subir from "./paginas/Subir";
import type { SesionActual } from "./tipos";

type RolSesion = SesionActual["rol"];

const MENU: { a: string; texto: string; icono: string; roles: RolSesion[] }[] = [
  { a: "/mi-equipo", texto: "Mis Usuarios", icono: "♙", roles: ["RESPONSABLE"] },
  { a: "/mi-equipo/pedidos", texto: "Pedidos", icono: "▤", roles: ["RESPONSABLE"] },
  { a: "/mi-equipo/cobros", texto: "Cobros y clientes", icono: "◈", roles: ["RESPONSABLE"] },
  { a: "/mi-equipo/pagos", texto: "Pago de Usuarios", icono: "▣", roles: ["RESPONSABLE"] },
  { a: "/comisiones-responsables", texto: "Comisiones de mi equipo", icono: "▥", roles: ["RESPONSABLE"] },
  { a: "/pago-gestores", texto: "Pago de Gestores", icono: "▣", roles: ["USUARIO"] },
  { a: "/comisiones", texto: "Simular comisiones", icono: "◉", roles: ["RESPONSABLE", "USUARIO"] },
  {
    a: "/",
    texto: "Dashboard",
    icono: "⌂",
    roles: ["SUPERADMIN", "ADMINISTRADOR", "GERENTE", "SECRETARIA", "USUARIO", "GESTOR"],
  },
  { a: "/subir", texto: "Subir documentos", icono: "↑", roles: ["USUARIO", "GESTOR"] },
  {
    a: "/registros",
    texto: "Registros",
    icono: "▦",
    roles: ["SUPERADMIN", "ADMINISTRADOR", "GERENTE", "SECRETARIA", "USUARIO", "GESTOR"],
  },
  {
    a: "/chat",
    texto: "Chat interno",
    icono: "◌",
    roles: ["SUPERADMIN", "ADMINISTRADOR", "GERENTE", "SECRETARIA", "USUARIO", "GESTOR"],
  },
  {
    a: "/secretaria",
    texto: "Control documental",
    icono: "▧",
    roles: ["SUPERADMIN", "ADMINISTRADOR", "SECRETARIA", "GERENTE"],
  },
  {
    a: "/documentos",
    texto: "Documentos",
    icono: "▤",
    roles: ["SUPERADMIN", "ADMINISTRADOR", "SECRETARIA", "USUARIO", "GESTOR"],
  },
  {
    a: "/expedientes",
    texto: "Expedientes",
    icono: "▱",
    roles: ["SUPERADMIN", "ADMINISTRADOR", "GERENTE", "SECRETARIA", "USUARIO", "GESTOR"],
  },
  {
    a: "/pendientes",
    texto: "Pendientes",
    icono: "◷",
    roles: ["SUPERADMIN", "ADMINISTRADOR", "SECRETARIA", "USUARIO", "GESTOR"],
  },
  {
    a: "/alertas",
    texto: "Alertas",
    icono: "⚑",
    roles: ["SUPERADMIN", "ADMINISTRADOR", "SECRETARIA", "USUARIO", "GESTOR"],
  },
  {
    a: "/empresas",
    texto: "Empresas",
    icono: "▥",
    roles: ["SUPERADMIN", "ADMINISTRADOR", "GERENTE", "SECRETARIA", "USUARIO"],
  },
  { a: "/organizacion", texto: "Organización", icono: "♧", roles: ["SUPERADMIN", "ADMINISTRADOR", "RESPONSABLE", "USUARIO"] },
  {
    a: "/produccion",
    texto: "Producción",
    icono: "▥",
    roles: ["SUPERADMIN", "ADMINISTRADOR", "GERENTE", "USUARIO", "GESTOR"],
  },
  {
    a: "/pagos",
    texto: "Pagos",
    icono: "▣",
    roles: ["SUPERADMIN", "ADMINISTRADOR", "GERENTE"],
  },
  {
    a: "/configuracion",
    texto: "Configuración",
    icono: "⚙",
    roles: ["SUPERADMIN", "ADMINISTRADOR"],
  },
];

export default function App() {
  const [modoBarra, setModoBarra] = useState<"AUTOMATICO" | "MANUAL">(() => window.localStorage.getItem("fc-sidebar-mode") === "MANUAL" ? "MANUAL" : "AUTOMATICO");
  const [barraAbierta, setBarraAbierta] = useState(false);
  const cambiarModo = (modo: "AUTOMATICO" | "MANUAL") => {
    setModoBarra(modo);
    window.localStorage.setItem("fc-sidebar-mode", modo);
    setBarraAbierta(false);
  };
  const { datos: sesion, error, cargando, recargar } = useDatos<SesionActual>("/api/v1/auth/me");

  if (cargando) return <main className="contenido"><p>Cargando sesión…</p></main>;
  if (!sesion || error) {
    const esPortalOracle = window.location.hostname === "factcentral.online";
    const esIngreso = window.location.pathname === "/ingresar";
    return esPortalOracle && !esIngreso
      ? <Presentacion />
      : <Login alIngresar={recargar} />;
  }
  if (sesion.cambio_clave_obligatorio) {
    return <CambiarClave sesion={sesion} alCambiar={recargar} />;
  }

  const cerrarSesion = async () => {
    try {
      await enviarJson<unknown>("/api/v1/auth/logout", "POST");
    } finally {
      recargar();
    }
  };

  const menu = MENU.filter((item) => item.roles.includes(sesion.rol));
  const cadena = sesion.rol === "GESTOR"
    ? [{ rol: "GESTOR", codigo: sesion.codigo, nombre: sesion.nombre }, ...(sesion.jerarquia ?? [])]
    : sesion.rol === "USUARIO"
      ? (sesion.jerarquia?.length ? sesion.jerarquia : [{ rol: "USUARIO", codigo: sesion.codigo, nombre: sesion.nombre }])
      : [{ rol: sesion.rol, codigo: sesion.codigo, nombre: sesion.nombre }];
  const dominio = window.location.hostname;

  return (
    <div className="app">
      <aside className={`menu menu-ajustable ${barraAbierta ? "menu-abierto" : "menu-cerrado"}`} onMouseEnter={() => { if (modoBarra === "AUTOMATICO") setBarraAbierta(true); }} onMouseLeave={() => { if (modoBarra === "AUTOMATICO") setBarraAbierta(false); }}>
        <div className="barra-controles"><button type="button" className="barra-toggle" aria-label={barraAbierta ? "Contraer menú" : "Expandir menú"} aria-expanded={barraAbierta} title={barraAbierta ? "Contraer menú" : "Expandir menú"} onClick={() => setBarraAbierta(!barraAbierta)}>☰</button><div className="barra-opciones"><label htmlFor="modo-menu">Modo</label><select id="modo-menu" aria-label="Comportamiento del menú lateral" value={modoBarra} onChange={(e) => cambiarModo(e.target.value as "AUTOMATICO" | "MANUAL")}><option value="AUTOMATICO">Automático</option><option value="MANUAL">Manual</option></select></div></div>
        <h1 className="barra-texto">FACT CENTRAL</h1>
        <div className="sesion-resumen barra-texto">
          <strong>{sesion.codigo}</strong>
          <span>{sesion.nombre}</span>
          <small>{sesion.rol}</small>

        </div>
        <nav>
          {menu.map((item) => (
            <NavLink key={item.a} to={item.a} end={item.a === "/"} title={item.texto} aria-label={item.texto}>
              <span className="menu-icono" aria-hidden="true">{item.icono}</span><span className="barra-texto menu-etiqueta">{item.texto}</span>
            </NavLink>
          ))}
        </nav>
        <button className="cerrar-sesion" onClick={cerrarSesion} title="Cerrar sesión" aria-label="Cerrar sesión"><span aria-hidden="true">⇥</span><span className="barra-texto"> Cerrar sesión</span></button>
      </aside>
      <main className="contenido">
        <header className="ruta-organizacion" aria-label="Dominio y cadena de responsabilidad">
          <div className="ruta-dominio"><strong>FACT CENTRAL</strong><span>{dominio}</span></div>
          <div className="ruta-personas">
            {cadena.map((persona, indice) => (
              <span className="ruta-persona" key={persona.rol + persona.codigo}>
                {indice > 0 && <span className="ruta-flecha" aria-hidden="true">→</span>}
                <strong>{persona.rol}:</strong> {persona.codigo} · {persona.nombre}
              </span>
            ))}
          </div>
        </header>
        <Routes>
          <Route path="/" element={sesion.es_administracion_demo && sesion.rol === "ADMINISTRADOR" ? <Navigate to="/organizacion" replace /> : <Dashboard />} />
          <Route path="/ingresar" element={<Navigate to="/" replace />} />
          <Route path="/subir" element={<Subir sesion={sesion} />} />
          <Route path="/registros" element={<Registros sesion={sesion} />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/secretaria" element={<Secretaria />} />
          <Route path="/documentos" element={<Documentos sesion={sesion} />} />
          <Route path="/expedientes" element={<Expedientes sesion={sesion} />} />
          <Route path="/expedientes/:id" element={<ExpedienteDetalle />} />
          <Route path="/pendientes" element={<Pendientes />} />
          <Route path="/alertas" element={<Alertas sesion={sesion} />} />
          <Route path="/empresas" element={<Empresas sesion={sesion} />} />
          <Route path="/mi-equipo" element={<MiEquipoResponsable />} />
          <Route path="/mi-equipo/pedidos" element={<MiEquipoResponsable inicial="PEDIDOS" />} />
          <Route path="/mi-equipo/cobros" element={<MiEquipoResponsable inicial="COBROS" />} />
          <Route path="/mi-equipo/pagos" element={<MiEquipoResponsable inicial="PAGOS" />} />
          <Route path="/pago-gestores" element={<PagoGestores />} />
          <Route path="/comisiones" element={<Comisiones sesion={sesion} />} />
          <Route path="/organizacion" element={<Organizacion sesion={sesion} />} />
          <Route path="/produccion" element={<Produccion />} />
          <Route path="/pagos" element={<Pagos sesion={sesion} />} />
          <Route path="/comisiones-responsables" element={<ComisionesResponsables sesion={sesion} />} />
          <Route path="/configuracion" element={<Configuracion sesion={sesion} />} />
          <Route path="*" element={<p>Página no encontrada.</p>} />
        </Routes>
      </main>
      <NexusFlotante sesion={sesion} />
    </div>
  );
}
