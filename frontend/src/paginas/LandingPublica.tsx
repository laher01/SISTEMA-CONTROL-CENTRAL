import { Link } from "react-router-dom";
import { useDatos } from "../api";
import Presentacion from "./Presentacion";
import type { ContenidoLanding } from "../contenidoLanding";

type EstadoLanding = { activa: boolean; version: number };
type EstadoCmsPublico = { disponible: boolean; contenido: ContenidoLanding | null };

function PresentacionAutorizada() {
  const { datos, cargando } = useDatos<EstadoCmsPublico>("/api/v1/plataforma/cms/publico");
  if (cargando) return <main className="contenido"><p>Cargando contenido comercial…</p></main>;
  // Ante ausencia o error del CMS, mantener el texto inicial aprobado, nunca un borrador.
  if (datos?.disponible === true && datos.contenido) {
    return <Presentacion contenido={datos.contenido} />;
  }
  return <Presentacion />;
}

/** Ocultar solo la landing, nunca el acceso o las páginas legales. */
export default function LandingPublica() {
  const { datos, error, cargando } = useDatos<EstadoLanding>("/api/v1/plataforma/landing/publico");
  if (cargando) {
    return <main className="contenido"><p>Consultando presentación…</p></main>;
  }
  // Falla cerrada cuando no se puede comprobar la autorización de publicación.
  if (error || datos?.activa !== true) {
    return (
      <main className="contenido">
        <h1>FACT CENTRAL</h1>
        <p>La presentación comercial no está disponible por el momento.</p>
        <p><Link to="/ingresar">Ingresar al sistema</Link></p>
        <p><Link to="/privacidad">Privacidad</Link> · <Link to="/terminos">Términos y condiciones</Link></p>
      </main>
    );
  }
  return <PresentacionAutorizada />;
}
