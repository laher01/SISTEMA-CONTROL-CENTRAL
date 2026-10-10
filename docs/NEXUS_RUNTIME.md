# NEXUS RUNTIME ARCHITECTURE

## Propósito

NEXUS es la capa cognitiva contextual de FACT CENTRAL.

No sustituye los servicios transaccionales, PostgreSQL, Rule Engine, Permission Engine ni la Knowledge Base oficial. Su función es interpretar preguntas, reunir contexto autorizado, consultar conocimiento relevante y explicar o recomendar acciones sin ampliar permisos.

## Flujo de una consulta

```text
Usuario
  ↓
Ruta / pantalla actual
  ↓
Operational Context
  ↓
Filtro de permisos y jerarquía
  ↓
Datos autorizados del SaaS
  ↓
Knowledge Base
  ↓
Especialistas determinísticos
  ↓
Motor conversacional opcional
  ↓
Respuesta + fuentes + auditoría
```

## Operational Context

Cada consulta incluye como mínimo:

- actor;
- rol activo;
- Tenant activo;
- Usuario o Gestor efectivo cuando corresponde;
- ruta;
- filtros visibles;
- recurso actual;
- sección funcional.

El Context Pack nunca debe ampliar el ámbito del actor.

### Alcance por rol

- SUPERADMIN / ADMINISTRADOR: ámbito del Tenant autorizado.
- GERENTE: Responsables vinculados y operación permitida.
- RESPONSABLE: Usuarios y Gestores bajo su responsabilidad.
- USUARIO: su propia producción y Gestores.
- GESTOR: su propia operación.
- SECRETARIA: contexto documental autorizado, sin acceso económico de Pagos ERP.

## Contexto por pantalla

NEXUS reconoce al menos:

- Dashboard;
- Registros;
- Documentos;
- Expedientes;
- Empresas;
- Organización;
- Producción;
- Pagos;
- Configuración.

El contexto se reconstruye en cada consulta; no se confía en identificadores enviados libremente por el navegador.

## Fuente de verdad

Orden de precedencia:

1. PostgreSQL para datos económicos, estados y relaciones operativas.
2. Servicios determinísticos de FACT CENTRAL para reglas ejecutables.
3. Knowledge Base para reglas documentadas y arquitectura.
4. Motor conversacional para explicación, relación e inferencia.

Un modelo conversacional nunca reemplaza un cálculo determinístico.

## Knowledge Base

El backend incorpora en runtime documentación versionada del repositorio.

Fuentes iniciales:

- MASTER_PLAN.md
- README.md
- docs/BUSINESS_RULES.md
- docs/DATA_MODEL.md
- docs/CORE_ARCHITECTURE.md
- docs/futuro/nexus/MULTI_AGENT_SYSTEM.md

NEXUS recupera fragmentos relevantes por consulta y por sección.

La Knowledge Base pertenece a FACT CENTRAL; NEXUS es consumidor, no propietario.

## Especialistas determinísticos

Antes de usar razonamiento abierto, NEXUS conserva herramientas especializadas para:

- revisión de expediente;
- faltantes documentales;
- consulta de RUC;
- totales de compras;
- búsqueda externa configurada.

Estas rutas son preferidas cuando la pregunta exige exactitud transaccional.

## Motor conversacional

El motor LLM es opcional y configurable mediante:

- FC_NEXUS_LLM_URL
- FC_NEXUS_LLM_TOKEN
- FC_NEXUS_LLM_MODEL
- FC_NEXUS_LLM_TIMEOUT_SECONDS

El contrato esperado es compatible con un endpoint conversacional JSON que reciba:

- model;
- messages;
- temperature.

NEXUS admite respuestas en campos comunes como:

- choices[0].message.content;
- answer;
- respuesta;
- output_text;
- text.

Si no existe motor configurado, NEXUS continúa operando con contexto estructurado y especialistas determinísticos.

## Memoria conversacional

El frontend envía un historial corto.

El backend limita cuántos mensajes incorpora mediante:

- FC_NEXUS_HISTORY_MESSAGES

La memoria conversacional no reemplaza la memoria institucional ni la base de datos.

## Límite de contexto

El Context Pack se limita mediante:

- FC_NEXUS_CONTEXT_MAX_CHARS

El objetivo es minimizar exposición de datos y mantener respuestas enfocadas.

## Seguridad

NEXUS no puede:

- cambiar Tenant;
- ampliar permisos;
- asumir otro actor;
- cerrar expedientes por sí mismo;
- aprobar o ejecutar pagos;
- modificar reglas críticas;
- declarar evidencia inexistente;
- convertir una inferencia en hecho;
- escribir conocimiento oficial sin aprobación.

Los identificadores internos innecesarios no deben enviarse al motor conversacional.

## Auditoría

Cada consulta registra:

- actor;
- rol;
- ruta;
- expediente cuando exista;
- acción;
- motor;
- sección;
- uso de Internet;
- uso de LLM.

## Evolución

### NEXUS 1

Router por reglas y palabras clave.

### NEXUS 2 — implementación actual

- contexto de pantalla;
- Operational Context;
- jerarquía autorizada;
- Knowledge Base;
- historial conversacional;
- especialistas determinísticos;
- motor LLM configurable;
- fallback contextual;
- auditoría de motor y sección.

### Próximas etapas

- Agent Orchestrator;
- herramientas internas tipadas;
- Memory System persistente y gobernado;
- Knowledge Graph;
- Document Graph;
- Evidence Engine;
- planificación multiagente;
- aprendizaje validado;
- evaluación de calidad y explicabilidad.

## Regla central

NEXUS debe pensar con contexto, pero la autoridad siempre permanece en FACT CENTRAL.
