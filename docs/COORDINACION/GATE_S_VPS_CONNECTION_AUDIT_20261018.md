# Gate S — Inventario GitHub / mecanismos VPS y decisión de continuación
Fecha: 2026-10-18
Estado: **OPEN — No desplegar, fusionar ni modificar VPS**.

## Referencias verificadas (HEAD exactos)
| PR | HEAD | Estado | CI |
|---|---|---|---|
| #264 | `4c0fc3259f73ded1ce307901e43908ee0b86ff4c` | OPEN/DRAFT, sin fusionar | 7/7 SUCCESS |
| #290 | `916a5a4323b885729eab611a660b8f67fdbf24a4` | OPEN/DRAFT, sin fusionar | 4/4 SUCCESS |
| #293 | `8909346939fef50f732d85bc57585b09a0a457ef` | OPEN/DRAFT, sin fusionar | 4/4 SUCCESS |
| #294 | `c4be6af8d245207dbce05ed15a7ea6575bb75c9c` | OPEN/DRAFT, sin fusionar | 4/4 SUCCESS |

**Nota:** aprobación CI del HEAD documental no reemplaza restore completo de DB + archivos ni pruebas de producción.

## Inventario de conexión
Inspeccionado contra rama `main`, sin ejecutar workflows:
- `.github/workflows/alembic-vps-diagnostic.yml`: `workflow_dispatch`; en `main` ejecuta script remoto `deploy/inspect-alembic-readonly.sh` desde Actions y secrets del environment `staging`. El job valida script y consulta revisión SQL Alembic. La validación estática enumera comandos prohibidos como cadenas, no ejecuta migraciones. Destino fijado a VPS antigua.
- `.github/workflows/secretaria-vps-preflight.yml`: `workflow_dispatch`, SSH y `deploy/preflight-secretaria.sh`; revisa Git, espacio, backend health y Docker. Si se proporciona `EXPECTED_COMMIT`, el script puede ejecutar `git fetch`; no considerarlo estrictamente sin escritura en ese caso.
- `.github/workflows/audit-vps-staging.yml`: `workflow_dispatch` pero **sí escribe** respaldo `pg_dump` y archivo SHA; NO usar para diagnóstico estrictamente read-only.
- `.github/workflows/deploy-staging.yml`: dispara por push a main o manualmente; puede modificar servicios y Git remoto. No usar como prueba de conexión.
- `deploy/README.md`: diferencia VPS antigua staging de VPS Oracle con túnel independiente `factcentral.online`. No asumir que Actions staging accede a Oracle.

Nombres de secretos requeridos, sin leer valores: `VPS_HOST`, `VPS_USER`, `VPS_DEPLOY_PATH`, `VPS_SSH_PRIVATE_KEY`, `VPS_SSH_KNOWN_HOSTS`.
Solo se comprobó **configuración de código**, no disponibilidad de credenciales, autorización de environment, red SSH ni respuesta de VPS.

## Limitación de herramientas en este chat
El conector GitHub disponible permite leer código/PR/CI y editar ramas autorizadas. No se identificó aquí herramienta directa SSH ni disparo `workflow_dispatch`; no declarar diagnóstico remoto ejecutado.

## Siguiente gate verificable
1. Responsable identifica entorno objetivo (VPS antigua staging versus Oracle) y concede autorización específica de inspección read-only.
2. Emplear únicamente workflow/script clasificado como lectura y destino correcto; validar que logs no exponen secretos.
3. Verificar directorio, SHA instalado, contenedores/health, versión Alembic, almacenamiento y espacio; dejar capturas/logs de ejecución.
4. Definir respaldo consistente y pareado DB + almacenamiento, manifiesto SHA256, restauración en entorno segregado autorizado, comprobación FACT/GRE/VCHR/ítems y rollback.
5. Validar CI de código candidato exacto y obtener revisión/aprobación humana. Gate S permanece OPEN hasta completar evidencia real.

**Alcance de esta rama:** documentación de inventario únicamente; ningún cambio runtime.
