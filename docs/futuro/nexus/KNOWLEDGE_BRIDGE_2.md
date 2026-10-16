# NEXUS 2.0 — Knowledge Bridge (especificación inicial)

Estado: DISEÑO, NO IMPLEMENTADO. Este archivo no habilita accesos, procesos, secretos, sincronización ni despliegues.

## Objetivo

Permitir dos flujos independientes, auditables y autorizados:
1. Recuperar decisiones y conocimientos de conversaciones seleccionadas por el titular del contenido, mediante exportación/importación o integración oficialmente autorizada.
2. Preparar incidencias técnicas desde FACT CENTRAL para analizarlas con un proveedor de modelo autorizado y devolver propuestas revisables, sin afirmar que el modelo externo accede a la conversación privada original.

## Límites del sistema

- GitHub aloja código, documentación, incidencias y versiones revisadas. No concede acceso automático a conversaciones privadas de ChatGPT.
- La VPS ejecuta los servicios. PostgreSQL almacena memoria operativa aislada por tenant, con política de retención y eliminación.
- El motor LLM es opcional y no es fuente de verdad transaccional. Sus salidas son propuestas, nunca instrucciones ejecutables por sí solas.
- No se utilizarán cookies, sesiones, ingeniería inversa de endpoints privados o extracción no autorizada.
- Datos de un tenant no podrán convertirse en conocimiento visible para otros tenants.
- Se excluyen secretos, credenciales y datos personales innecesarios de las exportaciones a GitHub y del contexto LLM.

## Flujo A — conocimiento de conversaciones

1. Un usuario con permisos selecciona explícitamente el contenido a importar.
2. Ingesta con procedencia (fuente, fecha, versión, propietario, tenant, consentimiento, hash de contenido).
3. Clasificación: hipótesis, decisión propuesta, decisión aprobada, instrucción obsoleta.
4. Redacción de datos sensibles y extracción de unidades de conocimiento con citas al material original autorizado.
5. Revisión y aprobación por rol competente antes de publicar en la Knowledge Base institucional.
6. Indexación y recuperación filtradas por tenant, rol y fecha de vigencia.
7. Rectificación, revocación y eliminación verificables; sin reusar material revocado.

## Flujo B — incidencias y propuestas técnicas

1. NEXUS recoge error, versión, módulo, registro de pruebas y contexto mínimo sin secretos.
2. El usuario autorizado aprueba el envío a un proveedor LLM o genera un issue/PR de GitHub con información saneada.
3. NEXUS recibe un diagnóstico con evidencia, archivos afectados y pruebas sugeridas.
4. Desarrollo en rama aislada; revisión humana y CI obligatorios.
5. Las acciones sobre GitHub y VPS se ejecutan por flujos autorizados con auditoría, no por texto del LLM.
6. Tras verificar resultados, se registra la solución como experiencia validada.

## Seguridad y gobierno

- ACL y aislamiento por tenant aplicados en cada consulta, ingesta y recuperación.
- Protección frente a prompt injection: conversaciones, PDFs, issues, logs y repositorios son **datos no confiables**.
- Registro de consentimiento, accesos, versiones, revisión y acciones.
- Sin cambios automáticos a pagos, expedientes, reglas fiscales o permisos.
- Sin despliegue sin CI, backup restaurable y validación explícita de los guardarraíles existentes.

## Fases sugeridas

A. Contrato de datos, permisos y política de retención.
B. Ingesta manual segura de conversaciones exportadas y buscador con fuentes.
C. Memoria persistente versionada; aprobación y revocación.
D. Canal de incidencias GitHub y proveedor LLM autorizado.
E. Pruebas de privacidad, calidad, recuperación, regresión y restauración.

## Criterios de aceptación

- Importación explícita, procedencia verificable y permisos correctos.
- Una decisión no aprobada nunca se presenta como norma oficial.
- Nunca se filtra material entre tenants ni al proveedor externo sin autorización.
- El sistema funciona con proveedor LLM no disponible y lo indica.
- No altera el comportamiento de despliegue existente ni toca datos de producción durante esta fase documental.
