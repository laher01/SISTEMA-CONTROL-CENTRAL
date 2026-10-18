# FACT CENTRAL — Matriz de coordinación e integración Gate S (18/10/2026)

**Alcance:** revisión de metadatos y patch/filenames de 17 PR; no demuestra actividad de otros chats en tiempo real. Propiedad funcional = **propuesta**, no asignación confirmada. Ninguna fusión ni despliegue. **Gate S OPEN.**

## Inventario verificable
| PR | Frente propuesto | Base | HEAD | Archivos clave / migración | Estado |
|---|---|---|---|---|---|
| #264 | Seguridad / recovery | integration/208-main-review-20261017 | 4c0fc325 | deploy/recovery_*, workflows de simulación, pruebas PostgreSQL | DRAFT |
| #268 | Infraestructura | main | 3d478e0f | deploy/auditar-vps-solo-lectura.sh | DRAFT |
| #281 | Contabilidad OCR/reescaneo | main | fac5831e | contabilidad_items_reescaneo.py y contabilidad_items_ubl.py | DRAFT |
| #286 | Eliminación / reingesta | main | ca6281bb | rutas documentos, expedientes, contabilidad_items, ingesta; bloqueo_documental.py | DRAFT |
| #288 | NEXUS contexto | main | 7f543e6a | nexus.py, nexus_items.py | DRAFT |
| #289 | NEXUS incidencias OCR | main | 5d384904 | casos_ocr.py, modelos, main.py, migración 0041 | DRAFT |
| #290 | Gate S pruebas tenant/items | release/264-gate-s-readiness-20261018 | 916a5a43 | test_pr264_ocr_tenant_items_isolation.py | DRAFT |
| #291 | OCR JABSA | main | d971b6f0 | test_ocr_jabsa_pypdf_real.py | DRAFT |
| #292 | Gestión documental/papelera | main | a7ccf3aa | rutas documentos, expedientes, registros; frontend Documentos | DRAFT |
| #293 | Gate S pruebas OCR/RBAC | test/264-ocr-rbac-tenant-items-20261018 | 89093469 | test_pr290_ocr_document_api_rbac.py, test_pr290_ubl_postgres_concurrency.py | DRAFT |
| #294 | Gate S autenticación integral | test/290-ocr-rbac-postgres-20261018 | c4be6af8 | tests login cookies y GRE/VCHR, evidencia | DRAFT |
| #295 | Infraestructura OCR | main | 8ab76584 | workflow diagnostico-vps-ocr.yml | DRAFT |
| #296 | Gate S inventario VPS | test/293-auth-real-staging-gate-20261018 | 465a07db | documentos coordinación únicamente | DRAFT |
| #102 | Rol Responsable | main | 9aceb5e9 | migración 0024, models.py, api/deps.py, responsable.py | DRAFT |
| #186 | Contabilidad Ítems | main | 9aac21d2 | migración 0035, items/ingesta/main.py, frontend ContabilidadItems | DRAFT |
| #217 | Etapa 7 CMS | main | 5144f6bb | contrato documental CMS | DRAFT |
| #238 | Etapa 7 landing | main | 4a9540d6 | validador landing TS + test | DRAFT |

Los SHA anteriores son prefijos informativos del HEAD consultado; verificar SHA completo antes de pruebas y merge. Un PR DRAFT con CI verde NO equivale a integrado ni a otro chat activo.

## Cruces detectados por comparación exacta de rutas modificadas
**Riesgo alto (mismo archivo en ramas candidatas):**
- #286 ↔ #292: `backend/app/api/routes/documentos.py`, `expedientes.py`, `backend/tests/test_api.py`. Contrato eliminación / retirada / restauración, sin reescribir módulos. Requiere matriz de transiciones, efectos contables, auditoría, roles y concurrencia.
- #281 ↔ #186: `backend/app/services/contabilidad_items_ubl.py`, `backend/tests/test_contabilidad_items_persistencia.py`. Reescaneo e idempotencia, revisar portado sobre HEAD actual de main.
- #286 ↔ #186: `backend/app/api/routes/contabilidad_items.py` e `backend/app/services/ingesta.py`. Retirada no debe dejar sumatorias fantasma, y reingesta no debe duplicar líneas.
- #102 ↔ #289: `backend/app/models.py`; además #186 toca `backend/app/main.py` como #289. Se requieren migraciones y registro de rutas consistentes, aunque dominios sean independientes.

