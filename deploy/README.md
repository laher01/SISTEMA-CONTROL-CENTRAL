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

## Actualización automática desde GitHub

Crear el Environment `staging` en GitHub y guardar estos secretos:

- `VPS_HOST`: IP pública de la VPS.
- `VPS_USER`: usuario SSH de despliegue, inicialmente `ubuntu`.
- `VPS_DEPLOY_PATH`: `/home/ubuntu/fact-central`.
- `VPS_SSH_PRIVATE_KEY`: clave privada exclusiva para despliegue.
- `VPS_SSH_KNOWN_HOSTS`: huella SSH verificada de la VPS.

El despliegue automático queda habilitado por defecto: cada cambio aceptado en `main` ejecuta
todas las pruebas y, solo si backend y frontend aprueban, GitHub continúa con el despliegue.

Antes de conectarse, el workflow valida que todos los secretos anteriores existan. Después entra por
SSH, descarga `main`, verifica que la VPS quede exactamente en el commit que disparó el workflow,
crea un respaldo de PostgreSQL, reconstruye los contenedores y comprueba `/health`.

El disparo manual (`workflow_dispatch`) se mantiene únicamente como contingencia para volver a
desplegar la versión actual sin modificar código.

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
