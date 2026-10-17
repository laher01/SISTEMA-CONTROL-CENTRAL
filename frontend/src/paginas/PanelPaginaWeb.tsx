/** Panel de inventario de la web comercial en SUPERADMIN.
 * La conmutación real requiere un endpoint global persistente y auditoría.
 * No fingir que un estado local modifica la publicación pública.
 */
export default function PanelPaginaWeb() {
  return (
    <section className="panel-configuracion" aria-labelledby="pagina-web-titulo">
      <h3 id="pagina-web-titulo">Página web y Landing Page</h3>
      <p className="tenue">
        Administración global de la presentación comercial de FACT CENTRAL. Este
        panel no concede acceso a expedientes ni modifica la configuración de tenants.
      </p>
      <div className="panel-configuracion">
        <h4>Publicación de la Landing Page</h4>
        <p><strong>Estado:</strong> control de publicación pendiente de conexión al servidor.</p>
        <label className="bloque">
          <input type="checkbox" disabled aria-describedby="landing-pendiente" />
          Activar o desactivar la página de aterrizaje
        </label>
        <p id="landing-pendiente" className="tenue">
          El interruptor estará disponible cuando exista una configuración global
          persistente, exclusiva de SUPERADMIN y con auditoría. Desactivarla no
          deberá bloquear el login ni las páginas legales públicas.
        </p>
      </div>
      <div className="panel-configuracion">
        <h4>Secciones comerciales preparadas</h4>
        <ul>
          <li>Inicio: portada, necesidad del cliente y solución.</li>
          <li>Precios: planes y tarifas sujetos a aprobación.</li>
          <li>Registro: orientación de altas sin habilitar cuentas automáticamente.</li>
          <li>Multimedia: imágenes y banners con validación de archivos.</li>
          <li>NEXUS comercial: propuestas de contenido, nunca publicación automática.</li>
          <li>Versiones: borrador, vista previa, aprobación, publicación y restauración.</li>
        </ul>
        <p>
          <a href="/bienvenida" target="_blank" rel="noopener noreferrer">
            Ver presentación pública actual
          </a>
        </p>
      </div>
    </section>
  );
}
