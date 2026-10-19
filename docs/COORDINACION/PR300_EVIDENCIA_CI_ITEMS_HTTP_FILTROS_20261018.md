# PR #300 — Evidencia CI y alcance de pruebas HTTP de Ítems

Fecha de auditoría: 18/10/2026, rama aislada Gate S.

## Verificación de SHA
- SHA `ae05b399889f87429d0c48f7ba24342624b23a0c`: workflows backend (39181823463), recepcion-documental-ci (39181823469), roles-real-integration (39181823439), coordination-guardrails (39181823445) **COMPLETED/SUCCESS — 4/4**.
- Log `backend` job 117836003141 registra `tests/test_gate_s_items_http_contract.py ..`: las dos pruebas HTTP existentes se ejecutaron y pasaron, además de los ficheros de pruebas sintéticas T01–T10 y pedidos/ítems.
- Se confirma ejecución individual en CI PostgreSQL de pruebas HTTP ya existentes; **no** significa integración de ramas #186, #281, #211 o #212.

## Ampliación aislada
Commit `ddfe28cb7c0a746755ab18226c7e7cb122b453d8` agrega únicamente cuatro pruebas al fichero `backend/tests/test_gate_s_items_http_contract.py`: denegación SUPERADMIN, límite inválido 501, emisor desconocido y receptor desconocido. Se basan en fixture `client` y `auth_prueba`, sin cambiar código de rutas.

## Alcance y limitaciones
- Permiso SUPERADMIN se comprueba contra `_alcance()` actual; no se concede acceso por pertenecer al rol más alto.
- Los filtros con identificadores UUID sintéticos desconocidos no demuestran todavía acceso multi-tenant con datos reales. La prueba completa requiere un segundo tenant y registros explícitos.
- No hay aquí un modelo de avance real de pedidos por proveedor/cliente; #211 y #212 siguen siendo propietarios. Tampoco se altera la persistencia UBL de #186/#281.
- Verificar CI del último SHA tras cada cambio. Gate S OPEN; no merge, main, VPS, migraciones reales ni despliegue.
