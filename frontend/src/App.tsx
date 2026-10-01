import { NavLink, Route, Routes } from "react-router-dom";

import Alertas from "./paginas/Alertas";
import Dashboard from "./paginas/Dashboard";
import Empresas from "./paginas/Empresas";
import ExpedienteDetalle from "./paginas/ExpedienteDetalle";
import Expedientes from "./paginas/Expedientes";
import Pendientes from "./paginas/Pendientes";
import Subir from "./paginas/Subir";

const MENU = [
  { a: "/", texto: "Dashboard" },
  { a: "/subir", texto: "Subir documentos" },
  { a: "/expedientes", texto: "Expedientes" },
  { a: "/pendientes", texto: "Pendientes" },
  { a: "/alertas", texto: "Alertas" },
  { a: "/empresas", texto: "Empresas" },
];

export default function App() {
  return (
    <div className="app">
      <aside className="menu">
        <h1>FACT CENTRAL</h1>
        <nav>
          {MENU.map((item) => (
            <NavLink key={item.a} to={item.a} end={item.a === "/"}>
              {item.texto}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="contenido">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/subir" element={<Subir />} />
          <Route path="/expedientes" element={<Expedientes />} />
          <Route path="/expedientes/:id" element={<ExpedienteDetalle />} />
          <Route path="/pendientes" element={<Pendientes />} />
          <Route path="/alertas" element={<Alertas />} />
          <Route path="/empresas" element={<Empresas />} />
          <Route path="*" element={<p>Página no encontrada.</p>} />
        </Routes>
      </main>
    </div>
  );
}
