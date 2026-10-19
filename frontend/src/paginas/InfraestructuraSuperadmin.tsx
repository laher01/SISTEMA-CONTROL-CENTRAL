/** Vista de planificación segura: nunca atribuir valores estimados a una VPS real. */
export default function InfraestructuraSuperadmin() {
  return (
    <section className="panel-configuracion" aria-label="Infraestructura y almacenamiento VPS">
      <h2>Infraestructura VPS · Consola SUPERADMIN</h2>
      <p className="tenue">
        Inventario inicial y política de almacenamiento documental secuencial.
        La lectura de recursos requiere agentes autenticados: ningún valor sin telemetría es una medición real.
      </p>
      <div className="resumen-carga">
        <strong>VPS central · Aplicación y PostgreSQL</strong>
        <span>Servidor autorizado: 132.145.233.172</span>
        <span>Estado de conexión: sin telemetría verificada</span>
        <span>vCPU: sin telemetría</span>
        <span>RAM: sin telemetría</span>
        <span>Swap: sin telemetría</span>
        <span>Disco: sin telemetría</span>
      </div>
      <h3>Discos documentales · VPS externas</h3>
      <p>
        Ningún nodo externo se considera conectado hasta validar su identidad,
        acceso cifrado, lectura, escritura, hash y recuperación.
      </p>
      <div className="resumen-carga">
        <strong>Nodos externos verificados: pendiente de inventario</strong>
        <span>Almacén activo de escritura: por verificar</span>
        <span>Uso de disco: sin telemetría</span>
        <span>Umbral para preparar el siguiente nodo: 60 %</span>
      </div>
      <h3>Continuidad de almacenamiento</h3>
      <ol>
        <li>Un solo nodo recibe nuevos documentos de todos los tenants.</li>
        <li>Al alcanzar el 60 % de ocupación, se alerta y se prepara el siguiente nodo.</li>
        <li>El nodo siguiente se valida antes de habilitar la escritura.</li>
        <li>Los nodos anteriores conservan los documentos y permiten su lectura.</li>
        <li>El índice central mantiene la ubicación verificable de cada documento.</li>
      </ol>
      <p className="tenue">
        La activación de nodos, suspensión de tenants y gestión de claves no están disponibles
        en esta etapa. No se permiten acciones destructivas desde esta pantalla.
      </p>
    </section>
  );
}
