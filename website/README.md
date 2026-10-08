# FACT CENTRAL — Sitio comercial

## Objetivo
Sitio de aterrizaje de tres secciones (Inicio, Precios y Registro) independiente del frontend operativo de FACT CENTRAL. Las características descritas deben corresponder a capacidades existentes o identificarse como futuras.

## Estado de esta entrega
- `website/index.html`: sitio responsive, navegación accesible, maqueta de planes, formulario demostrativo con validación del navegador.
- Ningún dato del formulario es transmitido o almacenado. No existe checkout ni creación de cuentas en esta entrega.
- Los precios se indican «A definir» para no representar importes no aprobados.
- El panel estadístico muestra números **ilustrativos**, no estadísticas reales del sistema.

## Publicación de vista previa
Puede abrirse `website/index.html` localmente con un navegador. No requiere instalar dependencias. Para publicar una vista previa aislada, configurar Cloudflare Pages sobre el subdirectorio `website` sin build; publicar solo en un subdominio de staging. No reemplazar el aplicativo actual ni el DNS productivo sin pruebas.

## Arquitectura prevista
- `factcentral.online`: sitio informativo y comercial.
- `app.factcentral.online`: aplicativo autenticado existente.
- `api.factcentral.online`: backend de aplicaciones y onboarding, protegido por HTTPS, CORS de orígenes autorizados y límites de velocidad.
- Solo el backend controla identidades, tenant, roles, suscripciones, planes y activaciones.
- El frontend público jamás recibe claves privadas ni tokens de la pasarela.

## Contratos backend propuestos (NO IMPLEMENTADOS)
1. `GET /api/v1/public/planes`: lista de planes publicados (IDs, prestaciones, moneda, periodicidad, impuestos/condiciones).
2. `POST /api/v1/public/registro`: valida RUC, datos del administrador y email; crea solicitud pendiente, no Tenant activo. Debe tener antiautomatización, consentimiento legal verificable, verificación de correo, rate limit e idempotencia.
3. `POST /api/v1/public/checkout`: recibe ID de solicitud y plan validado en servidor; crea checkout hospedado en proveedor con referencia no predecible, sin aceptar importe arbitrario del navegador.
4. `POST /api/v1/webhooks/pagos/{proveedor}`: verifica firma y vigencia del evento, registra ID del evento, reconsulta proveedor cuando sea necesario, garantiza idempotencia y activa la suscripción solo tras pago confirmado.
5. `GET /api/v1/public/registro/{token}/estado`: consulta estado con token limitado y expirable, sin filtrar datos internos.
6. Servicio de aprovisionamiento transaccional: crea/activa tenant, administrador, plan y cuotas; emite evento auditable; envía enlace de configuración de contraseña mediante canal verificado. Nunca envía contraseñas por correo.

## Pasarela de pago — evaluación de integración
Candidatos para investigar: Culqi, Mercado Pago y Niubiz (disponibilidad de suscripción recurrente, medios peruanos, comisiones, liquidación, contratos, facturación, políticas de devolución, seguridad y webhooks). **No se verificó información comercial vigente ni se eligió proveedor**. Preferir checkout alojado/tokenizado y nunca capturar datos sensibles de tarjeta en FACT CENTRAL.

## Requisitos para lanzamiento
- Términos de servicio, política de privacidad y tratamiento de datos aprobados.
- Catálogo y precios aprobados; verificar implicancias tributarias.
- Prueba de aislamiento entre tenants, autorización RBAC, recuperaciones de contraseña y sesiones.
- Pruebas de webhook duplicado/retrasado/falso, reembolsos, renovaciones, cancelaciones, fallos de provisión y conciliación.
- Webhook no público sin autenticación criptográfica; secretos solo en variables de entorno protegidas.
- Pruebas automatizadas de navegación, accesibilidad y flujo completo en sandbox del procesador.
- Despliegue mediante Pull Request aprobado; jamás sobrescribir `main` automáticamente.

## Siguientes hitos
A. Aprobar identidad visual, copy, planes y condiciones.
B. Implementar tablas Tenant/Subscription/Plan/CheckoutAttempt/PaymentEvent con migraciones y modelos.
C. Implementar APIs públicas y adaptación al proveedor seleccionado.
D. Integrar UI y sandbox, probar seguridad y flujos de error.
E. Publicar en staging; luego producción mediante CI/CD con rollback.

## Visión de producto
FACT CENTRAL mantiene su foco en gestión documental de compras y expedientes empresariales. NEXUS AI se describe como asistente contextual en evolución, no como sistema autónomo ya entregado. Esta web es una interfaz comercial y no introduce funciones de facturación de comprobantes ni modifica la operación central.
