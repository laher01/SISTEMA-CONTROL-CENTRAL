# Despliegue de pruebas en VPS

Arquitectura aislada para convivir con los servicios existentes de la VPS:

- PostgreSQL 17 solo en la red privada de Docker.
- Backend FastAPI solo en la red privada de Docker.
- Frontend Nginx disponible localmente en `127.0.0.1:18080`.
- Cloudflare Tunnel publica el subdominio sin abrir 80/443 ni otro puerto entrante.
- Volúmenes exclusivos `fact_central_staging_*`.

## Preparación única en la VPS

1. Aplicar primero las actualizaciones de seguridad de Ubuntu. La VPS usa Ubuntu 20.04, que ya
   salió del soporte estándar; debe planificarse la actualización a Ubuntu 22.04 o 24.04.
2. Clonar el repositorio público en `/home/ubuntu/fact-central`.
3. Copiar `deploy/.env.production.example` a `deploy/.env.production` y generar una contraseña
   PostgreSQL larga y aleatoria. Confirmar `FC_TENANT_RUC`: se usa para distinguir al receptor de
   los proveedores durante la extracción automática de comprobantes de compra.
4. En Cloudflare Zero Trust crear un Tunnel y configurar el hostname
   `factcentral.nexomarnegocioseirl.online` con servicio `http://frontend:80`.
5. Proteger el hostname con Cloudflare Access antes de habilitarlo, porque el MVP todavía no tiene
   autenticación propia.
6. Copiar el token del Tunnel a `CLOUDFLARE_TUNNEL_TOKEN` en `.env.production`.
7. Ejecutar `chmod +x deploy/deploy.sh && bash deploy/deploy.sh`.

No se deben publicar los puertos de PostgreSQL ni FastAPI. El puerto 18080 escucha solo en
localhost y sirve para comprobaciones dentro de la VPS.

## Despliegue desde GitHub

El workflow `.github/workflows/deploy-staging.yml` ejecuta verificación de backend, frontend y
recuperación aislada en los cambios de `main`. **El despliegue automático está deshabilitado por
defecto**: solo entra al job `deploy` en un push a `main` cuando la variable de repositorio
`ORACLE_AUTO_DEPLOY_ENABLED` vale `true`. El workflow también exige
`ORACLE_RECOVERY_VERIFIED=true` en el Environment `oracle-autodeploy`; estos valores deben
habilitarse únicamente después de coordinar y aprobar la operación.

El workflow actual restringe SSH a `ubuntu@132.145.233.172` y valida la ruta
`/home/ubuntu/fact-central`. El Environment `staging` proporciona los secretos para
`workflow_dispatch`; el Environment `oracle-autodeploy` proporciona los secretos para el evento
`push`. En el Environment usado por cada evento deben existir:

- `VPS_HOST`: debe ser `132.145.233.172`.
- `VPS_USER`: debe ser `ubuntu`.
- `VPS_DEPLOY_PATH`: debe ser `/home/ubuntu/fact-central`.
- `VPS_SSH_PRIVATE_KEY`: clave privada exclusiva para despliegue.
- `VPS_SSH_KNOWN_HOSTS`: huella SSH verificada de esa VPS.

Antes de modificar la VPS, el workflow fija y valida el SHA de `main`, ejecuta las pruebas y
comprobaciones de recuperación, realiza el preflight remoto y verifica un respaldo PostgreSQL. Solo
entonces reconstruye los contenedores y consulta `/health`. Un workflow exitoso no confirma por sí
solo que el hostname público de Cloudflare, los roles ni los flujos documentales estén operativos;
esos puntos requieren una verificación funcional independiente.

`workflow_dispatch` queda como operación manual de contingencia y usa el Environment `staging`.
La existencia de secretos o el éxito de CI no habilitan el despliegue automático por sí mismos.

## Operación

```bash
docker compose --env-file deploy/.env.production \
  -f deploy/docker-compose.production.yml ps

docker compose --env-file deploy/.env.production \
  -f deploy/docker-compose.production.yml logs -f --tail=100
```

