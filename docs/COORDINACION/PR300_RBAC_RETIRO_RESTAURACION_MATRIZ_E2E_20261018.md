# Gate S — Especificación contractual RBAC y pruebas transaccionales sintéticas

Fecha 18/10/2026. **Solo especificación — no constituye integración ni aprobación del comportamiento.**
Fuentes HEAD: #286 `ca6281bb5d4295cb79274771cb85b7bc4ef2fbc7`, #292 `61a3a18aa071a2fb1a638ccf2285d3451db1eeba`, #186 `9aac21d2a1dae1c5fe2acc7159cc5547ff816515`, #281 `fac5831e3f86e985ff0bcdf31b874a6ac43b1ea4`.

## Evidencia de permisos y contrato actual
- #292 `GET /capacidades`: `puede_retirar` y `puede_restaurar` se basan en `PERMISO_ELIMINAR_REGISTROS` y exclusión de `SUPERADMIN`; `puede_eliminar_definitivamente=False`. Previsualización, lote y restauración reutilizan comprobaciones de ámbito/permisos.
- #286 `DELETE /documentos/{id}`: aplica bloqueo documental por tenant y, para documentos sin expediente, comprueba propiedad y referencias, mueve original y borra el registro; para asociados restringe al gestor propietario. `DELETE /expedientes/{id}` se restringe a gestor propietario.
- #292 `retirar_documentos_lote` llama `eliminar_documento(session, settings, hoy, tenant_id, auth, documento_id)`; #286 requiere `almacen` además de esos argumentos. Las firmas y **efectos** no son equivalentes.
- Contrato recomendado: rutas distintas para RETIRAR (recuperable), RESTAURAR y ELIMINAR_DEFINITIVAMENTE (irreversible con proceso expreso); no cambiar semántica de un endpoint existente sin revisar API/UI/roles; cada `/capacidades` responde por acción y recurso.

## Matriz de aceptación
| Caso | Actor / estado | Acción | Resultado requerido |
|---|---|---|---|
| A01 | Gestor dueño, factura activa, sin vínculos | Retirar | `deleted_at` lógico, archivo original conservado, auditoría, no sumas activas |
| A02 | Gestor ajeno o tenant B | Retirar/restaurar/eliminar | 403/404 sin revelar existencia ni alterar A |
| A03 | SUPERADMIN sin capacidad operativa | Las tres operaciones | 403, capacidades coherentes, sin efectos |
| A04 | Responsable autorizado dentro de alcance | Retirar/restaurar | Según permiso de la acción, validación individual; nunca baja definitiva implícita |
| A05 | Documento retirado, mismo original/hash válido | Restaurar | Mismo ID, una sola línea contabilizada por identificador, sumas restauradas una sola vez |
| A06 | Documento retirado, hash alterado o original ausente | Restaurar | 409 y DB sin alteración |
| A07 | Documento con GRE, voucher o pago relacionado | Eliminar definitivamente | 409 si dependencias no resueltas; cero huérfanos |
| A08 | Lote mezclado con IDs repetidos / ajenos / activos | Previsualizar y retirar | Sin duplicar efectos, no filtrar datos del tenant ajeno; resultados auditables |
| A09 | Eliminar caso permitido sin referencias externas | Eliminación definitiva | Diario FS + transacción SQL coordinados, sin archivo huérfano |
| A10 | Retirada simultánea con reingesta mismo hash | Concurrencia 2 sesiones PostgreSQL | Orden serializado o conflicto seguro; sin documento fantasma |
| A11 | Fallo tras mover archivo antes de commit | Recuperación | Reconciliación idempotente, hash e índice consistentes |
| A12 | Expediente FACT/GRE/VCHR con líneas UBL | Retirar y restaurar | Resumen PEN/USD no suma guías/vouchers como ventas ni duplica líneas |
| A13 | Documento pendiente aprobación | Consultar resúmenes | No sumar importe no aprobado; conservar trazabilidad |
| A14 | Dos tenants y reescaneo UBL concurrente | Reingesta y reporte | Catálogo separado; `(tenant,documento,numero_linea)` único |
| A15 | Control de roles en UI versus API | Consultar `/capacidades` y ejecutar acción | Respuestas congruentes con RBAC efectivo |

## Secuencia de fixtures y aserciones SQL
1. En DB PostgreSQL efímera con schema obtenido del árbol candidato y archivos temporales, crear tenants A y B; sesiones reales por rol, sin credenciales reales.
2. Crear factura UBL A con dos líneas: verificar `count(lineas)=2`; `SUM(importe_linea)` corresponde a líneas de la factura, no se infiere que sea automáticamente igual al importe fiscal en todos los casos.
3. Adjuntar GRE y VCHR sintéticos al expediente y un pago ficticio vinculado; contar referencias antes/después de la operación. No permitir eliminación definitiva mientras existan referencias.
4. Ejecutar retirada recuperable, `COMMIT`, nueva sesión y consultar APIs y SQL: ID persiste, sumas activas no incluyen retirados, archivo/sha intactos.
5. Restaurar y repetir consulta tras `COMMIT` nuevo: una factura activa, líneas idempotentes, ninguna referencia recuperada dos veces.
6. Dos transacciones independientes con barrera de concurrencia para retirada/reingesta y comprobación final tras `ROLLBACK` de fallo inyectado.
7. Verificar el último estado mediante reinicio de sesión y comprobar diario FS; no equiparar rollback de DB con restauración automática de archivos.
8. Ejecutar validación Alembic 0024/0035/0041 en DB descartable: revisión/id únicos, `heads` esperado, FK e índices; NO VPS.
9. Repetir A02/A03 con distintos actores y tenants: ninguna filtración y ningún cambio persistido.
10. Conservar logs y SHA de cada rama combinada; la ejecución es **pendiente**, no realizada.

## Gate de integración
- Dueños funcionales de #286 y #292 deben acordar contrato y cambios en sus propios frentes.
- Este chat puede incorporar pruebas de compatibilidad solamente en rama de pruebas.
- CI verde sobre la rama actual solo certifica las pruebas aisladas, no el ensayo combinado.
- No fusionar PRs encadenados ni modificar main. Gate S OPEN.
