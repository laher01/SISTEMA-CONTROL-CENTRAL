# Eliminación documental integral — auditoría de permisos e integración (18/10/2026)

Estado: **Fase 1 auditada; backend/frontend pendiente de implementación y pruebas. NO APTO PARA DESPLIEGUE.**
Base revisada: `main` commit `1d75eb39997dc7d6964ae339a13af029cef90b54`.
Rama de trabajo: `feat/document-retention-role-actions-20261018`.
Antecedentes: PR #184/#185; `docs/IMPLEMENTACION_ELIMINACION_DOCUMENTAL_INTEGRAL.md`. OCR/OSE/PSE, PR #289/#291: **fuera de alcance**.

## Hallazgos reales de código

- `backend/app/enums.py`: seis roles `RolMiembro`: SUPERADMIN, ADMINISTRADOR, GERENTE, SECRETARIA, RESPONSABLE, USUARIO. GESTOR se crea mediante `cuentas_acceso.gestor_id` en `backend/app/security.py`; **no** es miembro `RolMiembro`.
- `backend/app/models.py`: `Miembro.responsable_id`, `Gestor.usuario_id`, `CuentaAcceso.miembro_id/gestor_id`. Por tanto, alcance operativo RESPONSABLE → USUARIO → GESTOR, **no** permisos por simple jerarquía numérica. El rol GERENTE y SECRETARIA son funciones diferentes, no ramas equivalentes de autorización documental.
- `backend/app/api/routes/auth.py`: `/auth/me` reconstruye cadena real por `responsable_id`; `frontend/src/App.tsx` define módulos visibles por rol; SUPERADMIN usa exclusivamente consola SaaS, no módulos operativos.
- `backend/app/services/permisos.py`: `ELIMINAR_REGISTROS` habilitado por defecto para SUPERADMIN, ADMINISTRADOR y GESTOR; otros roles dependen de `PermisoConfigurado`. **Riesgo**: SUPERADMIN puede superar esta verificación aunque su menú esté segregado; una futura API de eliminación definitiva debe denegarlo en backend por defecto.
- `backend/app/api/routes/documentos.py`: `DELETE /{documento_id}` aplica `_validar_ambito_documento`, verifica `ELIMINAR_REGISTROS`, establece `deleted_at`, audita y recalcula expediente. No elimina bytes.
- `frontend/src/paginas/Documentos.tsx`: eliminación individual y lote por secuencia de DELETEs; confirma que originales no se borran; `Pendientes.tsx` ya ofrece Eliminar individual y Reprocesar. **No duplicar esas acciones**.
- `backend/app/api/routes/expedientes.py`, `registros.py` y `mantenimiento.py`: requieren integración por entidad, no borrado ciego en cascada.

## Matriz efectiva observada (no inventar privilegios)

| Actor | Acceso visible según App.tsx | ELIMINAR_REGISTROS backend | Borrado físico nuevo |
|---|---|---|---|
| SUPERADMIN | Consola SaaS exclusivamente | Activado por código (deuda de seguridad) | Denegado por defecto |
| ADMINISTRADOR | Documentos, Pendientes, Registros, Expedientes, Configuración | Activado por código | Permiso específico nuevo + alcance/validaciones |
| GERENTE | Registros, Expedientes, gestión comercial | Sólo cuando `PermisoConfigurado` lo habilite | No implícito |
| SECRETARIA | Documentos, Pendientes, Registros, Control documental, según activaciones | Sólo cuando se configure | No implícito |
| RESPONSABLE | Gestión de equipo, usuarios, comisiones/cobros | Sólo cuando se configure | No implícito |
| USUARIO | Documentos, Pendientes, Registros, Expedientes, Subir | Sólo cuando se configure | No implícito |
| GESTOR | Documentos, Pendientes, Registros, Expedientes, Subir | Activado por código, limitado por ámbito | No implícito |

La tabla expresa reglas observables del código, **no** configuraciones activas de PostgreSQL en producción. Validar registros `PermisoConfigurado` y build desplegado antes del rollout.

## Contratos de integración que deben respetarse

1. No cambiar semántica de `DELETE /api/v1/documentos/{id}`: sigue siendo **retirada lógica** compatible.
2. Añadir API de **capabilities efectivas** por registro/acción, calculadas por backend con tenant, propietario, delegaciones y estado. No equiparar visibilidad de menú con permiso efectivo.
3. Implementar servicio central de operaciones para Documentos, Pendientes, Registros y Expedientes, manteniendo ámbitos específicos.
4. Restauración: rechazar colisión por hash/identidad fiscal, restaurar sólo si archivo y referencias son coherentes, auditar y recalcular expediente.
5. Borrado definitivo: permiso independiente `ELIMINAR_DOCUMENTOS_DEFINITIVAMENTE` **denegado por defecto**, vista previa con checksum/versionado, protección de pagos/GRE/vínculos/alertas, aprobación explícita, auditoría de mínimos.
6. Archivo físico: cola durable después de commit, operaciones idempotentes y revalidación de refs; prohibido borrar antes de cerrar transacción. No limpiar OCR cache global.
7. Lote: prevalidar todos los UUID con ámbito individual, límites de cantidad, resultados por ítem, idempotencia/reintento y confirmación diferenciada.
8. Fantasmas: diagnóstico de sólo lectura y reparación supervisada, nunca barrido automático de documentos fiscales o archivos sin verificación.
9. Índices de deduplicación: cambios vía migración Alembic con prueba de colisiones en restore y rollback, no por SQL manual.
10. Fuera de alcance: cambios OCR/NEXUS o manejo de representación OSE/PSE.

## Gate técnico mínimo antes de PR listo para revisión

- Inspeccionar `_validar_ambito_documento`, middleware/deps de rutas y permisos reales de `registros` y `expedientes`.
- Diseñar esquema de cola y migración Alembic sin solapamiento con las migraciones 0040/0041 de ramas paralelas.
- Pruebas RBAC 7 roles, otros tenants, gestores ajenos, expedientes/pagos/GRE, falla post-commit, upload concurrente, índices de duplicado, lote mixto.
- Probar upgrade/downgrade y restauración de copia de respaldo aislada, lint/build/E2E y CI verde.
- Revisar diferencias GitHub `main` vs VPS, respaldos y despliegue sin tocar producción. Hasta entonces **NO LISTO PARA DESPLEGAR**.

## Entrega de esta iteración

Auditoría inicial registrada para evitar invasión de OCR y prevenir diseño basado en permisos imaginados. **No hay cambios en endpoints, esquemas ni producción, y no se han ejecutado pruebas**.
