# PR264 — URGENTE+ verificación de inventarios tenant y contratos OCR/NEXUS

Fecha 2026-10-17; exclusivamente pruebas sintéticas de seguridad y coordinación.

## CI de referencia
Commit `a57c430dfd247419c6b0839fb15b6c50899291f4`: 4/6 SUCCESS al iniciar, `roles-real-integration` y `recepcion-documental-ci` todavía IN_PROGRESS. No declarar verde el commit hasta seis resultados.

## Pruebas añadidas
- `test_pair_manifest_rejects_second_tenant_even_with_same_payload`: un archivo adicional `tenant-b/doc.pdf` no incluido en el manifiesto firmado hace fallar la auditoría, incluso con mismo payload que `tenant-a/doc.pdf`.
- `test_same_document_name_allowed_when_tenant_paths_are_distinct`: los archivos de rutas tenant A/B no colapsan por compartir nombre ni SHA; inventario independiente.

Son pruebas de hash/inventario de TAR, **no** pruebas reales del API de OCR ni del aislamiento RBAC de PostgreSQL. No generan eventos NEXUS, escrituras fiscales o vínculos de expediente.

## Siguiente contrato de integración
En una rama OCR/NEXUS independiente basada en main: cubrir `storage.file.available` e idempotencia de eventos versionados, duplicados fiscales normalizados con separación de tenant, `CONFLICT_REVIEW`, clasificación y revisión humana, relaciones GRE/OC/voucher, RBAC de dos usuarios con permisos distintos y comprobación de ninguna operación económica duplicada. La matriz de casos está en `PR264_OCR_NEXUS_CONTRACT_TEST_MATRIX_20261017.md`.

Los 14 archivos de PR #275 se comprobaron idénticos en blob SHA a main: no volver a fusionar ni copiar.

## Bloqueos
S abierta por restauración pareada real de BD+documentos en staging verdaderamente aislado con aprobación independiente y limpieza verificable. I y D bloqueados. PR264 draft, sin VPS, merge ni despliegue.
