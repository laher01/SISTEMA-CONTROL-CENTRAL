# Gate S — Contrato de ciclo de vida documental e integración (#286/#292/#186/#281)

Fecha: 2026-10-18. Fuente: parches GitHub de los HEAD indicados; **propuesta técnica, NO código integrado ni comportamiento aprobado**. Sin cambios en ramas funcionales, main, VPS o DB. Gate S **OPEN**.

## Evidencia, versiones examinadas
- #286 `ca6281bb5d4295cb79274771cb85b7bc4ef2fbc7` (base main): reemplaza DELETE documento y DELETE expediente con lógica de eliminación integral, chequeo de referencias, bloqueo de fila `Tenant FOR UPDATE`, diario de movimiento físico, sincronización y recuperación tras fallo; cambia las sumas para excluir `pendiente_aprobacion`.
- #292 `a7ccf3aa8061c4080af1574c860e116ef9fdb2cd` (base main): añade `GET /capacidades`, previsualización y retirada por lote, `GET /retirados`, `POST /{id}/restaurar`; conserva `DELETE` lógico y autorización `PERMISO_ELIMINAR_REGISTROS` excepto SUPERADMIN; evita restaurar sin archivo original y con colisión de huella.
- Archivos de conflicto directo: `backend/app/api/routes/documentos.py`, `expedientes.py`, `backend/tests/test_api.py`.
- #186 `9aac21d2a1dae1c5fe2acc7159cc5547ff816515`: aporta `contabilidad_items_ubl.py`, `ingesta.py`, API `contabilidad_items.py`, migración `0035` (`down_revision='0034'`), líneas únicas `(tenant_id, documento_id, numero_linea)`.
- #281 `fac5831e3f86e985ff0bcdf31b874a6ac43b1ea4`: modifica `contabilidad_items_ubl.py` con `SELECT Tenant FOR UPDATE` y validación documento activo/tenant antes de registrar; comparte test persistencia con #186.
- #102: migración `0024` (`down_revision='0023'`). #289: migración `0041` (`down_revision='0040'`).
- Rutas de los archivos exactos de migraciones `0024`, `0035`, `0041` no se encontraron en `main` mediante fetch_file (404) al consultar. **Esto no demuestra ausencia de las revisiones con otros nombres**: se debe consultar el grafo real Alembic de main y de una rama de integración para detectar revisiones duplicadas y cabezas divergentes.

## Hallazgo prioritario — contrato de eliminación
**Incompatibilidad semántica reproducible desde los parches**:
- En #292, `retirar_documentos_lote` invoca `eliminar_documento(session, settings, hoy, tenant_id, auth, documento_id)`, que efectúa retirada lógica.
- En #286, `eliminar_documento` requiere argumento adicional `almacen`, aplica eliminación definitiva a documentos sin expediente y una ruta integral específica para documentos asociados.
- Por tanto, portar #286 sin adaptar #292 puede romper la firma de la llamada del lote; además cambia un efecto recuperable a definitivo. El endpoint `GET /capacidades` de #292 devuelve `puede_eliminar_definitivamente: false`, inconsistente con rutas de eliminación irreversible de #286 en ciertas condiciones.
- En #286, expedientes requieren `GESTOR` propietario; en #292 se ajusta prohibición explícita a SUPERADMIN y conserva lógica de alcance/permisos anterior. No permitir que la interfaz prometa un permiso distinto del backend.

## Contrato común propuesto para revisión de los responsables (NO IMPLEMENTAR AQUÍ)
**Máquina de estados recomendada:** `ACTIVO → RETIRADO_RECUPERABLE → RESTAURADO`; `ACTIVO/RETIRADO → ELIMINACION_DEFINITIVA_PENDIENTE → ELIMINADO_DEFINITIVO` **solo con autorización explícita y controles adicionales**. Estados técnicos persistidos/journal deben respetar los campos y tablas vigentes; la nomenclatura es conceptual, no migración aprobada.

