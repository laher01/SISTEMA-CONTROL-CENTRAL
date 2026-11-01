# Informe de avance — PAG-DOC-001

**Alcance:** voucher documental distribuido entre varias facturas, pagos parciales, extracción OCR con evidencia y vista agrupada.

**Rama:** `feat/voucher-pago-agrupado-20261031`  
**Estado:** implementado y validado en rama aislada; no integrado ni desplegado.

## Implementado

- Se agregaron `PagoDocumental` y `AsignacionPagoDocumental`, con aislamiento por tenant, huella opcional de operación, importe por factura, evidencia, confianza y confirmación explícita.
- La migración `20261031_0045_pagos_documentales_agrupados.py` deja una única cabeza Alembic (`0045`).
- La API crea o recupera idempotentemente el grupo del voucher, admite hasta 500 asignaciones por solicitud, permite redistribuir pagos pendientes y bloquea la conciliación si la suma no coincide exactamente. Las asignaciones parciales se validan contra el saldo de la factura y las filas se bloquean durante la validación transaccional.
- El OCR incorpora banco, tipo de operación, fecha/hora, número de operación, beneficiario, cuentas, agencia y remitente visible; referencias de facturas e importes quedan como sugerencias con evidencia y requieren confirmación humana. La coincidencia de importes no establece vínculos automáticamente.
- Se añadió la vista agrupada desde Pendientes y el acceso al mismo grupo desde la factura, conservando el acceso a su expediente fiscal.
- La carga por lotes detecta vouchers sobre fondos de mesa mediante límites físicos. Para fotos claras conserva el original como `FOTO`, registra cada recorte como documento independiente y añade la relación `RECORTE_IMAGEN` con caja y confianza. El OCR mejora contraste y tamaño para clasificar cada voucher.
- En fondos claros de bajo contraste, el sistema solo separa bandas cuando OCR encuentra número de operación y fecha en cada una. Si no, conserva la imagen completa en revisión; no divide por el nombre ni por el importe.
- Las pruebas incluyen el ejemplo de S/ 28,200 con cuatro facturas, diferencia y conciliación, reintento idempotente, cinco facturas, pagos parciales, transferencia, evidencia OCR y rechazo de lectura/asignación de voucher entre tenants.
- Las cinco fotos adjuntas se analizaron sin guardar las imágenes en el repositorio: se obtuvieron 23 vouchers (2 BCP y 21 en cuatro fotos de mesa) y el OCR de las 23 copias sugirió `VCHR` tras mejorar el contraste. Cada lectura de pago permanece pendiente de confirmación humana.
- Se añadieron pruebas sintéticas para seis recortes, revisión de fondo ambiguo y registro de documentos hijos con vínculo al original.

## Validación ejecutada

- Backend: `630 passed, 10 skipped` (`uv run --python 3.13 pytest`).
- Ruff: sin problemas en los archivos modificados.
- mypy: sin problemas en los cuatro módulos revisados.
- Frontend: ESLint, compilación de producción y `13` pruebas Vitest aprobadas.
- Migraciones: `0045` es la única cabeza; `git diff --check` sin errores.
- La compilación frontend conserva la advertencia existente de bundle JavaScript mayor de 500 kB. La suite backend reporta advertencias conocidas de Starlette/SQLAlchemy/Pydantic.

## Pendiente antes de proponer integración

1. **Aplicación de migración con la base objetivo:** la cadena tiene una sola cabeza y las pruebas pasan, pero falta aplicar la migración en una copia de la base de integración antes de proponerla para merge.
2. **Integración:** `Pendientes.tsx` se superpone con cambios ya abiertos en PR #388; resolver el solapamiento al preparar la integración. Esta rama no crea PR, no hace merge ni despliega.

## Criterio para retomar

Aplicar la migración en la base de integración y resolver el solapamiento con PR #388. Mantener revisión manual de OCR y conciliación; no dar por pagada ninguna factura hasta confirmar referencia y distribución.
