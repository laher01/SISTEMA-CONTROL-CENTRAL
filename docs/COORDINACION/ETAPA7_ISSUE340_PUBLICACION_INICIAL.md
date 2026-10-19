# Etapa 7 — Issue #340: publicación inicial Landing/CMS y cadena Alembic

Estado: IMPLEMENTACIÓN PROPUESTA EN DRAFT PR #341 / SIN NUEVA REVISIÓN ALEMBIC. Propietario funcional: Etapa 7.
Coordinación: https://github.com/laher01/SISTEMA-CONTROL-CENTRAL/issues/340
PR consumidor MISD: #336 (base #292). No realizar merge ni despliegue desde este documento.

## Evidencias revisadas en main (2026-10-19)

- `backend/alembic/versions/20261017_0039_landing_global.py`: crea `configuracion_landing_global.activa` con `server_default=TRUE` e inserta `(id=1, activa=TRUE, version=1)`.
- `backend/alembic/versions/20261018_0041_landing_publicacion_explicita.py`: cambia solamente el `server_default` de la columna a FALSE, **sin actualizar filas**. Mantiene el estado editorial existente.
- `backend/app/api/routes/pagina_web.py` en main: `estado_publico` devuelve FALSE si falta fila; `actualizar_estado` crea FALSE si falta fila. Esta parte de la observación P2 de Codex ya no describe el código actual, pero **la inserción de 0039 continúa en TRUE**.
- El archivo 0041 de la rama auxiliar MISD #336 coincide con el de main. La migración MISD 0042 depende de 0041.

## Política requerida antes de modificar datos

**NO** actualizar indiscriminadamente filas existentes: el TRUE de una instalación desplegada puede representar una publicación autorizada. Tampoco reescribir a ciegas 0039 o renumerar migraciones aprobadas: cambiaría el comportamiento de migraciones históricas y puede producir ramas Alembic incompatibles.

Para que instalaciones nuevas sean privadas sin alterar decisiones editoriales antiguas, hace falta una señal segura de primera instalación o una secuencia de migración inicial acordada por Etapa 7 y responsables de Alembic. La ausencia de esa señal exige definir el procedimiento de inicialización, no deducir el consentimiento a partir de TRUE.

## Propuesta de implementación coordinada

1. Etapa 7 identifica la ruta real de aprovisionamiento para nuevas instalaciones y decide el punto de creación de la única configuración global. Se requiere comenzar en FALSE salvo publicación expresa por SUPERADMIN.
2. Elige estrategia versionada compatible con la secuencia actual (0040 → 0041 → 0042) **sin reutilizar 0042** ni crear heads divergentes.
3. Mantiene el valor editorial de filas existentes; prueba rollback y recuperación.
4. Asegura que `GET /plataforma/landing/publico` devuelva FALSE para una instalación nueva antes de publicación explícita, y que cambios autenticados conserven auditoría/versionado.

## Pruebas obligatorias (pendientes, no declaradas exitosas)

- Instalación limpia: ejecutar todos los upgrades hasta el HEAD acordado; verificar FALSE en `id=1` antes de cambios de SUPERADMIN.
- Base instalada con `activa=TRUE`: migrar sin modificar TRUE ni versión ni auditoría.
- Base instalada con `activa=FALSE`: migrar sin modificar FALSE ni versión ni auditoría.
- Publicación autenticada: TRUE solo después de orden expresa, con control de versión y auditoría; denegar usuarios no SUPERADMIN.
- Downgrade/upgrade; un solo HEAD Alembic y consistencia 0041→0042 MISD.
- CI backend + migración + integración y revisión de seguridad/documentación.

## P1 y P2 del PR #336

P1: archivo 0041 idéntico a main, se necesita coordinación histórica y de propietario; no cerrar el hilo por mera coincidencia.
P2: el seed TRUE en 0039 sigue sin cumplir el criterio de estado inicial no publicado; los endpoints de main sin fila ya devuelven/crean FALSE. No cerrar sin solución y pruebas.

Este documento prepara la corrección; **no constituye implementación ni prueba exitosa**.

## Implementación propuesta en PR #341 (2026-10-19)

Se ajustó **solo para instalaciones nuevas** el código fuente de la migración `0039`: la columna `activa` tiene `server_default=FALSE` y la fila inicial se inserta con `activa=FALSE`. El `0041` de `main` queda intacto y sigue estableciendo `server_default=FALSE`. No se añade revisión ni head Alembic, preservando `0041→0042` en la integración MISD.

**Limitación consciente:** cambiar el código de una migración histórica afecta las instalaciones nuevas que aún no ejecutaron `0039`; Alembic NO vuelve a ejecutar `0039` sobre bases ya migradas, por tanto no cambia el estado editorial de esas bases. Este cambio exige revisión del responsable de Etapa 7 por tratarse de archivo histórico, además de prueba de upgrade desde cero e inspección de estados existentes. Si la política del proyecto prohíbe cualquier edición de migraciones antiguas, revertir el cambio y acordar una inicialización distinta, antes de fusionar.

Se añadió la prueba `backend/tests/test_landing_initial_migration.py` para verificar el default y el INSERT del paso 0039 y que el downgrade conserva el orden de eliminación. **No garantiza por sí sola el upgrade integral de PostgreSQL**: debe comprobarse con CI y despliegue de prueba aislado, nunca en VPS productiva.
