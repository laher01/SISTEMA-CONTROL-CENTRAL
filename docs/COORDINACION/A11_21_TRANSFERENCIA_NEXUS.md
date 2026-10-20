# A 11 -2.1 - Revisar implementación NEXUS — Transferencia de contexto

Fecha: 2026-10-18. Fuente: decisiones explícitas del usuario en conversación de FACT CENTRAL, contraste con GitHub cuando esté disponible. No es prueba de implementación.

## Mandato
Continuar NEXUS 2.0 desde el estado REAL del repositorio, no reiniciar la arquitectura. ChatGPT es director del desarrollo dentro del proyecto «101 - SISTEMA FACTURA»; GitHub coordina, versiona, prueba y despliega mediante workflows existentes; VPS aloja el SaaS. No instalar un segundo agente en VPS.

## Frontera de responsabilidades, expresa e innegociable
- **OCR/recepción documental corresponde a OTRO chat**: ingesta de PDF, XML, imágenes pegadas o subidas, lotes, ZIP/RAR sin contraseña, correo y nuevos formatos. Ese equipo mantiene los procesadores y motores de extracción.
- **NEXUS no desarrolla OCR ni modifica los motores de carga, absorción, extracción ni procesamiento existentes**. Los servicios de recepción documental ya existen en FACT CENTRAL; NEXUS los CONSUME e INTERPRETA sus resultados.
- NEXUS es la IA transversal: identifica eventos de ingreso (manual/correo/paquete/etc. si el backend expone tales eventos), analiza resultados, valida permisos y consistencia, detecta novedades y anomalías, conversa con el usuario, mantiene tareas, propone acciones autorizadas, coordina revisión/aprobaciones y aprende de decisiones verificadas.
- Si aparece una tarea de OCR, advertir: «Ese desarrollo corresponde al otro chat de OCR; aquí implementaremos solo la interfaz y coordinación de NEXUS con los servicios existentes.» Registrar dependencia; no asumir que ZIP/RAR/correo ya funcionan sin evidencia.

## Visión funcional de NEXUS
1. Conversación humana en GESTOR, USUARIO, RESPONSABLE, GERENCIA, ADMINISTRADOR, con respeto al rol, ámbito y Tenant.
2. Mantener conversación/tarea entre pantallas y sesiones con memoria persistente y retención controlada.
3. Consultar facturas, documentos, proveedores emisores, clientes receptores, ítems, cantidades, importes y fechas con evidencia y sin cruzar Tenants.
4. Supervisar entradas de cualquier canal mediante eventos del sistema existente. Informar qué entró, qué reconoció OCR, qué está en revisión y qué falta; NO simular que procesó archivos.
5. Marcar anomalías como sugerencias de revisión, no declarar inválida/eliminar factura por la descripción del ítem; conservar trazabilidad de documentos.
6. Coordinar estados pendientes de activación de empresa, expedientes provisionales y solicitudes a Administración/Gerencia sin saltar controles ni contabilizar duplicados.
7. Aprendizaje institucional: conversaciones seleccionadas e importadas con consentimiento, resultados y soluciones validadas, versionadas por Tenant; no entrenar ni cambiar código con información no autorizada.
8. GitHub Knowledge Bridge: propuestas técnicas saneadas en Issue/PR, CI, revisión, respaldo restaurable y despliegue protegido. No hay acceso directo a chats privados mediante GitHub.

## Comandos
- S...: solucionar y seguir pruebas. NO merge ni deploy.
- C...: continuar autorizado desde pendientes.
- D...: desarrollar/depurar/probar. NO merge ni deploy.
- A...: auditar, integrar y desplegar únicamente con verificaciones satisfechas y sin riesgos críticos.
- HITO NEXUS: ejecutar ciclos completos EXCLUSIVOS del desarrollo de NEXUS, sin invadir OCR. Registrar resultado y próximos pasos.
- HITO era programa amplio #302 y se reorientó para separar OCR/NEXUS. No fusionar PR de OCR desde este chat.

## Estado técnico y referencias para revalidar
- Repo: laher01/SISTEMA-CONTROL-CENTRAL; rama principal main.
- Docs: AGENTS.md, docs/COORDINACION/00_LEER_PRIMERO.md y AGENTE_MAESTRO_CHATGPT_NEXUS.md.
- Issue #302: programa maestro de hitos (contenido inicial mezclaba OCR y NEXUS; aplicar esta separación actualizada).
- PR #243: diseño Knowledge Bridge.
- PR #288: seguimiento de producto al preguntar por proveedor.
- PR #289/#275/#290/#292: trabajos OCR y documentales, **propiedad de otras conversaciones**; sólo consultar dependencias y resultados, no desarrollar/merge desde NEXUS.
- PR #244 saludos NEXUS, observado fusionado anteriormente.
- Servicios de NEXUS vistos: backend/app/services/nexus.py, nexus_context.py, nexus_knowledge.py, nexus_items.py; rutas backend/app/api/routes/nexus.py. Verificar estado actual y CI.
- Etapas NEXUS prioritarias:
  N1. Comprensión conversacional y preguntas sucesivas.
  N2. Memoria persistente y continuidad de tarea entre pantallas.
  N3. Supervisión y alertas mediante eventos de módulos existentes.
  N4. Coordinación de revisiones, expedientes y aprobaciones sin ejecutar acciones no autorizadas.
  N5. Knowledge Bridge GitHub y evolución supervisada.
- Estimación conversada ~30% de la visión ampliada implementada. NO porcentaje medido.

## Al abrir el nuevo chat
1. Leer AGENTS.md, coordinación e Issue #302 y este documento.
2. Revisar main, PR de NEXUS, workflows y estados vigentes; no confiar en viejos hashes.
3. Escoger N1, corregir respuestas contextuales, preguntas sucesivas y consultas del GESTOR; NO tocar motores OCR.
4. Crear rama/PR aislados y pruebas por rol y Tenant.
5. Ejecutar CI; integrar/desplegar sólo con comando/mandato autorizado y verificaciones, informando resultados.
6. Registrar en GitHub al cierre commit, pruebas, PR, despliegue, bloqueos y siguiente acción.

## Limitaciones de autonomía
Un chat normal no continúa desarrollando por sí solo una vez que terminó el turno. La transferencia de este documento permite continuidad verificable entre chats, no transmite razonamiento privado ni da acceso a toda conversación sin mecanismos autorizados.
