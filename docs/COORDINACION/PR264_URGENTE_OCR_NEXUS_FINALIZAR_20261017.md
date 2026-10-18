# URGENTE+ zz... + S + C + FINALIZAR — OCR/NEXUS y seguridad PR264

Fecha: 2026-10-17. Alcance: rama aislada del PR #264, sin VPS, merge ni despliegue.

## Estado verificado de partida
- PR #264 DRAFT, commit `b63e5cd98af4cefbdf09aca82c9f391f80d861a8`: seis workflows SUCCESS.
- PR #277 OCR consolidado: MERGED a main; PR #275 OCR v2: abierto DRAFT, no asumir que sus cambios siguen pendientes hasta comparar los trees.
- Auditoría funcional en `docs/COORDINACION/PR264_AUDITORIA_TRABAJO10_OCR_NEXUS_20261017.md`.

## Corrección de seguridad de esta iteración
`deploy/recovery_orphan_cleanup.py`: la opción CLI `--apply` ahora exige Linux y explícitamente `CI=true`, `GITHUB_ACTIONS=true`, `FC_RECOVERY_SYNTHETIC_ONLY=YES`. El defecto anterior permitía solicitar eliminación CLI sin contexto sintético. Por defecto sigue en dry-run. Pruebas añadidas contra apply fuera del CI y para preservar los archivos durante un dry-run.

La barrera de variables de entorno es una protección accidental, **NO es autenticación ni aislamiento contra adversarios**. Las pruebas internas que llaman `cleanup(... dry_run=False)` operan únicamente sobre directorios temporales de pytest.

## Criterios de FINALIZAR (preparación, no liberación)
1. Revisar CI del SHA final: seis workflows, matriz PostgreSQL 16 y 17, RBAC FastAPI, documentos+SHA256, Alembic 0039 y rollback.
2. Contrastar PR #275 y #277/main usando diff de commits: no cherry-pick ciego ni doble integración.
3. Probar OCR con hasta diez imágenes, duplicados, conflictos de identidad, PDFs multipágina, GRE, facturas, vouchers y órdenes de compra; revisar evidencia por campo, tenant y auditoría.
4. Resolver contrato discrepante «rechazar duplicado» vs «reutilizar expediente» sin segundo impacto fiscal.
5. Auditar eventos `storage.file.available`, idempotencia, NEXUS consumer y migraciones antes de considerar integración.
6. S mantiene OPEN hasta restauración pareada en staging real aislado/autorizado y revisión humana independiente.

**Estado operativo: S ABIERTA; I/D BLOQUEADOS. No VPS, merge ni deploy.**
