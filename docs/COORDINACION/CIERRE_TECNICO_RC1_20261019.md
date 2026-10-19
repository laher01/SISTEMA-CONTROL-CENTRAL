# FACT CENTRAL — Cierre técnico acelerado y candidatura de lanzamiento
Fecha de corte: 2026-10-19. Alcance: evaluación de repositorio y GitHub Actions; **no** inspección ni despliegue de VPS.

## Criterio de avance: no inventar porcentajes
Un porcentaje de módulo solo puede computarse después de versionar un inventario de criterios de aceptación ponderados y registrar para **cada criterio** la evidencia de prueba integral y su estado (aprobado, fallido, pendiente). Fórmula: 100 × (peso de criterios aprobados / peso total de criterios acordados). **En ausencia de pesos y resultados exhaustivos, no hay porcentaje global verificable**. El 100% de workflows exitosos para un PR mide únicamente las verificaciones de ese SHA.

## Inventario ejecutivo y criterios de aceptación

| Área | Evidencia existente | Pendiente para aceptación |
| --- | --- | --- |
| Fundación / API / PostgreSQL / frontend | Workflow deploy-staging.yml con backend y frontend, Docker Compose y PostgreSQL | CI conjunto de SHA candidato y smoke de versión desplegada |
| Identidad SUPERADMIN / tenant | PR #323 CI 3/3; issues #311 y #312 | Revocación de sesiones tras suspensión; altas desde plataforma; aislamiento cruzado y auditoría verificables |
| Documentos / MISD | PR #336 y issue #280 | Política fiscal y migraciones, recuperación de documentos, no eliminar conservación protegida |
| OCR / recepción | Issue #221 | ZIP/RAR, despiece multirregión y regresión de ingesta según criterios acordados |
| NEXUS IA | Issues #202 y #229 | Reescaneo, alertas, formato de comprobantes y regresiones |
| Ítems / contabilidad | Issue #224 | Eliminar defecto de cero líneas y validar persistencia y conciliación |
| Jerarquías / pagos / Responsable | Issues #196, #240, #242, #256 | Permisos por rol, exclusión de pendientes, montos y liquidaciones sin regresión |
| Dashboard | Issue #189 | Filtros dependientes y totales correctos por rol |
| Landing / CMS / ventas | Issue #340, reservado a Etapa 7 | Publicación, migración Alembic 0041 y aceptación comercial |
| Recuperación | PR #328, #333, #345; CI 4/4 cada uno en SHA consultado | Captura consistente de BD y volumen, cifrado, restauración conjunta real en aislado y cotejo |
| Infraestructura / despliegue | .github/workflows/deploy-staging.yml, issue #235 | Preflight de respaldos completos, recuperación comprobada, autorización de auto-despliegue |

**Esta tabla es un inventario de bloqueantes conocidos, no un cálculo de porcentajes por módulo.** Issues abiertos no prueban por sí mismos que una función esté completamente ausente.

## PR y dependencias verificadas
- #323 revocación de sesiones tenant, SHA 9fc002f2329b3d474a3b90a011340b63d51ff3c7: 3/3 CI correcto.
- #328 verificación del volumen, SHA f7b7dedb9920113eda950f1f836b94ca388d7ec0: 4/4 CI correcto.
- #333 respaldo/restauración offline, SHA d4f33156ce94e3a6feb65a4ff014f5e4af3fc493: 4/4 CI correcto; rama **basada en #328**.
- #345 exportar manifiesto PostgreSQL restaurado/cotejo, SHA a1d595441db0193b185841cdbd75a9bfd5f4ded3: 4/4 CI correcto; rama **basada en #333**.
- Cadena #328 → #333 → #345: comparada con main tiene 27 commits delante y 0 detrás en consulta realizada.
- Los cuatro PR no tienen revisiones de aprobación registradas a este corte.
- #331 es PR temporal para compatibilidad; **NO INTEGRAR**.
- #336 MISD/pagos y #340 dependencia Etapa 7 requieren coordinación de migraciones; no modificar desde infraestructura.
- #322 protocolo de comandos: verificar su estado y aprobación separadamente.

## Candidato mínimo (RC-1): alcance sugerido
**Objetivo:** permitir actualización segura de infraestructura y seguridad sin afirmar terminación del SaaS completo.
1. Congelar un único SHA candidato construido de PR aprobados y compatibles. Revisar conflictos, protecciones y migraciones; no usar directamente una rama de pruebas como candidato.
2. Incorporar sesiones tenant (#323) tras revisión, pruebas cross-tenant y regresión de autenticación.
3. Completar una ruta de recuperación **consistente y cifrada** (PostgreSQL + documentos + referencias) con prueba de restauración aislada y evidencia de checksum, RTO/RPO y rollback.
4. Ejecutar CI backend, frontend y pruebas funcionales críticas: login, tenant, subida/lectura de documentos, expedientes, permisos y consulta.
5. Obtener aprobación de PR y **autorización expresa para el despliegue automático que puede originar el merge a main**.
6. En etapa D independiente, actualizar únicamente la VPS antigua autorizada; cotejar SHA, contenedores, logs, servicios y rutas críticas.

**Fuera de RC-1, salvo que bloqueen operaciones ya productivas:** aprendizaje NEXUS, nuevas capacidades comerciales de Etapa 7, mejora dashboard y funciones nuevas de OCR/contabilidad. No posponer defectos de seguridad, pérdida de documentos, migraciones incompatibles o errores críticos de funcionalidades ya desplegadas.

## Gates de no-despliegue
- Backup completo y recuperación PostgreSQL + volumen documental no demostrados.
- Cifrado/custodia y secretos no verificados.
- SHA y PR sin aprobación/revisiones exigidas; CI conjunto o pruebas funcionales pendientes.
- Conflictos o migraciones Alembic no conciliados.
- Falta de autorización expresa para efecto de auto-despliegue de merge en main.

## Evidencia de automatización
- Workflow .github/workflows/deploy-staging.yml: push a main activa validaciones y potencial despliegue vía SSH a VPS antigua 132.145.233.172; no equivale a una certificación de seguridad de toda producción.
- En este cierre se realizó inspección de PR, issues, workflow y CI históricos; **no** se construyó SHA combinado nuevo ni se ejecutó prueba de restauración real, frontend completo o infraestructura productiva.

## Próximo paso
Continuar desarrollo bloqueante de respaldo coordinado y prueba de recuperación aislada, entonces ejecutar T conjunto sobre un SHA candidato. Tras pruebas y aprobaciones, solicitar I con autorización específica de auto-despliegue. El despliegue efectivo solo mediante D explícitamente autorizada.
