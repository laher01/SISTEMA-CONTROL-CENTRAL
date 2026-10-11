# OAuth de correo — diagnóstico y plan de integración (11-10-2026)

## Hallazgos revisados en main

- `backend/app/api/routes/correo.py` **sí** contiene: registro de buzones/remitentes, `POST /api/v1/correo/buzones/{buzon_id}/google/iniciar`, callback `GET /api/v1/correo/google/callback`, comprobación de identidad del buzón, persistencia cifrada y activación del buzón.
- `backend/app/services/google_oauth_correo.py` **sí** contiene: URL de consentimiento con scope `gmail.readonly`, PKCE S256, intercambio/renovación de tokens, comprobación de cuenta y primitivas de lectura de mensajes Gmail.
- `backend/app/core/config.py` declara variables OAuth Google, Microsoft y control de worker Google. Microsoft tiene configuración preliminar **y un constructor de URL de consentimiento PKCE** en `backend/app/services/microsoft_oauth_correo.py`; no se confirmó callback, canje de token ni Graph operativo en las rutas revisadas.
- `backend/app/api/routes/auth.py` mantiene login interno con sesión y RBAC. **No confundir** OAuth de acceso al buzón con OIDC para iniciar sesión en FACT CENTRAL.
- `GET /api/v1/correo/estado-proveedores` indica **configuración**, no conexión operativa. Debemos diferenciar configurado, autorizado, activo, sincronizando y error.
- Los antecedentes de conversación reportaban Google sin callback, pero el código actual ya lo incorpora. **No reimplementar lo que existe**.

## Posibles causas de los fallos anteriores (por validar en staging)

1. Falta/mala carga de `FC_GOOGLE_OAUTH_CLIENT_ID`, `FC_GOOGLE_OAUTH_CLIENT_SECRET`, `FC_GOOGLE_OAUTH_REDIRECT_URI` o `FC_CORREO_TOKEN_ENCRYPTION_KEY` dentro del **contenedor backend**, no solo en el host.
2. URI de redirección distinta a la registrada exactamente en Google Cloud (esquema HTTPS, host, ruta, barra final).
3. Proyecto OAuth sin usuario de prueba autorizado, aplicación en modo Testing, scope Gmail restringido o consentimiento denegado. Los refresh tokens de apps External en Testing pueden tener duración limitada.
4. La cuenta autorizada no coincide exactamente con el buzón registrado. Revisar la diferencia histórica entre `factur.central.2023@gmail.com` y `factura.central.2023@gmail.com`. La dirección indicada por el usuario es **factura.central.2023@gmail.com**.
5. Las cookies de sesión `SameSite=Strict` podrían no acompañar el retorno externo de Google. El callback llama `validar_sesion_host`: comprobar en pruebas si rechaza el callback legítimo sin abrir ataques CSRF; conservar `state` de un uso y validación tenant/cuenta.
6. Un callback exitoso no garantiza worker activo: verificar `FC_CORREO_GOOGLE_WORKER_ENABLED`, proceso, scheduler y logs sin datos sensibles.
7. OAuth de Microsoft/Graph aún no está completado: existe `crear_url_microsoft`, pero el consentimiento por sí solo no conecta el buzón. No marcar Outlook como conectado solo porque exista Client ID.

## Diagnóstico sin publicar secretos

Ejecutar **dentro del entorno backend** con las variables `FC_*` ya cargadas:

```bash
python scripts/oauth_preflight.py
```

Si el script no está montado en el contenedor, ejecutarlo en la VPS con el mismo entorno **sin imprimir ni compartir el archivo .env**. El script únicamente verifica presencia y formato, no revela valores ni crea conexiones.

Callback Google previsto según `correo.py`: `/api/v1/correo/google/callback`. Confirmar la URL pública efectiva a partir de la configuración real y del reverse proxy.

## Checklist de implementación

- [x] Rama aislada creada desde `main`.
- [x] Diagnóstico local de configuración sin exponer secretos.
- [ ] Prueba automatizada del preflight (entorno ausente, callbacks inválidos, clave Fernet errónea).
- [ ] Confirmar comportamiento de cookies y retorno cross-site de Google; ajustar de manera segura tras prueba.
- [ ] Verificar migraciones Alembic de credenciales/intentos de OAuth en base staging.
- [ ] Probar Google con autorización real de **factura.central.2023@gmail.com** desde cuenta administrativa válida y un tenant de prueba.
- [ ] Comprobar refresh token cifrado, reautorización/revocación y reconexión sin duplicados.
- [ ] Worker real Gmail, manejo de paginación, rate limits, adjuntos y deduplicación: revisar cobertura y completar.
- [ ] Microsoft Entra: tenant/authority, client secret, `offline_access`, `Mail.Read`, PKCE, callback, validación de cuenta, cifrado y Graph.
- [ ] Mostrar estados verificables por proveedor en React, con errores útiles sin exposición de credenciales.
- [ ] Pruebas unitarias/integración, lint, migraciones, y pruebas E2E en staging.
- [ ] Solo tras CI aprobado, revisión y staging funcional: PR listo para revisión hacia `main`. No desplegar ni fusionar automáticamente.

## Límites

Esta rama aún **no** completa Microsoft ni confirma conexión efectiva con Google. El script es únicamente preflight; ningún resultado debe mostrarse como «OAuth conectado». Mantener tokens/credenciales fuera de Git y preservar aislamiento multi-tenant, jerarquías y registros de auditoría.
