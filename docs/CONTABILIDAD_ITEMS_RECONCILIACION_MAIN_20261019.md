# Reconciliación de Contabilidad de Ítems con main — 19/10/2026

## SHA y punto de partida
- main confirmado mediante GitHub compare: `e24599110f95b2f089fffd54ae013f827d3ae7ef`.
- PR #186: `9aac21d2a1dae1c5fe2acc7159cc5547ff816515`, DRAFT.
- PR #281: `fac5831e3f86e985ff0bcdf31b874a6ac43b1ea4`, DRAFT.
- PR #320: `969911b0712ec628d5dc408bc749895d9f25a013`, DRAFT.
- PR #325: `b088914eae2b5a07241fbc093593ea514f8ca8a7`, DRAFT.
- Nueva candidata PR #327 `test/items-reconciliacion-main-20261019` nacida **desde main vigente**, base `main`, DRAFT, sin merge.

## Conflictos reales detectados por contraste de archivos
1. `backend/app/api/routes/contabilidad_items.py` de main incorpora ámbito `RESPONSABLE`, conciliación económica y exclusión de facturas observadas. La candidata antigua no los tenía. Se conservó main y se agregaron filtros y ruta ítem→facturas con las mismas restricciones.
2. `frontend/src/paginas/ContabilidadItems.tsx` de main incorpora tabla de conciliación por moneda. Se conservó y se añadieron búsquedas, CSV filtrado y navegación de ítems a expedientes.
3. `backend/app/services/contabilidad_items_ubl.py` de main incorpora ingesta de líneas PDF/SCORPIO. Se conservó y se añadió bloqueo PostgreSQL del tenant y validación de documento antes de registrar XML.
4. `backend/app/main.py`, `backend/app/services/ingesta.py`, `backend/alembic/env.py`, `backend/tests/test_alembic_0034_integracion.py` difieren o ya contienen mejoras del main actual. **No se reemplazaron**.
5. La vieja migración `20261014_0035_contabilidad_items.py` no está presente con esa ruta en main; no debe copiarse hasta validar el grafo Alembic actual. Este candidato no altera migraciones.

## Incorporaciones aisladas
- API filtros `buscar` (nombre normalizado y descripción original) y `categoria`; CSV con mismos parámetros y detalle de facturas por producto y expediente.
- UI de filtros y vínculo `Ver facturas` sin perder conciliación monetaria.
- Reescaneo XML paginado con validación de hash, rutas, tamaño y tenants, sin reescribir OCR/PDF.
- Pruebas sintéticas en dos tenants, filtros, CSV, restauración lógica solo en consulta, concurrencia mediante bloqueo PostgreSQL, reescaneo.
- No se copió integralmente ningún archivo de servicio compartido desde #325 ni se modificaron los PR de origen.

## Validación pendiente
- Primer CI de #327: Frontend falló por saltos de línea escapados en TSX; Backend y Recepción fallaron por Ruff E501 en lista de estados. Ambos fallos de formato fueron corregidos en commits aislados.
- Segundo CI disparado por SHA `a85b71d71f796c8b58657f08e602fa046f0288c3`. Frontend y Roles Browser SUCCESS; Backend, Recepción y Roles Real todavía ejecutándose al redactar.
- Revisar fallo pytest si aparece; confirmar aislamiento, reescaneo, SQL PostgreSQL, prueba Alembic efímera y frontend, todos en el HEAD de #327.
- Revisiones y protecciones de main deben confirmarse antes de I. No borrar ramas previas por quedar obsoletas.

Sin modificación de main, ramas ajenas, VPS o datos productivos. Sin merge ni deploy.
