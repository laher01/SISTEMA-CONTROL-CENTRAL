# 07_CONTEXT_ENGINE.md

# FACT CENTRAL

## CONTEXT ENGINE

### Motor de Contexto de NEXUS

---

# 1. Objetivo

El Context Engine es el componente encargado de reunir, filtrar y organizar la información necesaria para que NEXUS comprenda correctamente una situación antes de razonar o tomar decisiones.

La memoria contiene el pasado.

El Knowledge Graph contiene las relaciones.

El State Engine contiene el presente.

El Context Engine selecciona qué información es relevante para cada caso.

---

# 2. Filosofía

NEXUS no debe analizar toda la información del ERP cada vez que recibe una solicitud.

Debe utilizar únicamente el contexto necesario.

Un buen contexto permite decisiones precisas.

Un contexto incompleto genera errores.

Un contexto excesivo genera lentitud y confusión.

---

# 3. ¿Qué es el Contexto?

El contexto es el conjunto de información relevante para comprender una tarea, evento, documento, expediente, usuario o misión.

Puede incluir:

- usuario;
- rol;
- permisos;
- gestor;
- organización;
- expediente;
- empresa emisora;
- empresa receptora;
- documentos relacionados;
- estado actual;
- historial;
- reglas aplicables;
- riesgos;
- eventos recientes;
- misión activa;
- nivel de confianza.

---

# 4. Fuentes de Contexto

El Context Engine obtendrá información de:

- Memory System;
- Knowledge Graph;
- State Engine;
- Event Bus;
- Mission Engine;
- Expedient Digital Twin;
- Base de Datos;
- Archivo Maestro;
- Business Rules;
- Configuración;
- Auditoría.

---

# 5. Contexto del Usuario

Antes de responder o ejecutar una acción, NEXUS deberá conocer:

- identidad;
- rol;
- permisos;
- organización;
- gestores relacionados;
- empresas autorizadas;
- expedientes visibles;
- acciones permitidas;
- sesión activa.

## Regla

El contexto nunca podrá incluir información que el usuario no esté autorizado a consultar.

---

# 6. Contexto del Documento

Para analizar un documento se considerará:

- archivo original;
- tipo detectado;
- OCR;
- HASH;
- fecha de carga;
- usuario que lo subió;
- gestor propietario;
- RUC detectados;
- serie;
- correlativo;
- importe;
- moneda;
- empresas relacionadas;
- posibles duplicados;
- nivel de confianza.

---

# 7. Contexto del Expediente

Para analizar un Expediente se incluirá:

- identidad;
- emisor;
- receptor;
- gestor;
- usuario responsable;
- documentos principales;
- documentos importantes;
- documentos complementarios;
- porcentaje de completitud;
- semáforo;
- estado tributario;
- estado financiero;
- observaciones;
- riesgos;
- línea de tiempo;
- misiones activas.

---

# 8. Contexto de Empresa

Para analizar una empresa se utilizará:

- RUC;
- razón social;
- estado SUNAT;
- condición;
- agente de retención;
- historial documental;
- productos frecuentes;
- emisores o receptores relacionados;
- montos habituales;
- gestores relacionados;
- incidencias;
- riesgos;
- última verificación.

---

# 9. Contexto Temporal

Toda consulta deberá considerar el tiempo.

Ejemplos:

- hoy;
- semana actual;
- mes actual;
- período tributario;
- cierre mensual;
- fecha límite;
- historial;
- última actualización.

## Regla

Una respuesta nunca deberá mezclar períodos sin indicarlo claramente.

---

# 10. Contexto de Misión

Toda misión tendrá su propio contexto.

Incluirá:

- objetivo;
- prioridad;
- estado;
- responsable;
- fecha límite;
- tareas;
- dependencias;
- eventos;
- documentos;
- expedientes;
- agentes involucrados;
- bloqueos;
- progreso.

---

# 11. Contexto Tributario

Cuando corresponda, NEXUS deberá reunir:

- importe total;
- moneda;
- bancarización;
- detracción;
- retención;
- agente de retención;
- condición SUNAT;
- documentos de sustento;
- reglas vigentes;
- fecha de operación;
- período tributario.

---

# 12. Contexto Financiero

Podrá incluir:

- monto;
- pagos;
- vouchers;
- pagos parciales;
- saldos;
- adelantos;
- comisiones;
- liquidaciones;
- retenciones;
- detracciones;
- cuentas bancarias relacionadas.

---

# 13. Contexto de Riesgo

Para evaluar riesgos se considerará:

- duplicados;
- documentos faltantes;
- inconsistencias;
- empresas observadas;
- montos inusuales;
- fechas atípicas;
- errores anteriores;
- nivel de confianza IA;
- alertas del Agente Auditor;
- historial del Expediente.

---

# 14. Construcción del Contexto

El Context Engine deberá:

1. identificar la tarea;
2. identificar al usuario;
3. validar permisos;
4. identificar entidades relacionadas;
5. consultar estado actual;
6. recuperar memoria relevante;
7. consultar relaciones;
8. aplicar filtros;
9. limitar información;
10. construir un paquete de contexto.

---

# 15. Paquete de Contexto

Cada paquete tendrá:

- UUID;
- tipo de tarea;
- usuario;
- permisos;
- organización;
- entidades relacionadas;
- estado actual;
- hechos relevantes;
- reglas aplicables;
- riesgos;
- fuentes;
- fecha de creación;
- fecha de expiración;
- nivel de confianza.

---

# 16. Contexto Mínimo

NEXUS deberá utilizar el contexto mínimo suficiente para resolver correctamente una tarea.

No deberá enviar información innecesaria a modelos externos.

Esto reduce:

- costo;
- tiempo;
- exposición de datos;
- errores;
- confusión.

---

# 17. Contexto Dinámico

El contexto podrá actualizarse mientras una misión esté en ejecución.

Ejemplo:

Se recibe un nuevo Voucher.

↓

El State Engine cambia.

↓

El Context Engine actualiza el Expediente.

↓

El Reasoning Engine vuelve a evaluar.

---

# 18. Conflictos de Contexto

Cuando existan datos contradictorios, el Context Engine deberá:

- conservar ambas versiones;
- identificar las fuentes;
- comparar fechas;
- comparar confianza;
- señalar el conflicto;
- solicitar validación cuando sea necesario.

Nunca ocultará una contradicción.

---

# 19. Expiración del Contexto

El contexto no será permanente.

Deberá reconstruirse cuando:

- cambie el estado;
- llegue un nuevo documento;
- cambien permisos;
- cambie una regla;
- venza su tiempo de validez;
- se reabra una misión;
- exista una corrección.

---

# 20. Seguridad

Todo contexto deberá respetar:

- organización;
- rol;
- permiso;
- usuario propietario;
- gestor propietario;
- clasificación de información;
- auditoría;
- minimización de datos.

---

# 21. Auditoría

Cada paquete de contexto registrará:

- quién lo solicitó;
- qué información incluyó;
- qué fuentes utilizó;
- qué reglas aplicó;
- qué información excluyó;
- cuándo fue creado;
- para qué tarea fue utilizado.

---

# 22. Integración

El Context Engine trabajará con:

- Memory System;
- Knowledge Graph;
- State Engine;
- Event Bus;
- Event Router;
- Scheduler;
- Reasoning Engine;
- Decision Engine;
- Learning System;
- Mission Engine;
- Multi Agent System.

---

# 23. Regla Suprema

NEXUS nunca deberá razonar sin contexto.

Toda decisión deberá basarse en información actual, relevante, autorizada, trazable y suficiente.

El Context Engine determina qué debe conocer NEXUS antes de pensar.
