import { Link } from "react-router-dom";
import "../presentacion.css";

const soporte = "nexomarnegocioseirl@gmail.com";

function CabeceraPublica() {
  return <header className="presentacion-cabecera">
    <Link className="presentacion-logo" to="/">FACT CENTRAL</Link>
    <nav aria-label="Páginas públicas">
      <Link to="/">Inicio</Link>
      <Link to="/privacidad">Privacidad</Link>
      <Link to="/terminos">Términos</Link>
    </nav>
    <Link to="/ingresar" className="presentacion-acceso">Ingresar</Link>
  </header>;
}

export function PiePublico() {
  return <footer className="presentacion-pie">
    FACT CENTRAL · Servicio de NEXOMAR NEGOCIOS E.I.R.L. ·
    {" "}<Link to="/privacidad">Privacidad</Link> · <Link to="/terminos">Términos</Link> ·
    {" "}<a href={`mailto:${soporte}`}>Contacto</a>
  </footer>;
}

export default function PaginaLegal({ tipo }: { tipo: "privacidad" | "terminos" }) {
  const privacidad = tipo === "privacidad";
  return <main className="presentacion">
    <CabeceraPublica />
    <article className="presentacion-legal">
      {privacidad ? <>
        <h1>Política de privacidad de FACT CENTRAL</h1>
        <p>FACT CENTRAL es una plataforma de gestión documental empresarial ofrecida por NEXOMAR NEGOCIOS E.I.R.L. Esta información explica el tratamiento de datos realizado en el uso de la plataforma y la recepción autorizada de correos.</p>
        <h2>Datos tratados y finalidad</h2>
        <p>El servicio gestiona información de las cuentas autorizadas, empresas, usuarios, comprobantes, guías, expedientes y archivos asociados. Cuando una administración conecta una cuenta de Gmail, FACT CENTRAL solicita autorización de lectura de mensajes y adjuntos para identificar documentación relacionada con operaciones empresariales, clasificarla y vincularla a sus registros.</p>
        <h2>Acceso a Gmail</h2>
        <p>El permiso utilizado es <code>https://www.googleapis.com/auth/gmail.readonly</code>. La aplicación no solicita mediante este permiso enviar, modificar ni eliminar mensajes de Gmail. El acceso depende del consentimiento del titular y puede revocarse desde la configuración de seguridad de su cuenta Google.</p>
        <h2>Protección y acceso interno</h2>
        <p>El acceso a la información en FACT CENTRAL se organiza mediante cuentas, permisos y ámbitos empresariales. Los mensajes y documentos procesados pueden almacenarse para su consulta y trazabilidad documental. Los responsables de cada organización deben administrar sus usuarios autorizados y proteger sus credenciales.</p>
        <h2>Conservación y solicitudes</h2>
        <p>La información documental se conserva para la prestación del servicio y las necesidades administrativas o legales aplicables. Para solicitar acceso, rectificación, eliminación de datos cuando proceda o información sobre su conservación, escriba a <a href={`mailto:${soporte}`}>{soporte}</a>. La revocación de acceso en Google impide nuevas lecturas con esa autorización, pero no borra automáticamente los expedientes previamente registrados en FACT CENTRAL.</p>
        <h2>Uso limitado de datos de Google</h2>
        <p>El uso y transferencia de información recibida de las API de Google por FACT CENTRAL debe cumplir la Política de Datos de Usuario de los Servicios de API de Google, incluidos sus requisitos de uso limitado. No se utiliza la información de Gmail para publicidad personalizada.</p>
        <h2>Contacto</h2>
        <p>NEXOMAR NEGOCIOS E.I.R.L. · <a href={`mailto:${soporte}`}>{soporte}</a></p>
      </> : <>
        <h1>Términos y condiciones de FACT CENTRAL</h1>
        <p>FACT CENTRAL es una plataforma de organización y seguimiento de documentación empresarial proporcionada por NEXOMAR NEGOCIOS E.I.R.L.</p>
        <h2>Acceso autorizado</h2>
        <p>El acceso a los espacios empresariales está sujeto a habilitación por la administración correspondiente. Cada persona debe custodiar sus credenciales y usar las funciones conforme a los permisos que le han sido asignados.</p>
        <h2>Gestión documental</h2>
        <p>La plataforma ayuda a registrar y relacionar comprobantes, guías, sustentos y expedientes. Su utilización no sustituye la revisión profesional ni garantiza por sí sola la aceptación de documentos por autoridades tributarias u otras entidades.</p>
        <h2>Conexiones externas</h2>
        <p>La conexión con Gmail requiere autorización de la cuenta correspondiente. La disponibilidad de integraciones depende de los proveedores externos y de su configuración. El titular puede revocar la autorización de Google desde su cuenta.</p>
        <h2>Responsabilidades</h2>
        <p>Quien utiliza el servicio debe contar con autorización para incorporar y procesar los documentos y datos que proporcione. No se permite acceder a información ajena ni usar el sistema para actividades contrarias a la ley.</p>
        <h2>Servicio y consultas</h2>
        <p>Las condiciones comerciales, tarifas y modalidades de suscripción se comunicarán antes de su contratación. Para preguntas sobre el uso del servicio, contacte a <a href={`mailto:${soporte}`}>{soporte}</a>.</p>
      </>}
    </article>
    <PiePublico />
  </main>;
}
