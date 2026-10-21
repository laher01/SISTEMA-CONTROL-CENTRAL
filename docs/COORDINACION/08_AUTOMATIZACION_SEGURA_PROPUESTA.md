# Política central de integración y despliegue automatizados — propuesta

**Estado:** propuesta en PR; no vigente hasta integrarse en main y verificar CI.

## Alcance común
Todos los chats presentes y futuros que escriben en `laher01/SISTEMA-CONTROL-CENTRAL` siguen esta misma política, independientemente del módulo. Primero consultar `AGENTS.md`, `docs/COORDINACION/`, PR abiertos y responsables. Las ramas/PR en borrador no se integran.

## Separación de controles
1. **PR → main:** mantener revisión de conflictos, alcance, dependencias, cambios de código y CI. La rama `main` debe exigir comprobaciones obligatorias, estar al día con la base y denegar bypass. El presente cambio NO habilita fusiones automáticas de PR; debe diseñarse una compuerta específica con pruebas de protección de rama y rutas críticas antes de automatizarlas.
2. **main → VPS antigua:** `deploy-staging.yml` se inicia con un `push` a `main` o manualmente. Ejecuta pruebas completas del backend y frontend; solo si ambas concluyen satisfactoriamente se ejecuta el job `deploy`. Mantiene un solo despliegue concurrente.
3. **Preflight:** permitir exclusivamente la VPS autorizada, exigir secretos protegidos, árbol Git compatible, espacio y servicio saludable; generar un respaldo PostgreSQL fresco con SHA256 y restaurarlo en una base aislada. Ningún fallo debe permitir llegar al paso de despliegue.
4. **Actualización:** comprobar SHA esperado, evitar divergencias o colisiones, preservar datos locales; verificar servicios y salud al finalizar. Una tarea verde de GitHub **no sustituye** la verificación del commit y rutas críticas efectivamente desplegados.

## Excepciones que permanecen bloqueadas
- Migraciones destructivas; alteraciones tributarias, fórmulas económicas o documentos fiscales protegidos.
- Cambios de autenticación, RBAC, auditoría, aislamiento de tenants, secretos, cifrado, respaldos o recuperación sin revisión de seguridad adicional.
- Falta de evidencia de restauración, fallo de CI, conflicto con otro chat, PR en borrador o cambios no aprobados por los responsables de módulo.
- Intervenciones en VPS distintas de la permitida y cualquier operación irreversible sin autorización específica.

## Activación y seguimiento
La integración de este PR **activaría** intentos automáticos de despliegue de cualquier `push` posterior a `main` (incluido el merge del propio PR). Antes de integrarlo deben revisarse las protecciones de rama, secretos/environment de GitHub, disponibilidad de la VPS y capacidad de restauración. Si una condición falla, el workflow debe bloquear la actualización; no forzar bypass. El acceso SSH y los logs de ejecución se verifican en GitHub Actions, nunca mediante suposiciones.

La propuesta no garantiza monitoreo permanente desde una conversación ni modifica automáticamente las instrucciones de chats ya abiertos. Las instrucciones compartidas solo se actualizan después de integrar la política.