Los respaldos automáticos se guardan en `deploy/backups` y se conservan 14 días.


## Nota de operación: túnel Oracle (octubre 2026)

La VPS Oracle (Ubuntu 24.04, x86_64) usa el **mismo repositorio y Compose** con un túnel
Cloudflare **independiente** `fact-central-oracle` y dominio `factcentral.online`.
El túnel anterior `fact-central-staging` corresponde a otra VPS y **no debe alterarse**.

Incidencia diagnosticada en Oracle: `cloudflared` reiniciaba porque el comando se ejecutaba
sin un valor tras `--token`. El archivo `deploy/.env.production` contenía un token
no vacío, pero la sesión Bash había exportado `CLOUDFLARE_TUNNEL_TOKEN` como variable
**vacía**; esa variable prevalecía sobre `--env-file` al interpolar Compose.

Solución validada en Oracle:

1. `unset CLOUDFLARE_TUNNEL_TOKEN` en la sesión que ejecuta Compose.
2. Mantener `CLOUDFLARE_TUNNEL_TOKEN=<token real>` solo en `deploy/.env.production`,
   con permisos `600`, sin subir jamás ese archivo al repositorio.
3. La instrucción de Compose es `tunnel run --token ${CLOUDFLARE_TUNNEL_TOKEN:?...}`:
   `cloudflared` ya aporta su entrypoint `--no-autoupdate`, y la interpolación
   requerida evita iniciar con un token vacío.
4. Iniciar solo el túnel (cuando el frontend esté listo) con
   `docker compose --env-file deploy/.env.production -f deploy/docker-compose.production.yml up -d --no-deps --force-recreate tunnel`.
5. Verificar `docker ps`, `docker logs --tail 20 fact-central-staging-tunnel-1`
   (censurando secretos) y el estado del túnel en Cloudflare One.

**Estado observado:** Cloudflare One muestra ambos túneles en estado **Óptimo**.
Esto prueba la conexión del túnel, **no** que FastAPI, React o `factcentral.online`
estén operativos; el backend/frontend y la protección Access deben verificarse.

**Pendiente:** configurar y validar el despliegue automático de Oracle desde GitHub Actions.
El workflow `deploy-staging.yml` actual apunta solo al entorno `staging`;
haber creado secretos en `oracle-production` no activa ese segundo destino.
No fusionar cambios a `main` sin comprobar su efecto en la VPS anterior,
los permisos SSH desde GitHub y el comportamiento de `deploy/deploy.sh`.


## NEXUS contextual

NEXUS funciona en dos niveles:

1. **Contextual determinístico**: activo por defecto. Usa la sesión, la ruta, el ámbito
   autorizado, PostgreSQL y la Knowledge Base versionada en `docs/`.
2. **Conversacional**: se activa cuando se configura un endpoint LLM compatible mediante
   `FC_NEXUS_LLM_URL`, junto con su token y modelo cuando el proveedor lo requiera.

Variables disponibles:

- `FC_NEXUS_LLM_URL`
- `FC_NEXUS_LLM_TOKEN`
- `FC_NEXUS_LLM_MODEL`
- `FC_NEXUS_LLM_TIMEOUT_SECONDS`
- `FC_NEXUS_KNOWLEDGE_ENABLED`
- `FC_NEXUS_HISTORY_MESSAGES`
- `FC_NEXUS_CONTEXT_MAX_CHARS`

Las credenciales del proveedor nunca deben subirse a GitHub. Deben permanecer únicamente en
`deploy/.env.production` con permisos restringidos.

El contenedor backend incorpora la documentación Markdown de FACT CENTRAL en cada build. Por eso
los cambios aceptados en las librerías de `docs/` pasan a formar parte de la Knowledge Base de
NEXUS después del siguiente despliegue.

Aunque exista un motor conversacional externo, NEXUS no amplía permisos, no cambia Tenant, no
aprueba pagos y no modifica datos críticos por sí mismo.
