# 09A_ACTION_PLANNER.md

# FACT CENTRAL

## ACTION PLANNER

### Motor de Planificación de Acciones de NEXUS

---

# 1. Objetivo

El Action Planner transforma una decisión en un plan estructurado de ejecución.

Mientras el Decision Engine determina qué decisión tomar, el Action Planner define cómo ejecutarla.

No toma decisiones.

No razona.

Planifica.

---

# 2. Filosofía

Una buena decisión no garantiza un buen resultado.

El éxito depende de ejecutar correctamente cada acción.

Toda decisión importante deberá convertirse en un plan ordenado.

---

# 3. Responsabilidades

El Action Planner deberá:

- descomponer decisiones;
- ordenar tareas;
- identificar dependencias;
- asignar responsables;
- definir prioridades;
- calcular tiempos;
- generar el plan de ejecución.

---

# 4. Entradas

Recibirá:

Decision Engine.

Mission Engine.

Business Rules.

Context Engine.

State Engine.

Reasoning Engine.

---

# 5. Salidas

Generará:

Plan de Acción.

Lista de tareas.

Eventos.

Misiones.

Notificaciones.

Dependencias.

Cronograma.

---

# 6. Estructura del Plan

Cada Plan tendrá:

UUID.

Nombre.

Objetivo.

Fecha.

Hora.

Prioridad.

Responsable.

Estado.

Tiempo estimado.

Nivel de riesgo.

---

# 7. Acción

Cada acción tendrá:

UUID.

Descripción.

Responsable.

Agente.

Dependencias.

Prioridad.

Estado.

Tiempo estimado.

Tiempo real.

Resultado.

---

# 8. Dependencias

Una acción podrá depender de otra.

Ejemplo

No cerrar Expediente

hasta

Relacionar Voucher.

---

# 9. Orden

El Planner deberá ordenar automáticamente las acciones.

Ejemplo

Factura recibida.

↓

OCR.

↓

Clasificación.

↓

Relacionar Expediente.

↓

Validación Tributaria.

↓

Actualizar Dashboard.

↓

Notificación.

---

# 10. Paralelismo

Cuando dos acciones no dependan entre sí,

podrán ejecutarse simultáneamente.

Ejemplo

Actualizar Dashboard.

Enviar Notificación.

Registrar Auditoría.

---

# 11. Reintentos

Si una acción falla:

Reintentar.

Esperar.

Delegar.

Escalar.

Cancelar.

---

# 12. Priorización

Urgente.

Alta.

Media.

Baja.

Background.

---

# 13. Asignación

Cada acción será asignada al agente más adecuado.

OCR.

Documental.

Expedientes.

Tributario.

Pagos.

Dashboard.

Auditor.

Aprendizaje.

---

# 14. Seguimiento

El Planner conocerá:

Acciones pendientes.

Acciones ejecutándose.

Acciones bloqueadas.

Acciones terminadas.

Acciones fallidas.

---

# 15. Replanificación

Si cambia el contexto,

el Action Planner podrá reconstruir el plan.

Ejemplo

Llegó un Voucher.

↓

Eliminar misión pendiente.

↓

Actualizar Expediente.

↓

Cerrar Expediente.

---

# 16. Planes Inteligentes

NEXUS podrá reutilizar planes exitosos.

Ejemplo

Proceso Factura + Guía + Voucher.

↓

Guardar plantilla.

↓

Reutilizar posteriormente.

---

# 17. Optimización

El Planner analizará:

Tiempo.

Costo.

Cantidad de agentes.

Carga.

Dependencias.

Objetivo.

Buscará siempre la mejor secuencia.

---

# 18. Auditoría

Cada plan registrará:

Quién lo creó.

Qué decisión lo originó.

Qué acciones ejecutó.

Qué resultado obtuvo.

Qué cambios sufrió.

---

# 19. Integración

Trabajará con:

Decision Engine.

Mission Engine.

Scheduler.

Event Router.

Event Bus.

Multi Agent System.

Dashboard.

Learning System.

Digital Twin.

---

# 20. Regla Suprema

Toda decisión relevante deberá transformarse en un Plan de Acción.

El éxito de FACT CENTRAL dependerá no solo de decidir correctamente, sino de ejecutar cada decisión mediante un plan organizado, auditable y optimizable.
