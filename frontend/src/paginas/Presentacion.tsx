import "../presentacion.css";
import { Link } from "react-router-dom";
import { PiePublico } from "./PaginasPublicas";
import { contenidoLandingInicial as contenido } from "../contenidoLanding";

export default function Presentacion() {
  return (
    <main className="presentacion">
      <header className="presentacion-cabecera">
        <Link to="/" className="presentacion-logo">{contenido.marca}</Link>
        <nav aria-label="Navegación principal">
          <a href="#inicio">Inicio</a>
          <a href="#precios">Precios</a>
          <a href="#registro">Registro</a>
        </nav>
        <Link to="/ingresar" className="presentacion-acceso">Ingresar</Link>
      </header>

      <section id="inicio" className="presentacion-hero">
        <p className="presentacion-etiqueta">{contenido.etiqueta}</p>
        <h1>{contenido.titulo}</h1>
        <p>{contenido.descripcion}</p>
        <div className="presentacion-acciones">
          <Link to="/ingresar" className="presentacion-primario">Ingresar a mi espacio</Link>
          <a href="#precios" className="presentacion-secundario">Conocer el servicio</a>
        </div>
        <p className="presentacion-nota">Acceso exclusivo para cuentas habilitadas por su administración.</p>
      </section>

      <section className="presentacion-seccion" aria-label="Beneficios">
        <h2>{contenido.beneficiosTitulo}</h2>
        <div className="presentacion-tarjetas">
          {contenido.beneficios.map((beneficio) => <article key={beneficio.id}><h3>{beneficio.titulo}</h3><p>{beneficio.descripcion}</p></article>)}
        </div>
      </section>

      <section id="precios" className="presentacion-seccion presentacion-alternada">
        <h2>{contenido.planesTitulo}</h2>
        <p>{contenido.planesDescripcion}</p>
        <Link to="/ingresar" className="presentacion-secundario">Ya tengo una cuenta</Link>
      </section>

      <section id="registro" className="presentacion-seccion">
        <h2>{contenido.registroTitulo}</h2>
        <p>{contenido.registroDescripcion}</p>
        <Link to="/ingresar" className="presentacion-primario">Ir a la página de ingreso</Link>
      </section>

      <PiePublico />
    </main>
  );
}
