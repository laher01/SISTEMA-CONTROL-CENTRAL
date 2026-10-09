# Etapa 7 — Infraestructura, versiones y despliegues

Fecha: 2026-10-09. Base verificada: `origin/main` en `392e67d`.
Rama de desarrollo: `feature/etapa-7-infraestructura`.

## Diagnóstico y decisión de integración

La copia inicial estaba en `feature/saas-documentation-v2` y tenía código local
sin registrar, incompatible con la distribución actual. Se conserva intacta.
Se consultó GitHub y se creó un checkout separado de main actualizado en
`.worktrees/etapa7`, dentro del proyecto. Main incluye FastAPI, SQLAlchemy,
PostgreSQL, React, cookies de sesión, aislamiento por host, SUPERADMIN, 15
migraciones Alembic, CI backend/frontend y despliegue Oracle/Cloudflare Tunnel.
Redis no está desplegado en el Compose actual. No se inventa ese servicio.
Las 72 pruebas de la copia antigua no certifican la versión actual.
No se ha consultado directamente la VPS ni modificado producción.

## Diseño autorizado

El plano global de infraestructura se integra a Admin Platform y utiliza la sesión
existente, cambio obligatorio de contraseña y rol SUPERADMIN verificado en backend.
No se aceptan roles ni identidades de cabeceras. Las mutaciones comprueban Origin
cuando lo envía el navegador y se sirven únicamente como JSON o acciones explícitas.
El inventario de nodos es global; las asociaciones de tenants son metadata de
ubicación y no conceden acceso a registros de negocio de otros tenants.

Se añaden tablas separadas para nodos, reportes, versiones, asociaciones y auditoría
operacional. La migración 0016 expande el esquema de 0015 sin modificar datos previos.
Los endpoints privados son inventario: el backend no hace HTTP ni SSH a esos destinos.
Los agentes envían reportes mediante Bearer individual aleatorio. Se guarda SHA-256;
el token se entrega una sola vez al generar/rotar credencial, con Cache-Control no-store.
Desactivar un nodo invalida su acceso. Repetir un reporte con el mismo UUID devuelve
el resultado previo; otro contenido con la misma clave da conflicto.

Sin reporte se muestra DESCONOCIDO. CPU/RAM/disco y servicios son información reportada
por el agente, nunca valores simulados. El servidor fija la hora de recepción.
Los umbrales y la tolerancia de desconexión se configuran mediante variables FC_.
Los registros de versión contienen commit, imagen por digest, entorno y compatibilidad.
Una versión registrada no demuestra que esté instalada ni que un despliegue haya pasado.

## Fases y aceptación

1. Inventario local/remoto y documentación.
2. Modelos, migración, nodos, SUPERADMIN y auditoría.
3. Reportes autenticados, desconexión, healthchecks y alertas.
4. Panel React integrado con datos reales y estados de carga/error.
5. Versiones y CI/Docker.
6. Despliegues mediante agente autorizado.
7. Backups y recuperación diferenciada de datos/contenedores.
8. Asociación tenant/nodo y lotes canary.
9. Regresión, seguridad y documentación.
10. Commits, push y PR.

Toda fase se valida antes de declararla terminada. Las pruebas de staging,
PostgreSQL real, restauración aislada y la VPS requieren entornos disponibles.
Las migraciones no se ejecutarán sobre producción durante el desarrollo.

## Estado inicial

Diagnóstico realizado; implementación y verificaciones se registrarán por bloque.
No hay módulos de esta etapa declarados completos.

## Bloque 1 — Registro, monitoreo y panel

Implementados registro/edición/desactivación lógica de nodos, rotación de credencial,
reportes idempotentes autenticados, alertas por umbrales/desconexión/servicios,
registro de versiones por digest, ubicación de tenants y auditoría correlacionada.
El panel React reutiliza la sesión actual. Los endpoints nuevos tienen prefijo
`/api/v1/infraestructura`: `nodos`, `nodos/{id}/credencial`, `agentes/{id}/reportes`,
`dashboard`, `versiones`, `asociaciones`, `eventos` y `salud`.
Las respuestas nunca incluyen hashes de tokens ni claves SSH.

Variables: `FC_INFRA_DESCONEXION_SEGUNDOS` (180), `FC_INFRA_CPU_UMBRAL` (90),
`FC_INFRA_RAM_UMBRAL` (90), `FC_INFRA_DISCO_UMBRAL` (85).
El dashboard muestra hasta 200 nodos; la colección admite `limite` y `offset`.
Las versiones/eventos muestran los últimos 100 registros. Los reportes requieren
política de retención antes de habilitar una flota productiva prolongada.

Validaciones locales iniciales: 133 pruebas backend correctas, una omitida;
Ruff y mypy sin errores. Frontend: lint sin errores (aviso anterior en Chat.tsx),
cuatro pruebas correctas, typecheck y build correctos. SQL PostgreSQL de todas las
migraciones generado sin errores; ejecución PostgreSQL todavía no verificada.
Se corrigieron dos pruebas anteriores que enviaban strings donde SQLAlchemy requiere UUID.
El inventario PostgreSQL/Redis de la VPS no se ha verificado: Redis figura NO_CONFIGURADO
en salud local porque no existe en el Compose actual.

No se declara completa la Etapa 7 ni se asigna un porcentaje sin evidencia de staging,
recuperación real y CI remoto. El siguiente bloque desarrolla agente y despliegues.
