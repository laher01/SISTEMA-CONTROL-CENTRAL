# Auditoría remota restringida — VPS Oracle antigua

**Estado:** propuesta para revisión. No habilita acceso SSH por sí misma, no crea credenciales y no modifica la VPS.

## Alcance

- VPS autorizada: `132.145.233.172`.
- Workflow: `.github/workflows/audit-vps-readonly.yml`.
- Activación **manual** (`workflow_dispatch`) únicamente tras integrar el workflow con aprobación; GitHub generalmente solo permite despacharlo desde la rama predeterminada.
- GitHub Environment **nuevo**: `audit-vps-readonly`, distinto de `staging`.
- Secretos **exclusivos**: `AUDIT_VPS_SSH_PRIVATE_KEY` y `AUDIT_VPS_SSH_KNOWN_HOSTS`.
- Cuenta Linux dedicada sin sudo ni grupo docker: `factaudit`. No reutilizar el usuario `ubuntu`, claves ni secretos de despliegue.
- No incluye comandos de SQL, Docker, dumps, instalaciones, reinicios, actualizaciones ni cambios de configuración.

## Preparación en VPS (requiere autorización explícita aparte)

Un administrador debe crear la cuenta restringida `factaudit`, sin privilegios. Instalar un script propiedad de root, **no editable por factaudit**, por ejemplo `/usr/local/bin/factcentral-audit-readonly`, con contenido revisado:

```bash
#!/usr/bin/env bash
set -euo pipefail
test "${SSH_ORIGINAL_COMMAND:-}" = "audit-vps-readonly-v1" || exit 126
printf 'AUDIT_PROTOCOL=v1\n'
printf 'HOSTNAME=%s\n' "$(hostname)"
printf 'UTC=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf 'DOCKER_SERVICE=%s\n' "$(systemctl is-active docker 2>/dev/null || true)"
printf 'HEALTH_HTTP_STATUS='
curl --silent --output /dev/null --write-out '%{http_code}\n' \
  --connect-timeout 3 --max-time 8 http://127.0.0.1:18080/health
printf 'AUDIT_END=OK\n'
```

Se permite únicamente informar de esos campos predefinidos. No dar acceso a registros, variables de entorno, archivos documentales ni credenciales.

La **clave pública** específica de auditoría se instala en `~factaudit/.ssh/authorized_keys` con prefijo restrictivo:

```text
restrict,command="/usr/local/bin/factcentral-audit-readonly" ssh-ed25519 <CLAVE_PUBLICA_DE_AUDITORIA>
```

`restrict` deshabilita port forwarding, PTY, agente, X11 y ejecución no autorizada; el forced command debe verificar estrictamente `SSH_ORIGINAL_COMMAND`. Comprobar permisos de `.ssh` (700) y `authorized_keys` (600), y propietario del script root:root (755). La cuenta no debe estar en `sudo` ni en `docker`. Usar `sshd -T` y una conexión de prueba como verificación, con operador autorizado y sin compartir claves privadas en conversaciones.

**Nota:** `curl` y `systemctl` son consultas. Si el servicio no responde, la auditoría debe fallar, no ejecutar remediación automática.

## Configuración GitHub (operador)

1. Generar una identidad SSH **nueva** para auditoría, fuera del repositorio y del chat. La privada va exclusivamente en el secreto `AUDIT_VPS_SSH_PRIVATE_KEY` del Environment `audit-vps-readonly`. La pública se autoriza restringida en la VPS.
2. Verificar la huella SSH del servidor por canal confiable; cargar `AUDIT_VPS_SSH_KNOWN_HOSTS` con la línea host-key validada para **132.145.233.172**. No usar `StrictHostKeyChecking=no` ni confiar ciegamente en `ssh-keyscan`.
3. Restringir el Environment a la rama predeterminada y a operadores autorizados; no conceder a PRs ni forks acceso a secretos. Revisar reglas de aprobación de ambientes y protección de ramas.
4. Revisar el workflow, validar YAML y CI en PR borrador. La prueba SSH solo será posible **después** de que el operador complete la provisión autorizada y se integre el workflow.

## Límites y despliegue

Este mecanismo solo devuelve inventario de estado (host/fecha/docker/health). **No da una sesión SSH interactiva al asistente.** El análisis de resultados dependerá de las herramientas GitHub disponibles; el conector actual no puede despachar workflows por sí mismo.

Ni la existencia del workflow ni el texto de confirmación `vps-desplega-1` autorizan fusiones o despliegues. Todo despliegue requiere confirmación concreta, verificación de SHA, CI, respaldos, restauración y efectos automáticos.

No modificar ni habilitar el antiguo `audit-vps-staging.yml`: utiliza SSH de despliegue y crea copias; no cumple el alcance de solo lectura.