1. **Retirar**: operación explícita `retirar` (no `DELETE` ambiguo); preservar DB, archivos y evidencias de auditoría, ocultar de listados y sumas activas, mantener referencias históricas.
2. **Restaurar**: verificar tenant, ámbito de actor, original y SHA, inexistencia de equivalentes activos, relación con expediente vivo y consistencia de líneas/importes; rollback transaccional si hay colisión.
3. **Eliminar definitivamente**: ruta/capacidad separada de la retirada, previsualización de dependencias, denegar vínculos externos, pagos, GRE, líneas/decisiones de auditoría o expedientes ajenos sin tratamiento validado. No borrar comprobantes fiscales cuya eliminación local pueda perder trazabilidad obligatoria; registrar estado de documentos emitidos/aceptados por SUNAT, que no se anulan por borrar una copia en la aplicación.
4. **Expediente**: sin borrado parcial silencioso de FACT/GRE/VCHR; rechazo atómico ante dependencia externa o procedimiento explícito de baja de conjunto; documentar qué documentos quedan históricos.
5. **Concurrencia**: serialización por tenant en altas, retiradas, restauraciones, eliminación y reingesta; lock adquirido antes de comprobar hash y referencias; solo tras COMMIT liberar huellas y permitir alta; recuperar archivo físico/journal ante error.
6. **Contabilidad**: no hacer sumas de datos retirados, definitivos o pendientes de aprobación; línea UBL única por tenant/documento/número y suma única por operación; posterior restauración no multiplica líneas; registrar reversión de estados auditable.
7. **RBAC**: decisiones de autorización por acción `retirar`, `restaurar`, `eliminar definitivamente` y ámbito del documento; la API de capacidades debe reflejar la misma decisión usada por los endpoints. SUPERADMIN no adquiere permiso implícito.
8. **NEXUS/OCR**: casos OCR, relaciones y cambios de estado no deben revivir borrados ni reconstruir expedientes ajenos; comprobar referencias antes de cambios irreversibles.

**Propietarios sugeridos:** #286 implementa atomicidad/borrado/reingesta; #292 implementa retirada/papelera/restauración/capacidades. Coordinación Gate S únicamente define contrato, tests de cruce y evidencia; no edita sus ramas.

## Plan de prueba antes de cualquier integración
| Escenario | Resultado exigible |
|---|---|
| Retirar por lote documento activo | Sigue existiendo y es restaurable; no se elimina el original |
| Restaurar tras retirada | Un solo documento vigente; hash verificado; importe correcto |
| Lote con documento fuera de tenant | Nunca revela metadatos ni cambia registros |
| Eliminar FACT con GRE o voucher vinculados | Rechazar con dependencia explícita; no dejar referencias huérfanas |
| Reingestar el mismo PDF autorizado tras eliminación definitiva | Una operación registrada; sin registro fantasma ni doble importe |
| Concurrencia retirar/reingestar mismo SHA | Serializa o rechaza de forma consistente, sin contenido perdido |
| Fallo intermedio entre movimiento físico y COMMIT | Recuperación idempotente y original restaurado o journal coherente |
| Documento pendiente aprobación | Excluido de montos consolidados sin perder trazabilidad |
| Otro tenant/rol o SUPERADMIN no autorizado | Denegación con ámbito correcto |
| Contabilidad #186 + UBL #281 | Un solo catálogo y una línea por número de item en reproceso concurrente |
| Alembic 0024/0035/0041 | Grafo lineal o ramificación controlada, `heads` esperado, esquema coherente tras upgrade/rollback sintéticos |
| NEXUS OCR #289 | Casos sin references colgantes ni lectura de documento retirado de otro tenant |

## Bloqueantes antes de escribir código de integración
1. Obtener decisión funcional del dueño de #286 y del dueño de #292 sobre semántica final del botón eliminar y compatibilidad de rutas.
2. Hacer ensayo de combinación solo en rama temporal aislada, nunca en main: comparar firmas API, actualizar tests del lote, comprobar permisos y archivo original.
3. Comprobar `alembic history`, `alembic heads` y `upgrade head` en base de datos desechable con árbol candidato; no ejecutar sobre VPS.
4. Ejecutar test end-to-end sintético FACT→GRE→VCHR→líneas→retirada/restauración→reingesta y confrontar montos exactos.
5. Revisar CI del HEAD concreto y aprobar manualmente Gate S previo a despliegue.

**Este documento no supone que otros chats estén ejecutándose simultáneamente.** Su actividad se acredita solo por nuevas evidencias de cambios/CI.
