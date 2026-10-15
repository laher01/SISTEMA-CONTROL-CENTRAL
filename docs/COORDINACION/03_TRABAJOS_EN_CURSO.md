# Trabajos en curso

## FC-DOC-207 — Extracción inteligente de cotizaciones
- Módulo: procesamiento documental.
- Responsable: chat del PR #207.
- Inicio: 2026-10-15.
- Rama: `feature/cotizaciones-extraccion-segura-20261015`.
- PR: https://github.com/laher01/SISTEMA-CONTROL-CENTRAL/pull/207
- Estado: **PR ABIERTO** (borrador; no integrado, ni desplegado).
- Archivos en su rama: `backend/app/api/routes/documentos.py`, `backend/app/services/extraccion_campos.py`, `backend/tests/test_separador_pdf.py`, `backend/tests/test_cotizaciones_importes.py`.
- Dependencias: #183 integrado, extracción general OCR, tratamiento de identidades comerciales.
- Pruebas: CI backend, recepción documental y roles aprobadas en `fbd72cf`.
- Pendientes: comprobación con PDF COMPOSTELA 00861 real, identificación segura de emisor/receptor, reprocesamiento histórico auditable, comparación con `main` actualizado.
- Archivos transversales: rutas/documentos y extractor general; coordinar antes de continuar modificaciones.

## FC-COORD-001 — Centro de coordinación
- Módulo: documentación transversal.
- Responsable: chat que abrió el PR de coordinación; se debe confirmar titularidad permanente.
- Inicio: 2026-10-15.
- Rama: `docs/centro-coordinacion-multichat-20261015`.
- Estado: **EN DESARROLLO**, pendiente de PR y revisión.
- Alcance: archivos `AGENTS.md` y `docs/COORDINACION/`.
- Dependencia: revisión de otros trabajos activos para evitar duplicación.
- No modifica código de aplicación.

## Registro siguiente
Añadir identificador, módulo, responsable verificable, fecha, rama, archivos, dependencias, PR, estado, evidencia y siguiente paso. No declarar como implementado lo solo propuesto.
