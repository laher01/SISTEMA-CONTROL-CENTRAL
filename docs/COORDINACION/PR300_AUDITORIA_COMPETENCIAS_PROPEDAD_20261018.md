# PR #300 — Auditoría de competencias y no duplicación (18/10/2026)

**Decisión del propietario del proyecto:** el frente **3-2.1, Módulo de Eliminación de Archivos, PR #292** es el único responsable funcional de eliminación definitiva, retirada, papelera, restauración, registros fantasma y reingesta. **PR #300 Gate S** solo verifica contratos entre frentes; no desarrolla esas funciones. El menú Contabilidad de Ítems tampoco incluye pedidos ni avances de presupuestos.

## Inventario constatado
Fuente: diff de PR #300, HEAD `15178ee0af0a97467e25d03d91dac79bbd3caa39`; **19 archivos: 1 script, 7 tests, 11 documentos**. La clasificación describe responsabilidad y destino recomendado; **no es traslado ni borrado ejecutado**.

### A — Competencia propia de Gate S: CONSERVAR con alcance delimitado
- `scripts/gate_s_contract_dryrun.py`: inspección AST, firmas/contratos de otros PR sin alterar ramas. **Reducir después** su alcance a comprobaciones no funcionales si se pactan contratos.
- `backend/tests/test_gate_s_contract_dryrun.py`: pruebas del analizador, no de negocio.
- `docs/COORDINACION/GATE_S_ENSAYO_ESTATICO_COMPAT_286_292_186_281_20261018.md`: reporte de incompatibilidades, solo lectura.
- `docs/COORDINACION/PR300_CI_VERDE_CONTRATO_REAL_286_292_20261018.md`: evidencia CI histórica, conservar como evidencia.
- `docs/COORDINACION/PR300_AST_FIRMA_SEMANTICA_286_292_20261018.md`: evidencia de frontera de integración, **sin convertirla en implementación de eliminación**.
- `docs/COORDINACION/PR300_VERIFICACION_CI_CONFLICTO_PR292_PR286_20261018.md`: evidencia y bloqueo, sin resolver por cuenta propia.

### B — Trabajo funcional ajeno o duplicado: RETIRAR DEL ALCANCE ACTIVO DE #300 tras revisión coordinada
- `backend/tests/test_gate_s_lifecycle_contract_examples.py`: simulador de retirada, restauración y eliminación; cobertura funcional de **#292**, no centro de integración.
- `backend/tests/test_gate_s_order_progress_examples.py`: porcentajes y presupuestos; **#211/#212**.
- `backend/tests/test_gate_s_items_orders_cross_contract.py`: simulación de acumulados por pedido/gestor/proveedor; **#211/#212**; no pertenece a Contabilidad de Ítems.
- `docs/COORDINACION/PR300_PEDIDOS_DASHBOARD_ITEMS_CONTRATO_TRANSVERSAL_20261018.md`: documento de pedidos; derivar referencia a #211/#212 y no continuar aquí.
- `docs/COORDINACION/PR300_PROPUESTA_API_RBAC_CICLO_DOCUMENTAL_20261018.md`: define rutas de eliminación/papelera; decisiones e implementación deben quedar **exclusivamente en #292**.
- `docs/COORDINACION/PR300_RBAC_RETIRO_RESTAURACION_MATRIZ_E2E_20261018.md`: matriz extensa de pruebas funcionales de eliminación; propietario **#292**.
- `docs/COORDINACION/PR300_T01_T10_ESTADO_EVIDENCIAS_20261018.md`: escenarios de negocio de eliminación/restauración; **#292** salvo referencias mínimas de compatibilidad.
- `docs/COORDINACION/GATE_S_PLAN_E2E_SINTETICO_FACT_GRE_VCHR_ITEMS_RESTAURACION_20261018.md`: plan funcional combinado; reasignar sus pruebas específicas a respectivos dueños; mantener únicamente criterios de frontera si se necesita.

### C — Controles de integración legítimos: CONSERVAR pero sin ampliar funcionalidades ajenas
- `backend/tests/test_gate_s_items_http_contract.py`: prueba de respuesta HTTP, validación de filtros y denegación por rol; frontera de API de **#186/#281**. Propietarios desarrollan menú y filtros.
- `backend/tests/test_gate_s_two_tenant_http.py`: fronteras entre tenant/documentos/ítems y vínculos FACT/GRE/VCHR; **no usar como implementación ni reemplazo de pruebas funcionales de #292**. Mantener solo pruebas de contrato transversales; reasignar validación detallada de papelera/restauración a #292.
- `backend/tests/test_gate_s_lifecycle_semantic_collision.py`: advertencia AST de que firmas compatibles no garantizan semántica; **conservar únicamente como guardia de integración temporal**.
- `docs/COORDINACION/PR300_EVIDENCIA_CI_ITEMS_HTTP_FILTROS_20261018.md`: evidencia de pruebas HTTP.
- `docs/COORDINACION/PR300_EVIDENCIA_RESTAURACION_GRE_VCHR_AUDITORIA_ITEMS_20261018.md`: evidencia histórica de pruebas transversales, no especificación funcional de eliminación.

## Política de trabajo desde ahora
1. **#292**: dueño único de eliminación física/lógica, papelera, restauración, fantasma, reingesta, UI, RBAC funcional y pruebas del módulo. Gate S **no implementará** ni duplicará esas pruebas.
2. **#186/#281**: extracción UBL/OCR conforme alcance, clasificación y organización de ítems, búsqueda/filtros, vínculo ítem→facturas reales, roles específicos de consulta. Gate S solo valida contrato público, tenant, ausencia de duplicados y compatibilidad documental.
3. **#211/#212**: pedidos, presupuestos, porcentajes, avance por proveedor/gestor/cliente. **Fuera de Ítems y fuera del trabajo activo de PR #300**.
4. **#300**: matriz de propietarios/dependencias, comparaciones estáticas, pruebas mínimas de interfaces entre módulos, vigilancia de CI, evidencia y comunicación de bloqueos sin corregir ramas ajenas.
5. **No borrar aún las pruebas históricas**: eliminar archivos del PR sin acuerdo podría perder evidencia o reducir cobertura. Primera decisión: congelarlas; segunda: coordinar sus destinos; tercera: retirar del diff activo con cambios auditables y CI, dentro de #300 exclusivamente.
6. No se considera resuelto un conflicto por hacer coincidir firmas; el dueño funcional decide los contratos. No proponer desplegar hasta revisión de integración autorizada.

## Estado y siguiente acción segura
Inventario concluido; **no se modificó ningún archivo funcional**. Antes de depurar el PR se debe contrastar este inventario con los propietarios de #292/#186/#281/#211/#212. La siguiente iteración de #300 debe trabajar únicamente en ítems como **frontera de integración**, no como desarrollo de su menú.

**Gate S OPEN, PR #300 DRAFT, sin merge, cambios a main, VPS, migraciones reales ni despliegue.**
