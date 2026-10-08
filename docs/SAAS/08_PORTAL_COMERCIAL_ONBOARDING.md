# Portal Comercial FACT CENTRAL — Especificación integrada

**Estado:** implementación de preproducción en `feature/website-comercial-fact-central`.
**Objetivo:** convertir la idea de “Diseño SaaS y seguridad” en la puerta de entrada comercial del SaaS sin mezclar el sitio público con el núcleo operativo.

## Principio rector
La web no es un micrositio aislado: forma parte del ciclo de vida SaaS.

```text
Visitante
  -> Inicio
  -> Precios
  -> Registro
  -> Verificación
  -> Checkout del proveedor
  -> Confirmación servidor-a-servidor
  -> Suscripción activa
  -> Aprovisionamiento Tenant + Administrador
  -> app.factcentral.online
  -> FACT CENTRAL + NEXUS
```

## Navegación pública
Solo tres destinos principales:
1. **Inicio**: necesidad -> solución -> capacidades -> NEXUS -> seguridad -> funcionamiento -> CTA.
2. **Precios**: planes publicados desde configuración/backend. El sitio no codificará importes definitivos.
3. **Registro**: onboarding del administrador y empresa; después continuará a checkout cuando la integración esté habilitada.

## Separación de superficies
- `factcentral.online`: sitio público.
- `app.factcentral.online`: aplicación autenticada.
- API: backend controlado. El navegador no accede a base de datos ni secretos.
- Staging: debe publicarse en dominio independiente antes de producción.

## Modelo mínimo para onboarding (por implementar)
### Plan
`id, codigo, nombre, descripcion, moneda, periodicidad, precio, activo, limites_json, version, published_at`.

### SignupRequest
`id, email, nombre_admin, ruc, razon_social, plan_id, status, email_verified_at, expires_at, created_at`.

### Subscription
`id, tenant_id, plan_id, provider, provider_customer_ref, provider_subscription_ref, status, current_period_start, current_period_end, cancel_at_period_end`.

### CheckoutAttempt
`id, signup_request_id, plan_id, provider, provider_checkout_ref, status, amount_expected, currency, idempotency_key, created_at`.

### PaymentEvent
`id, provider, provider_event_id, event_type, signature_verified, received_at, processed_at, processing_status, payload_hash`.

Los datos específicos del proveedor se almacenarán minimizados y nunca incluirán PAN/CVV.

## API pública prevista
- `GET /api/v1/public/planes`
- `POST /api/v1/public/registro`
- `POST /api/v1/public/registro/verificar-email`
- `POST /api/v1/public/checkout`
- `POST /api/v1/webhooks/pagos/{provider}`
- `GET /api/v1/public/registro/{token}/estado`

Todos los endpoints de escritura deben aplicar validación, rate limit, idempotencia donde corresponda, auditoría y respuestas que no permitan enumerar cuentas.

## Activación segura
1. El cliente selecciona un `plan_id`; el backend vuelve a cargar precio/moneda desde su catálogo.
2. El backend crea `SignupRequest` pendiente y verifica el correo.
3. El backend genera checkout en proveedor. El frontend recibe solo URL/token público permitido.
4. El proveedor envía webhook.
5. El backend valida firma, ID único, vigencia y coherencia del evento; reconsulta al proveedor cuando el adaptador lo requiera.
6. Solo un estado de pago/suscripción confirmado inicia aprovisionamiento.
7. En una transacción se crea o activa Tenant, Administrator, Subscription, cuotas y evento de auditoría.
8. Si el aprovisionamiento falla, la suscripción queda en estado recuperable; un job idempotente reintenta sin duplicar Tenant.
9. El administrador recibe enlace temporal para establecer contraseña; nunca una contraseña generada por correo.

## Estados recomendados
Signup: `PENDING_EMAIL | VERIFIED | CHECKOUT_CREATED | ACTIVATING | ACTIVE | EXPIRED | CANCELLED`.
Subscription: `PENDING | ACTIVE | PAST_DUE | SUSPENDED | CANCELLED`.
Checkout: `CREATED | PENDING | PAID | FAILED | EXPIRED | REFUNDED`.

## Seguridad
- HTTPS obligatorio; HSTS en producción.
- CSP estricta y orígenes CORS explícitos.
- Cookies/sesiones según arquitectura de identidad existente; no guardar tokens sensibles en localStorage.
- CSRF si se usan cookies autenticadas.
- Rate limit en registro/login/recuperación/checkout.
- CAPTCHA/anti-bot adaptativo en abuso, no como único control.
- Webhooks con firma y secreto rotatable.
- Secretos solo en gestor/variables protegidas del entorno.
- Logs sin contraseñas, tokens, datos de tarjeta ni payloads sensibles.
- Aislamiento Tenant y pruebas negativas cross-tenant.
- Auditoría de cambios de plan, altas, suspensiones, pagos y cambios de permisos.
- Backups y procedimiento de rollback antes de migraciones productivas.

## Privacidad y legal
Antes de aceptar registros reales deben existir textos aprobados de Términos, Privacidad y tratamiento de datos. El checkbox debe almacenar versión del documento, timestamp y evidencia técnica necesaria; no se debe afirmar cumplimiento regulatorio que no haya sido verificado.

## NEXUS en la web
La web puede presentar las capacidades actuales y el rumbo del producto. Debe distinguir:
- **Disponible:** contexto autorizado, consultas operativas implementadas y auditoría actual.
- **En evolución:** memoria, razonamiento, planificación, ejecución, aprendizaje y agentes avanzados.
NEXUS nunca se presenta como sustituto de una validación oficial ni como garantía de cumplimiento.

## Imágenes y marca
Las imágenes deben ser propias o con licencia compatible. Las composiciones generadas durante diseño sirven como referencia visual; no se publican logos, clientes, testimonios, estadísticas, precios ni certificaciones ficticias. Las capturas reales deberán usar datos de demostración anonimizados.

## Pasarela
Culqi, Mercado Pago y Niubiz quedan como candidatos. La elección exige investigación vigente de: soporte de suscripciones/recurrentes, métodos disponibles en Perú, webhooks, sandbox, conciliación, reembolsos, comisiones, contratos y condiciones tributarias. Hasta elegir proveedor, se usa una interfaz `PaymentProvider` para evitar acoplar el dominio.

## Definition of Done para producción
- Copy y marca aprobados.
- Planes/precios/condiciones aprobados.
- Términos y Privacidad aprobados.
- API de onboarding implementada y probada.
- Proveedor de pago validado en sandbox.
- Pruebas de webhook falso, duplicado, tardío y fuera de orden.
- Pruebas de doble clic/idempotencia.
- Pruebas de fallo durante aprovisionamiento.
- Pruebas cross-tenant y RBAC.
- Pruebas responsive, accesibilidad y navegadores.
- Staging aprobado.
- Backup y rollback probados.
- Observabilidad y alertas activas.
- Revisión final antes de promover a producción.

## Regla de despliegue
Esta rama no se fusiona ni despliega a producción automáticamente. Primero se revisa el PR, se ejecutan pruebas y se publica en staging. La promoción a `main` y producción se realiza únicamente después de aprobación.
