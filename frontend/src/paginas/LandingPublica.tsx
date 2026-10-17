import { Link } from "react-router-dom";
import { useDatos } from "../api";
import Presentacion from "./Presentacion";

type EstadoLanding = { activa: boolean; version: number };

/** Ocultar solo la landing, nunca el acceso o las páginas legales. */
export default function LandingPublica() {
  const { datos, error, cargando } = useDatos<EstadoLanding>("/api/v1/plataforma/landing/publico");
  if (cargando) {
    return <main className="contenido"><p>Consultando presentación…</p></main>;
  }
  // Disponibilidad heredada si el backend aún no tiene esta versión, sin bloquear el login.
  if (error) return <Presentacion />;
  if (datos?.activa === false) {
    return (
      <main className="contenido">
        <h1>FACT CENTRAL</h1>
        <p>La presentación comercial no está disponible por el momento.</p>
        <p><Link to="/ingresar">Ingresar al sistema</Link></p>
        <p><Link to="/privacidad">Privacidad</Link> · <Link to="/terminos">Términos y condiciones</Link></p>
      </main>
    );
  }
  return <Presentacion />;
}
