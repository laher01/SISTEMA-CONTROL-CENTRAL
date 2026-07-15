# 01_MEMORY_SYSTEM.md

# FACT CENTRAL

## Sistema de Memoria de NEXUS

---

# 1. Objetivo

Definir cómo NEXUS almacena, organiza, consulta y utiliza la memoria del ERP.

La memoria permitirá que FACT CENTRAL recuerde:

- lo que está ocurriendo;
- lo que ocurrió recientemente;
- el historial completo;
- las correcciones realizadas;
- los patrones aprendidos;
- las decisiones anteriores.

---

# 2. Filosofía

Un sistema inteligente no puede aprender si no recuerda.

NEXUS deberá conservar memoria suficiente para comprender el contexto, evitar repetir errores y mejorar con el tiempo.

La memoria no será una sola base de datos.

Estará dividida por niveles y funciones.

---

# 3. Niveles de Memoria

NEXUS tendrá cuatro niveles principales:

1. Memoria de Trabajo.
2. Memoria Operativa.
3. Memoria Histórica.
4. Memoria de Aprendizaje.

---

# 4. Memoria de Trabajo

Representa lo que está ocurriendo en este momento.

Contendrá temporalmente:

- usuarios conectados;
- documentos en procesamiento;
- expedientes abiertos;
- misiones activas;
- tareas en ejecución;
- agentes ocupados;
- eventos pendientes;
- alertas críticas;
- resultados parciales.

## Características

- rápida;
- temporal;
- de corta duración;
- orientada a procesos activos.

## Regla

La Memoria de Trabajo no será la fuente histórica oficial.

Su contenido deberá persistirse cuando corresponda antes de ser descartado.

---

# 5. Memoria Operativa

Representa lo ocurrido recientemente.

Podrá contener información de:

- hoy;
- esta semana;
- este mes;
- último cierre;
- expedientes recientes;
- errores recientes;
- productividad reciente;
- documentos pendientes;
- misiones abiertas;
- alertas vigentes.

## Función

Permitir que NEXUS responda rápidamente sin consultar todo el historial.

---

# 6. Memoria Histórica

Representa el historial oficial del ERP.

Contendrá:

- expedientes;
- documentos;
- pagos;
- empresas;
- productos;
- auditoría;
- usuarios;
- gestores;
- reglas;
- eventos;
- estados;
- versiones;
- cierres;
- reportes.

## Características

- permanente;
- auditable;
- trazable;
- protegida;
- recuperable.

---

# 7. Memoria de Aprendizaje

Representa el conocimiento adquirido por NEXUS.

Almacenará:

- correcciones de usuarios;
- errores de clasificación;
- nuevos formatos;
- coincidencias confirmadas;
- relaciones aceptadas;
- relaciones rechazadas;
- patrones tributarios;
- patrones documentales;
- mejoras de prompts;
- reglas aprendidas;
- resultados de agentes.

## Regla

Toda información de aprendizaje deberá tener origen, fecha, responsable y nivel de confianza.

---

# 8. Memoria por Entidad

NEXUS podrá mantener memoria específica para:

- Usuario.
- Gestor.
- Empresa.
- Expediente.
- Documento.
- Producto.
- Regla.
- Agente.
- Misión.

---

# 9. Memoria del Expediente

Cada Expediente tendrá una memoria propia.

Contendrá:

- eventos;
- documentos;
- estados;
- observaciones;
- riesgos;
- decisiones;
- validaciones;
- correcciones;
- recomendaciones;
- historial de agentes;
- misiones relacionadas.

---

# 10. Memoria de Usuario

Permitirá recordar:

- permisos;
- preferencias;
- historial de actividad;
- acciones frecuentes;
- errores repetidos;
- correcciones realizadas;
- nivel de autorización;
- expedientes consultados.

## Restricción

La memoria de un usuario nunca podrá utilizarse para mostrar información que exceda sus permisos.

---

# 11. Memoria de Empresa

Permitirá recordar:

- documentos anteriores;
- productos frecuentes;
- montos habituales;
- bancos utilizados;
- condición tributaria;
- retenciones;
- detracciones;
- gestores relacionados;
- incidencias;
- formatos documentales.

---

# 12. Memoria de Agentes

Cada Agente conservará:

- tareas ejecutadas;
- errores;
- tiempo promedio;
- tasa de éxito;
- resultados;
- nivel de confianza;
- reintentos;
- mejoras aplicadas.

---

# 13. Recuperación de Memoria

NEXUS deberá recuperar únicamente la memoria necesaria para cada tarea.

No enviará todo el historial a la IA.

Aplicará:

- filtros por usuario;
- filtros por expediente;
- filtros por empresa;
- filtros por fecha;
- filtros por tipo;
- filtros por relevancia;
- límites de contexto.

---

# 14. Resumen de Memoria

Cuando la información sea demasiado extensa, NEXUS generará resúmenes.

El resumen deberá conservar:

- hechos;
- decisiones;
- observaciones;
- pendientes;
- responsables;
- fechas;
- riesgos.

Nunca deberá inventar información.

---

# 15. Caducidad

No toda memoria tendrá la misma duración.

## Memoria de Trabajo

Minutos u horas.

## Memoria Operativa

Días o meses.

## Memoria Histórica

Permanente.

## Memoria de Aprendizaje

Permanente, salvo invalidación autorizada.

---

# 16. Corrección de Memoria

Cuando una información sea corregida:

- no se borrará el registro anterior;
- se creará una nueva versión;
- se registrará quién corrigió;
- se registrará el motivo;
- se actualizará el nivel de confianza;
- quedará auditado.

---

# 17. Conflictos de Memoria

Cuando existan datos contradictorios, NEXUS deberá:

1. conservar ambas versiones;
2. identificar la fuente;
3. comparar fechas;
4. comparar nivel de confianza;
5. solicitar revisión si es necesario;
6. no elegir silenciosamente una versión.

---

# 18. Seguridad

Toda memoria estará sujeta a:

- permisos;
- rol;
- organización;
- usuario propietario;
- gestor propietario;
- auditoría;
- cifrado cuando corresponda.

---

# 19. Integración

El Sistema de Memoria trabajará con:

- NEXUS OS;
- Mission Engine;
- Event Bus;
- Knowledge Graph;
- Context Engine;
- Reasoning Engine;
- Decision Engine;
- Learning System;
- Multi Agent System;
- PostgreSQL;
- almacenamiento documental.

---

# 20. Regla Suprema

NEXUS debe recordar lo necesario para comprender, decidir y aprender.

Pero nunca debe exponer, mezclar o utilizar información fuera de los permisos correspondientes.

La memoria existe para mejorar la inteligencia del ERP sin comprometer la seguridad, la trazabilidad ni la verdad de los datos.
