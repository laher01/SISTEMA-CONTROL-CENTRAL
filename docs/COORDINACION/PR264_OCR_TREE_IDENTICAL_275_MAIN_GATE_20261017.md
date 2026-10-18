# URGENTE+ FINALIZAR — reconciliación OCR y seguridad S (17/10/2026)

## Hallazgo exacto de Git
- `main` actual consultado: `75e84c5d69ae1662d99e1ef671898586e2157f15`.
- PR #277 fusionado (SHA antes de merge `7ca9ecebc881bfcbde4755ca2173cdefc734ac42`).
- PR #275 DRAFT, SHA `d217f27c3e95ab10d3ad4df0bd8eb9401b06f050`. `compare(main...#275)` informa divergent: 14 commits ahead / 24 behind.
- **Comparación de Git trees por blob SHA:** los 14 archivos enumerados en el diff del PR #275 frente al ancestro coinciden exactamente (14/14) con los mismos archivos en main. Se consultaron ambos árboles recursivos `/git/trees/{SHA}?recursive=1`. No hay diferencias de contenido para estos 14 archivos, aunque la historia de commits haya divergido.
- **Conclusión:** No cherry-pick ni fusionar PR #275 para estos cambios. No cerrar ni modificar PR ajenos sin decisión formal. Funcionalidades futuras OCR deben partir de main en rama separada.

## CI de partida
Commit PR264 `b63e5cd98af4cefbdf09aca82c9f391f80d861a8` tiene 6/6 workflows SUCCESS.
El nuevo HEAD desde que se inició este trabajo es `e8ec8bda167b331a24fe97a8f37bff0086fb7106`: consultar CI final de ese SHA por separado. Nunca confundir CI de otro SHA.

## Seguridades implementadas
- `deploy/recovery_orphan_cleanup.py`: `--apply` CLI no permitido fuera de contexto Linux + GitHub Actions synthetic; se mantiene dry-run por defecto y guardas de TTL.
- Las variables de entorno NO acreditan aislamiento ni sustituyen autenticación; el Python API puede usar dry_run=False en pruebas unitarias aisladas.

## Preparación final y bloques
- Gate S todavía OPEN: staging genuinamente aislado, backup pareado DB + documentos del mismo lote, prueba rollback, integridad SHA256, aislamiento tenant + RBAC, limpieza ante SIGKILL y revisión independiente.
- Gate I/D BLOCKED para PR264. Ninguna nueva conexión VPS, merge ni deploy.
- Contratos OCR–NEXUS pendientes: resolver política de duplicados vs nueva evidencia vinculable, corrección de OCR por usuario, idempotencia de eventos `storage.file.available`, validaciones 2 tenants y endpoints existentes frente a endpoints solo propuestos.
