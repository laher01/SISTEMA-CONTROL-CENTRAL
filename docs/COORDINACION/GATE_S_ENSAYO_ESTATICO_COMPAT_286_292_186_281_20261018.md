# Gate S — Ensayo estático de compatibilidad (18/10/2026)

## Evidencia fuente
- #298 HEAD `ea2391093633d6e9c640c53a92bef3c11a2810e9`: coordination-guardrails SUCCESS.
- #286 HEAD `ca6281bb5d4295cb79274771cb85b7bc4ef2fbc7`.
- #292 HEAD actualizado `61a3a18aa071a2fb1a638ccf2285d3451db1eeba` (diferente del auditado inicialmente).
- #186 HEAD `9aac21d2a1dae1c5fe2acc7159cc5547ff816515`.
- #281 HEAD `fac5831e3f86e985ff0bcdf31b874a6ac43b1ea4`.

## Herramienta incluida
`scripts/gate_s_contract_dryrun.py` inspecciona objetos git con `git show` sin checkout ni merge. Compara firma de `eliminar_documento` en #286 con llamadas desde `retirar_documentos_lote` de #292; identifica existencia de capacidades/restauración, bloqueo en #281 y metadatos de revisiones de migración con referencias explícitas. Emite JSON. Un resultado de firmas compatibles **no equivale a validación runtime**.
`backend/tests/test_gate_s_contract_dryrun.py` incorpora 3 pruebas sintéticas del analizador.

Ejecución propuesta **solamente en checkout local aislado con objetos ya descargados**:

```bash
python3 scripts/gate_s_contract_dryrun.py \
  --delete-ref ca6281bb5d4295cb79274771cb85b7bc4ef2fbc7 \
  --trash-ref 61a3a18aa071a2fb1a638ccf2285d3451db1eeba \
  --items-ref 9aac21d2a1dae1c5fe2acc7159cc5547ff816515 \
  --rescan-ref fac5831e3f86e985ff0bcdf31b874a6ac43b1ea4 \
  --migration-0024-ref 9aceb5e9ae4859cb14bd1509f1ef0d56c93c8b35 \
  --migration-0041-ref 5d3849044063f6aca338505a121f0bc1e96bb961
```

No ejecutado en VPS ni se han obtenido resultados de un repositorio clonado. Confirmación mediante inspección de parches: #292 continúa llamando a `eliminar_documento(session, settings, hoy, tenant_id, auth, documento_id)`; #286 añade argumento `almacen` y modifica la semántica de borrado: **incompatibilidad prevista, no prueba de fallo runtime combinado**.

## Condiciones de aceptación del ensayo de integración
1. Dueños #286 y #292 acuerdan separar retirar recuperable de eliminación definitiva y una interfaz estable; capacidad RBAC corresponde al efecto real.
2. Mantener validez tenant, scope y no habilitar por defecto SUPERADMIN.
3. Conservar archivos, huellas y relaciones de FACT/GRE/VCHR en retirada; eliminación definitiva rechaza dependencias no resueltas y respeta trazabilidad fiscal.
4. Una restauración comprueba hash, existencia física y conflictos de identidad; las sumas no se duplican.
5. Simulación aislada dos tenants, sesión doble y fallo entre filesystem y commit; no basta un test de firma.
6. Validar grafo Alembic real: #102 0024→0023, #186 0035→0034, #289 0041→0040. Las rutas exactas no están en main; no afirmar que las revisiones estén ausentes con nombres diferentes.
7. No mover código de otro frente desde este PR.

## Estado
**PREPARADO, PENDIENTE CI Y EJECUCIÓN DEL COMPROBADOR CONTRA GIT LOCAL.** Solo script de lectura, pruebas sintéticas y documentación. Gate S OPEN. Sin merge, main, VPS, migraciones o despliegue.
