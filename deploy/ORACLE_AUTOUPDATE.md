# Actualización automática en Oracle (reutiliza deploy/deploy.sh)

La VPS Oracle usa el mismo repositorio y el mismo `deploy/deploy.sh` que la VPS anterior. El puerto 22 de Oracle está restringido a la IP de administración; por eso los runners alojados por GitHub no tienen acceso SSH sin configurar una conexión de red adicional.

Como alternativa sin abrir SSH público, `deploy/check-updates.sh` consulta `origin/main` desde Oracle cada diez minutos mediante `systemd`. Solo cuando encuentra un commit nuevo de avance lineal ejecuta el **script original**. Este conserva sus respaldos de PostgreSQL y la comprobación de `/health`. No configura credenciales nuevas, no modifica volúmenes ni la VPS anterior.

Antes de habilitar un temporizador en un servidor de uso real, verificar:
- que los checks CI de `main` son obligatorios antes de integrar cambios;
- que Docker funciona para el usuario de servicio `ubuntu` y `deploy.sh` pasa en Oracle;
- que queda RAM/disco suficiente para `docker compose build --pull` en una VPS de 1GB;
- que `deploy/.env.production` es privado (600), tiene token real y no hay una variable Bash exportada vacía de igual nombre;
- que `factcentral.online` tiene Cloudflare Access y HTTPS comprobados antes de introducir contraseñas.

Archivos de unidades incluidos en `deploy/systemd/`: `factcentral-update.service` y `factcentral-update.timer`. La **instalación inicial de las unidades en la propia VPS exige permisos de administrador** (copiarlas a `/etc/systemd/system`, recargar systemd, habilitar timer). Agregarlas a GitHub **no** las instala ni activa por sí solo en Oracle. La ejecución desde el chat no equivale a SSH.

Comprobar desde Oracle mediante `systemctl status factcentral-update.timer`, `journalctl -u factcentral-update.service` y `docker compose --env-file deploy/.env.production -f deploy/docker-compose.production.yml ps`. Si hay un cambio de base de datos incompatible no es suficiente con revertir la imagen: restaurar la copia PostgreSQL siguiendo un procedimiento verificado.

Este es un paso operativo hacia sincronización multi-VPS. El entorno previo `staging` conserva su workflow de despliegue SSH; Oracle consulta el mismo `main` salientemente.
