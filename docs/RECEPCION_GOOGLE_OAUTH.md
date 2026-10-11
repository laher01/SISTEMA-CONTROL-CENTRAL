# FACT CENTRAL — Google OAuth de recepción documental

## Buzón inicial

El buzón confirmado es `factura.central.2023@gmail.com`. Los demás buzones
registrados en ADMINISTRACIÓN son independientes y requieren su propio consentimiento.

## Preparación segura en Google Cloud

1. Habilitar **Gmail API** en el proyecto Google Cloud.
2. Configurar la pantalla de consentimiento OAuth de la aplicación.
3. Crear un cliente OAuth de tipo **Aplicación web** y registrar exactamente
   `https://app.nexomarnegocioseirl.online/api/v1/correo/google/callback`
   entre los URI de redirección autorizados.
4. Si la app está en modo de pruebas, añadir al titular de
   `factura.central.2023@gmail.com` a los usuarios de prueba.
5. Revisar los requisitos de Google para el scope restringido
   `https://www.googleapis.com/auth/gmail.readonly`. Antes de abrir a terceros
   pueden requerirse verificación y evaluaciones de seguridad adicionales.

**Nunca incluir Client Secret, refresh tokens ni claves Fernet en GitHub ni en este chat.**

## Configuración VPS

Colocar en `deploy/.env.production`, con permisos restrictivos:

- `FC_GOOGLE_OAUTH_CLIENT_ID`: ID del cliente de Google Cloud
- `FC_GOOGLE_OAUTH_CLIENT_SECRET`: secreto del cliente
- `FC_GOOGLE_OAUTH_REDIRECT_URI=https://app.nexomarnegocioseirl.online/api/v1/correo/google/callback`
- `FC_CORREO_TOKEN_ENCRYPTION_KEY`: clave Fernet generada de forma segura

Para generar una clave Fernet localmente con la dependencia instalada:

```bash
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

La clave debe guardarse de forma segura, con respaldo cifrado: si se pierde
no podrán descifrarse las autorizaciones existentes.

## Autorizar cada buzón

Entrar como ADMINISTRADOR → Configuración → Recepción Automática,
seleccionar el buzón Google registrado, pulsar **Conectar con Google**
e iniciar sesión en esa cuenta concreta. FACT CENTRAL verifica con Gmail API
que el email devuelto coincida exactamente con el registro del buzón.
El estado OAuth expira a los diez minutos, solo funciona una vez y
se vincula al tenant y administrador que lo inició.

## Sincronización periódica opcional

El worker está desactivado por defecto para no utilizar credenciales
inexistentes. Tras verificar la conexión, activar en la VPS:

```text
FC_CORREO_GOOGLE_WORKER_ENABLED=true
FC_CORREO_GOOGLE_INTERVAL_SECONDS=300
COMPOSE_PROFILES=correo
```

El despliegue existente aplica el perfil cuando `COMPOSE_PROFILES=correo`
está en `deploy/.env.production`. El worker usa Gmail API en modo de solo lectura,
conserva UID por buzón, no duplica documentos, procesa cada tenant por separado
y registra los errores operativos sin imprimir tokens.

Este módulo no concede permisos para enviar correos ni modifica los mensajes.
Outlook/Microsoft requiere una integración OAuth independiente.
