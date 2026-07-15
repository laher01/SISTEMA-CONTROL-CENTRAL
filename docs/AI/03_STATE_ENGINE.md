# 03_STATE_ENGINE.md

# FACT CENTRAL

## STATE ENGINE

### Motor de Estado Global de NEXUS

---

# 1. Objetivo

El State Engine es el componente encargado de mantener el estado actual de todo el ecosistema FACT CENTRAL.

Su misión es conocer, en tiempo real, qué está ocurriendo en el ERP.

Mientras la Memoria recuerda el pasado y el Knowledge Graph conoce las relaciones, el State Engine representa el presente.

---

# 2. Filosofía

NEXUS debe ser consciente de su estado actual.

No basta con almacenar información.

Debe saber continuamente:

- qué está pasando;
- quién está trabajando;
- qué procesos están activos;
- qué agentes están ejecutándose;
- qué expedientes requieren atención;
- qué eventos acaban de ocurrir.

---

# 3. Definición de Estado

Un Estado representa la condición actual de una entidad.

Ejemplos:

Documento recibido.

Documento procesándose.

OCR finalizado.

IA clasificando.

Expediente abierto.

Expediente bloqueado.

Pago pendiente.

Pago confirmado.

Usuario conectado.

Agente ocupado.

Servidor sincronizando.

---

# 4. Entidades Monitoreadas

El State Engine supervisará:

Usuarios.

Gestores.

Empresas.

Expedientes.

Documentos.

Productos.

Pagos.

Misiones.

Agentes.

Procesos.

APIs.

Servidor.

Dashboard.

---

# 5. Estado del Documento

Cada documento podrá encontrarse en uno de los siguientes estados:

Recibido.

Validando.

OCR.

Extracción IA.

Clasificación.

Relacionando.

Pendiente.

Observado.

Rechazado.

Aprobado.

Archivado.

---

# 6. Estado del Expediente

Nuevo.

Abierto.

En proceso.

Pendiente.

En revisión.

Observado.

Completo.

Cerrado.

Reabierto.

Archivado.

---

# 7. Estado de los Agentes

Libre.

Ejecutando.

Esperando.

Suspendido.

Error.

Finalizado.

Reintentando.

Aprendiendo.

---

# 8. Estado de las Misiones

Creada.

Planificada.

Asignada.

En ejecución.

Esperando dependencia.

Completada.

Cancelada.

Fallida.

---

# 9. Estado de Usuarios

Conectado.

Desconectado.

Inactivo.

Procesando.

Supervisando.

Administrador.

Solo lectura.

---

# 10. Estado del Sistema

Normal.

Alta carga.

Modo mantenimiento.

Modo recuperación.

Modo respaldo.

Modo emergencia.

---

# 11. Eventos

Cada cambio de estado genera un evento.

Ejemplo

Factura subida.

↓

OCR terminado.

↓

IA clasificó.

↓

Expediente actualizado.

↓

Dashboard actualizado.

↓

Notificación enviada.

---

# 12. Historial de Estados

Todo cambio conservará:

Estado anterior.

Estado nuevo.

Fecha.

Hora.

Usuario.

Agente.

Motivo.

Duración.

---

# 13. Reglas

Un estado nunca podrá cambiar directamente si viola las reglas del negocio.

Ejemplo

Un expediente cerrado no podrá volver a "En proceso" sin autorización.

---

# 14. Detección de Bloqueos

El State Engine detectará automáticamente:

Procesos detenidos.

OCR congelado.

IA sin respuesta.

Expedientes olvidados.

Misiones vencidas.

Agentes inactivos.

Sincronizaciones fallidas.

---

# 15. Prioridades

Cada estado tendrá prioridad.

Alta.

Media.

Baja.

Crítica.

Las prioridades ayudarán al Decision Engine.

---

# 16. Integración

El State Engine alimentará:

Dashboard.

Mission Engine.

Reasoning Engine.

Decision Engine.

Multi Agent System.

Alertas.

Notificaciones.

Gemelo Digital.

---

# 17. Sincronización

Todos los módulos deberán informar sus cambios de estado.

El State Engine será la fuente oficial del estado del ERP.

---

# 18. Visualización

El Dashboard podrá mostrar:

Expedientes activos.

Usuarios conectados.

Documentos en proceso.

Agentes trabajando.

Procesos pendientes.

Alertas críticas.

Estado general del ERP.

---

# 19. Escalabilidad

El State Engine deberá soportar miles de cambios por segundo.

Su diseño deberá permitir procesamiento concurrente y distribuido.

---

# 20. Regla Suprema

La memoria representa el pasado.

El Knowledge Graph representa el conocimiento.

El State Engine representa el presente.

Todo razonamiento de NEXUS deberá basarse en el estado actual del sistema antes de tomar cualquier decisión.
