import "../presentacion.css";
import { Link } from "react-router-dom";

export default function Presentacion() {
  return (
    <main className="presentacion">
      <header className="presentacion-cabecera">
        <Link to="/" className="presentacion-logo">FACT CENTRAL</Link>
        <nav aria-label="Navegación principal">
          <a href="#inicio">Inicio</a>
          <a href="#precios">Precios</a>
          <a href="#registro">Registro</a>
        </nav>
        <Link to="/ingresar" className="presentacion-acceso">Ingresar</Link>
      </header>

      <section id="inicio" className="presentacion-hero">
        <p className="presentacion-etiqueta">GESTIÓN DOCUMENTAL TRIBUTARIA</p>
        <h1>De documentos dispersos a expedientes digitales organizados.</h1>
        <p>FACT CENTRAL reúne comprobantes, guías y sustentos de compras para facilitar el control documental, el seguimiento y la revisión administrativa.</p>
        <div className="presentacion-acciones">
          <Link to="/ingresar" className="presentacion-primario">Ingresar a mi espacio</Link>
          <a href="#precios" className="presentacion-secundario">Conocer el servicio</a>
        </div>
        <p className="presentacion-nota">Acceso exclusivo para cuentas habilitadas por su administración.</p>
      </section>

      <section className="presentacion-seccion" aria-label="Beneficios">
        <h2>Un solo lugar para controlar la documentación de compras</h2>
        <div className="presentacion-tarjetas">
          <article><h3>Documentos</h3><p>Organiza archivos PDF, imágenes y comprobantes por operación y empresa.</p></article>
          <article><h3>Expedientes</h3><p>Relaciona facturas, guías y evidencias para facilitar su revisión.</p></article>
          <article><h3>Control y trazabilidad</h3><p>Consulta registros, estados y permisos según el perfil autorizado.</p></article>
        </div>
      </section>

      <section id="precios" className="presentacion-seccion presentacion-alternada">
        <h2>Planes del servicio</h2>
        <p>Los planes y sus tarifas se publicarán cuando estén aprobados. No se realizan cobros desde esta página.</p>
        <Link to="/ingresar" className="presentacion-secundario">Ya tengo una cuenta</Link>
      </section>

      <section id="registro" className="presentacion-seccion">
        <h2>Registro y acceso</h2>
        <p>La creación de cuentas se realiza con autorización de cada administración. El formulario de solicitud de acceso aparece en la pantalla de ingreso solo cuando su administración lo tiene habilitado.</p>
        <Link to="/ingresar" className="presentacion-primario">Ir a la página de ingreso</Link>
      </section>

      <footer className="presentacion-pie">FACT CENTRAL · Plataforma de gestión documental empresarial</footer>
    </main>
  );
}