**Riesgo medio (contrato compartido, no necesariamente archivo idéntico):**
- #288 ↔ #289: contexto NEXUS frente a casos OCR. No asumir un event bus operativo solo por existencia de contratos documentales.
- #291 ↔ #289 / #281: misma semántica OCR y reescaneo; especial atención a detección de facturas y evidencia de extracción.
- #264 ↔ #286/#292: restauración pareada, eliminación lógica, trazabilidad de almacenamiento y objetos huérfanos.
- #268 ↔ #295 ↔ #296: diagnóstico VPS; #296 es inventario sin código runtime, y #268/#295 proponen scripts/workflows diferentes. Evitar duplicación antes de elegir uno revisado.
- #102 ↔ #186: saldos/liquidaciones vs sumas de ítems; verificar contratos y fechas históricas.

## Dependencias de PR de este chat
#290 (base release/264-gate-s-readiness-20261018) → #293 (base test/264-ocr-rbac-tenant-items-20261018) → #294 (base test/290-ocr-rbac-postgres-20261018) → #296 (base test/293-auth-real-staging-gate-20261018). **No tratar como PR independientes hacia main**. El PR #264 tiene base `integration/208-main-review-20261017` y debe revisarse respecto al árbol actual de main; los nombres de ramas intermedias no demuestran equivalencia semántica.

## Reparto propuesto: no invadir otro chat
- **Eliminación/expedientes:** dueño de runtime #286; gestión documental propietaria de interfaz y papelera #292. Pactar contrato antes de integrar.
- **Contabilidad Ítems:** responsable funcional de #186 y #281; corregir UBL/reescaneo en ese frente, aquí solo regresiones transversales.
- **NEXUS 2.0/OCR:** propietarios funcionales de #288/#289/#291; aquí validar permisos, event idempotency *solo si hay consumidor real*.
- **Rol Responsable:** frente dedicado #102. Reconciliar modelos y migraciones con NEXUS.
- **Etapa 7:** frente CMS/landing #217/#238, separado del Gate S.
- **Infraestructura diagnóstica:** frente #268/#295; aquí auditar/readiness #296, sin nueva variante de workflow.
- **ESTE CENTRO GATE S:** pruebas transversales, mapa de dependencias, revisión de seguridad, CI por SHA, restore/rollback autorizado, decisión de integración. No reemplazar funcionalidades ajenas.

## Secuencia segura recomendada, SIN autorizar merge
1. Congelar inventario de PR, HEAD y estado CI; identificar trabajos reemplazados por ramas nuevas antes de cerrar nada.
2. Resolver contrato #286/#292: soft-delete/papelera, reingesta, sumas, auditoría, tenant RBAC; diseñar pruebas que atraviesen ambos cambios.
3. Rebase/portado controlado de #281 y #186 contra árbol común en rama integración **aislada**; revisar que `0035` y `0041` tengan lineaje Alembic válido y que migración `0024` ya exista en main antes de cualquier intento.
4. Integrar solo como ensayo en rama temporal aislada candidatos #286, #292, #186, #281 y #289; resolver colisiones por dueño funcional, no con selección automática. CI backend/frontend/roles/Alembic/SQL.
5. Incorporar pruebas #290/#293/#294 de forma selectiva al árbol integrado; comprobar que las bases intermedias no arrastren cambios ajenos.
6. Validar una cadena API realista `FACT UBL → GRE → VCHR → ítems → eliminación/restauración/reingesta`, comprobando cero duplicidad y cruce entre tenants.
7. Gate S de restauración pareada DB+archivos con hash y rollback en staging segregado solo con aprobación explícita; auditar NEXUS event bus solo sobre runtime demostrado.
8. Preparar informes de aprobación por dueño; **NO fusionar en main** sin Gate S cerrado y orden autorizado (push a main puede activar staging).

## Pruebas transversales requeridas
- Dos tenants: login real, lectura/descarga/vinculación, RBAC de baja/restauración y usuarios subordinados.
- Dos sesiones concurrentes: mismo comprobante UBL / factura, guía y voucher, sin líneas ni montos dobles.
- Eliminar → restaurar → reingresar factura/GRE/voucher en un mismo expediente, con conteos de ítems y sumas antes/después.
- Alembic upgrade desde snapshot sintético, heads múltiples detectados, rollback aislado; CI no es restore de archivos real.
- NEXUS: solo cuando se encuentre productor, cola/consumidor y almacenamiento, inyección duplicada de evento y comprobación de exactamente un efecto.
- Respaldo pareado y prueba real de restauración en staging autorizada antes de cerrar Gate S.

## Limitaciones de evidencia
Esta matriz se basa en `get_pr_info` y `fetch_pr_patch` de GitHub. Detecta coincidencias de rutas, **no garantiza conflictos textuales de git**, ya que no se ejecutó merge de ensayo ni se consultó el grafo completo de commits. No asigna identidad humana ni demuestra qué chat está trabajando ahora. No hay acceso SSH ni cambios de VPS.
