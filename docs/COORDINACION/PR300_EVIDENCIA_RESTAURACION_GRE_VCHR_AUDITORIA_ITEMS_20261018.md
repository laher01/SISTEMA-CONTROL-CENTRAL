# Gate S — Evidencia de pruebas de ciclo documental / ítems, 18-10-2026

## Hechos verificados
- PR #300 HEAD inicial `cea494f5a4aecec65a0667b7e3793747676b7114`: Backend, Recepción, Roles y guardrails **4/4 SUCCESS**; 508 pytest aprobados.
- #292 actualizó HEAD a `454d11ee4a60b8858031fca0b429c4dedf67d0b8`; antes se examinó `61a3a18aa071a2fb1a638ccf2285d3451db1eeba`. Revaluar su contrato antes de fusionar. Otros HEAD: #286 `ca6281bb5d4295cb79274771cb85b7bc4ef2fbc7`, #186 `9aac21d2a1dae1c5fe2acc7159cc5547ff816515`, #281 `fac5831e3f86e985ff0bcdf31b874a6ac43b1ea4`.
- En `backend/tests/test_gate_s_two_tenant_http.py` se añadieron a las pruebas ya aprobadas: (1) restauración **simulada alterando deleted_at**, que no representa prueba real del endpoint de restauración de #292; (2) alta sintética de documentos GRE y VCHR vinculados a un mismo expediente sin duplicar importe conciliado; (3) decisión `OBSERVADA` de ítems que excluye las líneas del resumen de ítems pero mantiene importe observado visible en conciliación.
- Último SHA de código `6fc74f040ead33d8855f8af49a8d5e3c7007f511`: **CI todavía en curso** al redactar; no inferir aprobación por los anteriores.

## Límites críticos
No se ha ejecutado el motor definitivo de #286 junto con la papelera de #292. No se han validado efectos físicos FS, pagos ERP verdaderos, notificaciones a SUNAT, ni transacciones conjuntas tras combinación de ramas. Las pruebas GRE y voucher verifican relación documental y sumatoria, no la liquidación bancaria o GRE electrónica. Probar cuando dueños autoricen contrato único y en DB efímera.

## Gate
Gate S OPEN, PR #300 DRAFT; sin merge, main, VPS, migraciones reales ni despliegue.
