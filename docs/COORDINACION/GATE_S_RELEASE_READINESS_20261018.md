# Gate S — preparación verificable de liberación (18/10/2026)

Estado: **NO AUTORIZADO PARA DESPLIEGUE**. Documento de coordinación creado en rama aislada; no habilita merge, acceso VPS ni ejecución productiva.

## Punto de partida
- PR #264: DRAFT, base `integration/208-main-review-20261017`, HEAD auditado `4c0fc3259f73ded1ce307901e43908ee0b86ff4c`.
- 7 workflows PASS para ese HEAD: `backend`, `roles-real-integration`, `recepcion-documental-ci`, `coordination-guardrails`, `security-paired-restore-dry-run`, `security-synthetic-postgres-restore-ci`, `security-fiscal-concurrency-pr264`.
- PostgreSQL real: `backend/tests/test_facturas_concurrencia_postgresql_pr264.py` disputa una identidad de `Expediente` con dos sesiones, misma empresa/emisor/receptor/serie/número y confirma 1 alta y 1 `IntegrityError` (run 39101196039).
- CI restauración sintética: PG16 y PG17 restauran DB/archivos de prueba, prueban roundtrip Alembic 0039 y limpieza ante fallo (run 39101196053).
- Auditor archivo local (run 39101196049): sin SSH, sin VPS; no acredita recuperación productiva.

## Criterios comprobables pendientes antes de autorizar
- [ ] Entorno staging **aislado** aprobado por operador autorizado, secretos distintos y sin conexión escribible a producción.
- [ ] Respaldo pareado DB+documentos del mismo corte/lote, manifiesto SHA256 y evidencia de correspondencia, **sin copiar datos personales a entornos inseguros**.
- [ ] Restaurar respaldo pareado autorizado; verificar totales, relaciones factura/GRE/voucher/items y archivos íntegros.
- [ ] Ejecutar Alembic sobre copia restaurada; prueba de reversión o plan de recuperación comprobado.
- [ ] Prueba API real con **dos tenants y credenciales distintas**, misma identidad fiscal permitida independientemente por tenant, denegación consistente de lectura/modificación cruzada de documentos/expedientes.
- [ ] Verificar confirmación/vinculación OCR con roles autorizados vs. denegados, revisión ante campos contradictorios, y no inventar FACT a partir de GRE/voucher.
- [ ] Probar dos cargas simultáneas de mismo FACT con bytes/hashes diferentes, asegurando un expediente y **sin doble efecto contable de ítems**.
- [ ] Verificar ruta **existente** productor/consumidor NEXUS antes de testear reentrega de eventos; probar idempotencia, `event_id`, `correlation_id` y mensajes fuera de orden cuando el contrato runtime exista.
- [ ] Revisar migraciones, despliegue Docker, healthcheck, secretos, observabilidad y retroceso en staging.
- [ ] Revisiones independientes, autorización explícita del responsable y CI actualizado sobre candidato final.

## Política de operación
1. No modificar OCR runtime de `main` desde esta rama.
2. No mezclar esta rama documental con PR ajenos. Mantener #264 DRAFT mientras Gate S esté abierto.
3. No ejecutar acciones VPS, merge o despliegue sin superar criterios y aprobación específica.
4. Registrar evidencia por caso: commit exacto, run URL/ID, preparación, resultado observado, incidencias y responsable.
