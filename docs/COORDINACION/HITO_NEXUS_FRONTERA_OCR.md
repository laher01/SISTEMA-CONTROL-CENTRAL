# HITO NEXUS — Frontera de responsabilidades con OCR

Estado: contrato de coordinación. No crea un segundo sistema documental ni modifica OCR.

## Decisión del producto (18-10-2026)
NEXUS es el asistente inteligente transversal de FACT CENTRAL y consume la información **ya procesada** por los módulos existentes. El equipo/chat OCR es responsable exclusivo de recepción, desempaquetado, importación de correo, lectura de PDF/XML/imágenes, OCR, extracción de campos, identificación de formatos y procesamiento técnico documental.

**NEXUS no crea ni reemplaza motor OCR, lectores, endpoints de carga, archivos originales ni migraciones del sistema documental.** Si detecta una necesidad de extracción, abre una incidencia reproducible para el equipo OCR, sin modificar su código.

## Eventos de integración previstos
1. Archivo/paquete/correo recibido por FACT CENTRAL.
2. Documento clasificado y extracción completada, parcial o fallida.
3. Duplicado, inconsistencia o falta de relación identificados.
4. Documento vinculado a expediente o pendiente de autorización.
5. Reprocesamiento finalizado por el servicio documental.

Los eventos deberán transportar IDs internos, tenant, actor/ámbito, tipo, estado, correlación y fecha; no archivos originales ni secretos. Los nombres exactos de eventos y esquemas deben acordarse con el dueño de los módulos actuales antes de implementar adaptadores.

## Responsabilidades de NEXUS
- Observar de forma **solo lectura** estados y resultados autorizados; no afirmar que vio un archivo que no recibió.
- Conversar y continuar la tarea desde otra pantalla conforme a permisos y persistencia.
- Explicar datos y errores con evidencia, identificar anomalías, proponer seguimiento o revisión.
- Señalar posible falta de pertinencia de conceptos sin declararlos inválidos ni ordenar su eliminación.
- Preparar solicitudes de aprobación con confirmación de un actor facultado; no activar unilateralmente empresas.
- Consultar productos, cantidades, proveedores, expedientes y relaciones con datos existentes.
- Emitir incidencias técnicas saneadas para OCR o GitHub sin ejecutar sus instrucciones.

## Responsabilidades exclusivas OCR / sistema documental
- Recibir PDFs individuales/lotes, imágenes pegadas o cargadas, ZIP/RAR sin clave, correos y otros formatos **solo en la medida en que el motor ya soporte cada uno**; soporte futuro se implementa en su chat.
- Extraer y validar estructuras documentales; conservar originales y administrar versiones y reintentos.
- Evitar duplicados y mantener trazabilidad de expedientes/documentos.
- Entregar resultados legibles por NEXUS mediante servicios y datos existentes.

## Hitos propios de NEXUS
N1. Conversación natural, seguimiento de contexto y consultas encadenadas.
N2. Observación de estados documentales existentes y explicación contextual por rol.
N3. Memoria de tarea/conversación persistente aislada por tenant.
N4. Alertas proactivas, flujo de revisión y solicitudes de aprobación autorizadas.
N5. Knowledge Bridge: conocimiento verificado, propuestas técnicas, CI y despliegue protegido.

## Criterios mínimos de integración
- Pruebas multi-tenant y de alcance por actor.
- No mutación de documentos o expedientes desde un mero mensaje de diagnóstico.
- No ejecutar código ni recomendaciones incrustadas en documentos (prompt injection).
- No duplicar OCR ni lanzar reintentos por defecto.
- Reportar claramente acciones realmente ejecutadas, datos pendientes y fallos de proveedor.
- PR #304 ya implementa un primer observador **solo lectura** con pruebas; revisarlo y no duplicarlo.
- Los PR OCR #275/#289/#290/#292 pertenecen a su línea; NEXUS únicamente los consume cuando queden listos.

## Comando
**HITO NEXUS** ejecuta el siguiente ciclo N1-N5 sobre el código real, respetando AGENTS.md, docs/COORDINACION y Issue #302. Integración/despliegue solo con CI, revisión y controles de producción. Sin ejecución asíncrona garantizada por el mero comando.
