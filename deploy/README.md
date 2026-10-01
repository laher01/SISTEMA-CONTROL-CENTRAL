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
   PostgreSQL larga y aleatoria.
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

Después de guardar los secretos, crear la variable del Environment
`ENABLE_STAGING_DEPLOY=true`. Mientras no exista, GitHub ejecutará las validaciones pero omitirá
el acceso a la VPS, evitando despliegues incompletos.

Cada cambio aceptado en `main` ejecuta todas las pruebas. Solo si backend y frontend aprueban,
GitHub entra por SSH, descarga `main`, crea un respaldo de PostgreSQL, reconstruye los contenedores
y comprueba `/health`.

## Operación

```bash
docker compose --env-file deploy/.env.production \
  -f deploy/docker-compose.production.yml ps

docker compose --env-file deploy/.env.production \
  -f deploy/docker-compose.production.yml logs -f --tail=100
```

Los respaldos automáticos se guardan en `deploy/backups` y se conservan 14 días.
