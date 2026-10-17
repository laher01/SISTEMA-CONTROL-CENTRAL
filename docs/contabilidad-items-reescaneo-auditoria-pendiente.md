# Diseño pendiente: auditoría de trabajos de reprocesamiento XML

Estado: **propuesta técnica, no implementada ni desplegada**. PR #208.

## Separación de permisos
- `GET /api/v1/contabilidad-items/reescaneo/vista-previa` es **solo lectura**, limitado por tenant de sesión y rol `ADMINISTRADOR`. No devuelve contenidos completos ni escribe líneas.
- No se debe agregar `POST` de ejecución hasta implementar registro durable, comprobaciones RBAC propias, protección CSRF según política existente, límites operativos y pruebas.
- `SUPERADMIN`, `RESPONSABLE`, `USUARIO`, `GESTOR` y demás roles no están habilitados para la vista previa.

## Entidades de trabajo propuestas (requieren migración y revisión)
- `trabajo_id` (UUID), `tenant_id`, `solicitado_por_cuenta_id`, fecha de solicitud.
- Parámetros validados: período, empresa, UUID de expediente, formato/tipo, límite por página.
- `estado`: pendiente, ejecutando, pausado, completado, fallido; `cursor_documento_id` para checkpoint.
- Contadores: documentos revisados, XML válidos, líneas nuevas, repetidas, rechazadas y errores; última actualización.
- Registro inmutable de eventos: `trabajo_id`, actor, transición de estado, documento afectado, resultado y marca temporal; sin almacenar XML completo ni datos sensibles innecesarios.
- `idempotency_key` única por tenant y solicitud de usuario; índices/constraints de unicidad para líneas y catálogo.

## Reglas de ejecución
1. Vista previa únicamente permite estimar alcance; nunca guarda productos ni altera documentos originales.
2. El trabajo debe poseer autorización comprobada en el momento de crearlo y antes de procesar; nunca aceptar un `tenant_id` arbitrario del cliente.
3. Aislar escrituras por tenant y utilizar transacciones/savepoints por documento; persistir checkpoint y eventos **atómicamente** con los cambios de cada lote.
4. Tras reinicio, continuar desde último checkpoint confirmado; reintentos no generan líneas duplicadas.
5. Exponer progreso al actor autorizado y permitir cancelación supervisada; no borrar evidencias.
6. Previo a producción: migración reversible, pruebas con PostgreSQL real y aislamiento de tenants, respaldo y restauración aislada, autorización de integración y despliegue.

Este documento no autoriza ejecución automática ni implica que exista auditoría persistente todavía.
