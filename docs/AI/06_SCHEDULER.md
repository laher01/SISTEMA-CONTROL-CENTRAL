# 06_SCHEDULER.md

# FACT CENTRAL

## NEXUS Scheduler

### Motor Inteligente de Planificación

---

# 1. Objetivo

El Scheduler es el responsable de administrar el tiempo dentro de FACT CENTRAL.

Su función consiste en decidir cuándo debe ejecutarse cada tarea, misión, evento o proceso.

Mientras el Event Router decide dónde enviar un evento, el Scheduler decide cuándo ejecutarlo.

---

# 2. Filosofía

El tiempo es un recurso.

No todos los procesos deben ejecutarse inmediatamente.

NEXUS deberá administrar el tiempo de forma inteligente.

---

# 3. Responsabilidades

El Scheduler deberá:

- programar tareas;
- priorizar ejecuciones;
- administrar colas;
- controlar tiempos;
- detectar bloqueos;
- ejecutar procesos automáticos;
- reintentar tareas;
- optimizar recursos.

---

# 4. Tipos de Ejecución

## Inmediata

Se ejecuta apenas ocurre un evento.

Ejemplo

Factura subida.

↓

OCR.

---

## Diferida

Se ejecuta más tarde.

Ejemplo

Reindexar documentos.

---

## Programada

Se ejecuta en una fecha específica.

Ejemplo

Cierre mensual.

---

## Periódica

Cada cierto intervalo.

Ejemplo

Actualizar Dashboard cada cinco minutos.

---

## Condicional

Solo si se cumple una condición.

Ejemplo

Cerrar Expediente únicamente si:

Factura ✔

Guía ✔

Voucher ✔

---

# 5. Prioridades

Urgente

Alta

Media

Baja

Background

Las prioridades podrán cambiar automáticamente según el estado del sistema.

---

# 6. Colas

El Scheduler administrará múltiples colas.

Procesamiento documental.

OCR.

IA.

Dashboard.

Pagos.

Tributario.

Notificaciones.

Auditoría.

Aprendizaje.

Backups.

---

# 7. Calendario Inteligente

Permitirá programar tareas:

Por minuto.

Por hora.

Diarias.

Semanales.

Mensuales.

Anuales.

Según calendario tributario.

Según calendario empresarial.

---

# 8. Dependencias

Una tarea podrá depender de otra.

Ejemplo

No ejecutar:

Generar Liquidación

Hasta que:

Expediente = Completo

---

# 9. Reintentos

Si una tarea falla:

Primer intento.

Segundo intento.

Tercer intento.

Escalar.

Notificar.

Cancelar.

Todo configurable.

---

# 10. Balanceo

El Scheduler distribuirá la carga entre los Agentes disponibles.

Evitará saturar un único motor.

---

# 11. Horarios Inteligentes

Podrá decidir ejecutar tareas pesadas durante horarios de baja actividad.

Ejemplos

Respaldos.

Reindexación.

Entrenamiento IA.

Optimización.

---

# 12. Ventanas Especiales

Permitirá definir:

Ventanas de mantenimiento.

Ventanas de actualización.

Ventanas de respaldo.

Ventanas tributarias.

Ventanas de cierre mensual.

---

# 13. Misiones

Toda misión tendrá:

Fecha de inicio.

Fecha límite.

Prioridad.

Tiempo estimado.

Tiempo consumido.

Tiempo restante.

---

# 14. Eventos

El Scheduler podrá generar eventos automáticamente.

Ejemplos

CHECK_PENDING_EXPEDIENTS

GENERATE_MONTHLY_REPORT

VERIFY_RETENTIONS

RUN_BACKUP

UPDATE_DASHBOARD

---

# 15. Estado

Cada tarea tendrá:

Pendiente.

Programada.

Ejecutando.

Esperando.

Suspendida.

Finalizada.

Fallida.

Cancelada.

---

# 16. Monitoreo

El Scheduler conocerá:

Número de tareas.

Tiempo promedio.

Tiempo máximo.

Tiempo mínimo.

Colas.

Bloqueos.

Sobrecarga.

---

# 17. Integración

Trabajará con:

NEXUS OS

Event Bus

Event Router

Mission Engine

State Engine

Decision Engine

Reasoning Engine

Todos los Agentes

Dashboard

---

# 18. Auditoría

Toda ejecución registrará:

Hora.

Inicio.

Fin.

Duración.

Usuario.

Agente.

Resultado.

Errores.

Reintentos.

---

# 19. Escalabilidad

El Scheduler deberá soportar:

Millones de tareas.

Miles de eventos simultáneos.

Procesamiento distribuido.

Varios servidores.

---

# 20. Regla Suprema

Nada deberá ejecutarse fuera del Scheduler.

Toda tarea, misión, evento o proceso deberá ser administrado por el Scheduler de NEXUS.

El tiempo constituye un recurso estratégico del ERP y será administrado de forma inteligente.
