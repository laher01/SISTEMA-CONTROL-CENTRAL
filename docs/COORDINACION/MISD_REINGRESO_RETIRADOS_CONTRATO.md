# MISD 3-2.23 — Recarga de documentos retirados (hallazgo y contrato de corrección)

**Rama aislada:** `test/misd-reingreso-retirados-20261024`, creada desde PR #390 SHA `501290199ef1128d72d23401776b65aa7ea25b20`.
**Estado:** diagnóstico del defecto completado; **no habilitar purga física ni cambiar unicidad sin migración y pruebas integrales**.

## Problema reproducible por inspección

- `backend/app/services/ingesta.py::ingerir_documento` consulta por `Documento.tenant_id` + `Documento.sha256` **sin** filtrar `deleted_at`, y eleva `DocumentoDuplicado` aunque el registro esté retirado.
- `backend/app/models.py::Documento` declara `UniqueConstraint("tenant_id","sha256")` y `UniqueConstraint("tenant_id","huella_comercial")`: filtrar la consulta sin revisar estas restricciones produciría una colisión en INSERT.
- `backend/app/storage.py::AlmacenLocal.guardar` almacena por tenant/SHA; el archivo existente no equivale necesariamente a documento activo.
- `backend/app/api/routes/documentos.py`: DELETE lógico mantiene el original y el endpoint POST `/{documento_id}/restaurar` requiere permiso, expediente activo, existencia y hash del original y ausencia de colisión activa.
- `backend/app/api/routes/mantenimiento.py::_intentar_eliminar_archivo` bloquea eliminación física si **cualquier** Documento aún referencia la ruta, incluso retirado; esto protege originales restaurables.
- El diseño `docs/IMPLEMENTACION_ELIMINACION_DOCUMENTAL_INTEGRAL.md` plantea purga física tras commit en cola durable e idempotente, pero **no certifica** que esté desarrollada.

## Contrato de comportamiento requerido

1. **Activo con mismo SHA o huella fiscal:** no duplicar; respuesta clara y permiso/ámbito respetados.
2. **Retirado lógico:** ofrecer restauración del mismo documento, o reingreso de nueva identidad **solo tras** revisión de dependencia fiscal, permiso, auditoría, expediente y colisión. Nunca restauración automática con permisos más débiles que el endpoint explícito.
3. **Archivo físico existente sin referencia activa:** reutilización de bytes con verificación SHA y propiedad de tenant; el objeto físico no debe impedir por sí mismo el reingreso.
4. **Purgado legítimamente:** nuevo ingreso sin resucitar identificadores, conservando auditoría histórica mínima y registros fiscales legalmente protegidos.
5. **Fiscalmente protegido o relacionado con GRE, pagos, voucher, liquidación o auditoría:** impedir purga destructiva; reutilización/restauración autorizada donde proceda.
6. **Concurrencia:** transacción PostgreSQL + bloqueo de ámbito, restricciones de unicidad por estado activo **solo tras analizar migración Alembic**, para que dos cargas o carga/restauración simultáneas no produzcan doble factura.
7. **Storage:** nunca `unlink` si persiste referencia física, incluso de un documento retirado restaurable; borrar solo mediante cola postcommit, pruebas de idempotencia y conservación fiscal.

## Pruebas de aceptación pendientes

- Documento SHA A activo, retiro y segundo upload A; retorno autorizado, sin error de fichero existente y sin duplicado activo.
- Upload A de otro tenant; aislamiento de rutas/identidad y prohibición de restaurar registro ajeno.
- Restauración con SHA alterado, archivo ausente, expediente retirado y usuario sin permiso: denegación.
- Documento activo con mismo SHA/factura: duplicado bloqueado; dos uploads concurrentes: un único activo.
- Retirado con pago/voucher, GRE u obligación fiscal: nunca purga física; preservación de evidencia.
- Purga de material **sintético y jurídicamente elegible**, sin referencias, cola durable; re-upload permitido; verificación de auditoría e integridad FK.
- Alembic `upgrade`, `downgrade` solo con datos sintéticos, `compare_metadata` y CI backend/frontend/OCR/roles.

**No aplicar una solución superficial eliminando un registro o quitando el UNIQUE.** Resolver con una migración y lógica de negocio revisadas conjuntamente con propietarios MISD/OCR y conservación fiscal. Ningún cambio de código productivo realizado en esta nota.
