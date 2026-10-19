# Gate S PR #300 — Ejecución T01–T10 / estado verificable 18-10-2026

## Entradas verificadas
- PR #300 HEAD previo `331418be5f79918a63f1f7dee0e52e39b6111569`: coordination-guardrails SUCCESS; backend, recepcion-documental-ci y roles-real-integration figuraban in_progress al consultar.
- PR #286 HEAD `ca6281bb5d4295cb79274771cb85b7bc4ef2fbc7`, PR #292 HEAD `61a3a18aa071a2fb1a638ccf2285d3451db1eeba`: sin cambios de SHA durante esta ejecución, ambos DRAFT.
- Nuevo código de pruebas sintéticas: `backend/tests/test_gate_s_lifecycle_contract_examples.py`, commit `0f6d617d67fb882f81ed97fb29fff834842fffad`.

## Alcance de pruebas
Diez casos sobre objeto `Contract` en memoria, no importan modelos ORM, rutas API ni base PostgreSQL de los frentes #286/#292. Los escenarios documentan expectativas de retiro/restauración/baja, importes, tenant y líneas sin reclamar concurrencia real o coherencia física de archivos. T07 y T10 son simplificaciones ilustrativas, no sustituyen fallos entre filesystem y COMMIT ni constraints SQL. Las decisiones de runtime siguen con los responsables funcionales.

## CI
Al consultar el nuevo SHA `0f6d617d67fb882f81ed97fb29fff834842fffad`, los workflows backend, recepcion-documental-ci, roles-real-integration y coordination-guardrails estaban QUEUED. Se requiere verificar HEAD posterior del PR y conclusión completa por workflow antes de certificar pruebas.

## Bloqueantes
1. Reconciliar firma y semántica de `retirar_documentos_lote -> eliminar_documento` entre #292 y #286.
2. Acordar autorización RBAC por acción y recurso; retirada recuperable jamás debe llamar eliminación definitiva.
3. Ejecutar pruebas integradas sobre árbol candidato aislado y DB PostgreSQL descartable: referencias FACT/GRE/VCHR, ítems, sumas, concurrencia, rollback de archivo y auditoría.
4. Validar migraciones 0024/0035/0041 y restauración pareada DB/archivos antes de cerrar Gate S.
5. Ninguna rama funcional, main, VPS ni despliegue modificados desde este PR.
