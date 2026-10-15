# FACT CENTRAL — Eliminación documental integral por roles

Estado: diseño de implementación; **no habilitar borrado físico antes de superar pruebas**.
Base: PR #184, rama `fix/coherent-document-expediente-deletion-20261014`.

## Objetivo

La eliminación de documento o expediente debe reflejarse en gestores, registros, expedientes, pendientes, dashboard y montos, sin destruir identidades, empresas, usuarios, contraseñas, roles, proveedores ni credenciales de Google OAuth.

## Operaciones distintas

- **Retirar (restaurable)**: soft delete con `deleted_at`, exclusión consistente de vistas, actualización de importes y vínculo fiscal, trazabilidad y posibilidad de restaurar.
- **Eliminar definitivamente**: confirmación diferenciada y permiso elevado; borrar entidades documentales y derivados OCR; preservar evidencia mínima de auditoría sin datos sensibles; procesamiento físico mediante cola durable idempotente después del commit.
- **Reiniciar documentos de prueba**: acción separada de mantenimiento para Administración con previsualización por tenant, número de filas, total de bytes, confirmación explícita y resultado verificable; sin tocar tablas identitarias ni Google OAuth.

## Seguridad y alcance

Evaluar explícitamente permisos para ADMINISTRADOR, GERENTE, SECRETARIA, RESPONSABLE, USUARIO y GESTOR con alcance por tenant, jerarquía, asignación y propiedad. No interpretar rol como permiso universal. SUPERADMIN de plataforma no debe poder borrar datos operativos por defecto.

## Integridad

1. Misma transacción para marcar expediente y documentos, desvincular referencias y registrar auditoría.
2. Un documento retirado individualmente no implica borrar el expediente si contiene otra evidencia. Recalcular exclusivamente desde documentos activos.
3. En eliminación definitiva comprobar `pagos_erp.voucher_documento_id`, `referencias_gre`, `relaciones_documentos`, `correcciones_ia`, alertas y alertas manuales. No borrar pagos ni datos maestros accidentalmente.
4. La huella SHA-256 de bytes y la identidad fiscal deben aplicarse sobre documentos activos; al restaurar verificar colisiones e identidad de expediente.
5. El cache OCR bajo `_ocr_cache` se retira solamente para documentos afectados, no cache global de otros tenants.
6. No borrar físicamente antes del commit. Cola `eliminaciones_archivos_pendientes` con reintentos, errores auditables, idempotencia y comprobación de referencias; archivo compartido solo se borra cuando no tenga referencias activas.
7. Reconciliación programada: contar documentos activos, huérfanos físicos, pendientes de eliminación, fallos de almacenamiento, índices/contadores desfasados. Nunca efectuar borrado masivo automático sin alcance validado.

## Pruebas obligatorias

- Borrar documento activo, ya eliminado, con pago, con relación GRE y con expediente.
- Borrar expediente completo; mantener usuarios, empresas, contraseñas, roles y OAuth.
- Permisos permitidos/denegados por cada rol y tenant.
- Falla física después de commit: pendiente recuperable; sin falsas confirmaciones de eliminación física.
- Carrera entre re-subida, deduplicación fiscal y eliminación/restauración.
- Dashboard y listados de todos los roles: totales consistentes inmediatamente después de operación.
- Limpieza de prueba en copia aislada: 0 documentos/expedientes/relaciones, 0 archivos pendientes, inventario de cuentas/empresas/OAuth sin variaciones.
- CI verde y validación de despliegue solo en VPS `132.145.233.172`, Oracle excluido.

## Hallazgos de código existente

- `backend/app/api/routes/documentos.py`: DELETE marca `deleted_at`, llama `actualizar_expediente` y hace commit, sin retirar físicamente archivo.
- `backend/app/api/routes/expedientes.py` en `main`: DELETE marca `deleted_at`; PR #184 propone sincronizar documentos.
- `backend/app/api/routes/mantenimiento.py`: limpieza selectiva por cuenta/fecha/tipos; vincula archivos a una cola y los intenta retirar; requiere reforzar relaciones y límites de tenant.
- `frontend/src/paginas/Configuracion.tsx`: panel mantenimiento limitado a Administrador del tenant.

Este documento define criterios de aceptación; no indica que estén implementados.


## Nueva regla: empresa emisora asignada a gestor (14/10/2026)

Al cargar FACT, GRE, voucher u otro documento con emisor identificable, validar RUC emisor y titularidad de grupo **antes de su contabilización y publicación**. La propiedad se determina por la asociación empresarial vigente, no por el mero conocimiento del RUC ni por nombre de archivo. Revisar los modelos de asignación actuales antes de migrar.

- Si el emisor pertenece al ámbito permitido del usuario autenticado, continuar con validaciones documentales usuales.
- Si pertenece a otro gestor/responsable del mismo tenant, aislar en cuarentena temporal (sin expediente, importes ni contadores), notificar a Administración, al responsable propietario y a los usuarios habilitados del gestor correspondiente, con información del solicitante, RUC, gestor y responsable propietarios y referencia de la solicitud.
- El responsable habilitado o Administrador del tenant podrán aprobar o rechazar **una solicitud concreta** según RBAC, ámbito y conflicto de intereses. No equivale a transferir empresa ni a autorización general.
- Si se rechaza, borrar carga temporal y derivados; conservar metadatos mínimos de solicitud, decisión y auditoría sin exponer contenido del documento.
- Si el emisor no está registrado, si hay múltiples titulares, OCR poco confiable o discrepancias, pasar a revisión sin asignación automática ni contabilización.
- Proteger contra cargas simultáneas y sustitución del archivo aprobado (huella SHA-256), acceso entre tenants, acceso por rutas de descarga, duplicación semántica de facturas y notificaciones duplicadas.
- Si el documento es un voucher sin RUC emisor verificable, aplicar su propia regla documental sin atribuir titularidad a partir del importe.

Pruebas: emisor propio/ajeno, empresa sin asignación, usuario de otro tenant, aprobado/rechazado, recarga simultánea, OCR incompleto, mensajes por destinatario, y Dashboard sin montos de solicitudes pendientes/rechazadas.
