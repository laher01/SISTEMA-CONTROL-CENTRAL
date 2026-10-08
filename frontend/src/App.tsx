import { NavLink, Route, Routes } from "react-router-dom";

import { enviarJson, useDatos } from "./api";
import NexusFlotante from "./componentes/NexusFlotante";
import Alertas from "./paginas/Alertas";
import Configuracion from "./paginas/Configuracion";
import Chat from "./paginas/Chat";
import Dashboard from "./paginas/Dashboard";
import Documentos from "./paginas/Documentos";
import Empresas from "./paginas/Empresas";
import ExpedienteDetalle from "./paginas/ExpedienteDetalle";
import Expedientes from "./paginas/Expedientes";
import { CambiarClave, Login } from "./paginas/Login";
import Organizacion from "./paginas/Organizacion";
import Pagos from "./paginas/Pagos";
import Pendientes from "./paginas/Pendientes";
import Produccion from "./paginas/Produccion";
import Registros from "./paginas/Registros";
import Subir from "./paginas/Subir";
import type { SesionActual } from "./tipos";

type RolSesion = SesionActual["rol"];

const MENU: { a: string; texto: string; roles: RolSesion[] }[] = [
  {
    a: "/",
    texto: "Dashboard",
    roles: ["SUPERADMIN", "ADMINISTRADOR", "GERENTE", "SECRETARIA", "USUARIO", "GESTOR"],
  },
  { a: "/subir", texto: "Subir documentos", roles: ["USUARIO", "GESTOR"] },
  {
    a: "/registros",
    texto: "Registros",
    roles: ["SUPERADMIN", "ADMINISTRADOR", "GERENTE", "SECRETARIA", "USUARIO", "GESTOR"],
  },
  {
    a: "/chat",
    texto: "Chat interno",
    roles: ["SUPERADMIN", "ADMINISTRADOR", "GERENTE", "SECRETARIA", "USUARIO", "GESTOR"],
  },
  {
    a: "/documentos",
    texto: "Documentos",
    roles: ["SUPERADMIN", "ADMINISTRADOR", "SECRETARIA", "USUARIO", "GESTOR"],
  },
  {
    a: "/expedientes",
    texto: "Expedientes",
    roles: ["SUPERADMIN", "ADMINISTRADOR", "GERENTE", "SECRETARIA", "USUARIO", "GESTOR"],
  },
  {
    a: "/pendientes",
    texto: "Pendientes",
    roles: ["SUPERADMIN", "ADMINISTRADOR", "SECRETARIA", "USUARIO", "GESTOR"],
  },
  {
    a: "/alertas",
    texto: "Alertas",
    roles: ["SUPERADMIN", "ADMINISTRADOR", "SECRETARIA", "USUARIO", "GESTOR"],
  },
  {
    a: "/empresas",
    texto: "Empresas",
    roles: ["SUPERADMIN", "ADMINISTRADOR", "GERENTE", "SECRETARIA", "USUARIO"],
  },
  { a: "/organizacion", texto: "Organización", roles: ["SUPERADMIN", "ADMINISTRADOR", "USUARIO"] },
  {
    a: "/produccion",
    texto: "Producción",
    roles: ["SUPERADMIN", "ADMINISTRADOR", "GERENTE", "USUARIO", "GESTOR"],
  },
  {
    a: "/pagos",
    texto: "Pagos",
    roles: ["SUPERADMIN", "ADMINISTRADOR", "GERENTE"],
  },
  {
    a: "/configuracion",
    texto: "Configuración",
    roles: ["SUPERADMIN", "ADMINISTRADOR"],
  },
];

export default function App() {
  const { datos: sesion, error, cargando, recargar } = useDatos<SesionActual>("/api/v1/auth/me");

  if (cargando) return <main className="contenido"><p>Cargando sesión…</p></main>;
  if (!sesion || error) return <Login alIngresar={recargar} />;
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

  return (
    <div className="app">
      <aside className="menu">
        <h1>FACT CENTRAL</h1>
        <div className="sesion-resumen">
          <strong>{sesion.codigo}</strong>
          <span>{sesion.nombre}</span>
          <small>{sesion.rol}</small>
        </div>
        <nav>
          {menu.map((item) => (
            <NavLink key={item.a} to={item.a} end={item.a === "/"}>
              {item.texto}
            </NavLink>
          ))}
        </nav>
        <button className="cerrar-sesion" onClick={cerrarSesion}>Cerrar sesión</button>
      </aside>
      <main className="contenido">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/subir" element={<Subir sesion={sesion} />} />
          <Route path="/registros" element={<Registros sesion={sesion} />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/documentos" element={<Documentos sesion={sesion} />} />
          <Route path="/expedientes" element={<Expedientes sesion={sesion} />} />
          <Route path="/expedientes/:id" element={<ExpedienteDetalle />} />
          <Route path="/pendientes" element={<Pendientes />} />
          <Route path="/alertas" element={<Alertas sesion={sesion} />} />
          <Route path="/empresas" element={<Empresas />} />
          <Route path="/organizacion" element={<Organizacion sesion={sesion} />} />
          <Route path="/produccion" element={<Produccion />} />
          <Route path="/pagos" element={<Pagos sesion={sesion} />} />
          <Route path="/configuracion" element={<Configuracion sesion={sesion} />} />
          <Route path="*" element={<p>Página no encontrada.</p>} />
        </Routes>
      </main>
      <NexusFlotante sesion={sesion} />
    </div>
  );
}
