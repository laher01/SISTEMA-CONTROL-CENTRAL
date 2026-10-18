# Gate S — concurrencia fiscal PostgreSQL y aislamiento OCR (18/10/2026)

## Estado comprobado
Commit base PR264 `beff4f6b596cd06717b1407c91f77d45623e50de`: seis workflows SUCCESS.

## Prueba nueva
`backend/tests/test_facturas_concurrencia_postgresql_pr264.py`: dos sesiones SQLAlchemy, barrera de dos threads y transacciones simultáneas intentan insertar `Expediente` de tipo FACT con el mismo tenant, receptor, emisor, serie y correlativo. Se exige exactamente una operación `created`, una `duplicate` por IntegrityError y un expediente en base de datos. Se omite en SQLite; **solo la ejecución del workflow con FC_TEST_DATABASE_URL real PostgreSQL puede comprobar la carrera**. No se afirma cobertura OCR HTTP, ni efecto contable ni aislamiento RBAC intertenant.

## Contratos y riesgos
- `backend/app/models.py`: la identidad única de Expediente es tenant + receptor + tipo_comprobante + serie + correlativo + emisor. Los documentos tienen `UniqueConstraint(tenant_id, sha256)`.
- Contrato conceptual OCR y servicios de ingesta contienen filtros de tenant y excepciones de duplicado; faltan pruebas HTTP de expedientes con dos tokens, prueba de competencia con diferente documento/hash de origen, validación humana y eventos NEXUS reales.
- `storage.file.available` aparece en especificaciones; no se ha verificado productor/consumidor ejecutable con replay.
- El PR275 tiene 14 archivos idénticos a main para los blobs comprobados; no duplicar.

## Gate
S abierta: restauración DB y documentos del mismo lote en staging verdaderamente aislado, pruebas RBAC recuperadas, integridad, rollback y control independiente. I/D bloqueados. PR264 draft; sin VPS, merge, deploy ni modificación OCR main.
