# 04_EVENT_BUS.md

# FACT CENTRAL

## EVENT BUS

### Sistema Nervioso de NEXUS

---

# 1. Objetivo

El Event Bus es el mecanismo oficial de comunicación entre todos los componentes de FACT CENTRAL.

Ningún módulo deberá comunicarse directamente con otro.

Toda comunicación se realizará mediante eventos publicados en el Event Bus.

---

# 2. Filosofía

Los módulos no deben conocerse entre sí.

Cada módulo únicamente:

- publica eventos;
- escucha eventos;
- responde eventos.

De esta manera el ERP permanece desacoplado.

---

# 3. Arquitectura

```
                 NEXUS

                   │

             EVENT BUS

──────────────────────────────────────────

OCR

DOCUMENTAL

EXPEDIENTES

TRIBUTARIO

PAGOS

DASHBOARD

AUDITOR

IA

NOTIFICACIONES

API

DIGITAL TWIN

MISSION ENGINE

STATE ENGINE

MEMORY SYSTEM

KNOWLEDGE GRAPH
```

---

# 4. ¿Qué es un Evento?

Un evento representa algo que ocurrió.

Ejemplos

Documento recibido.

OCR finalizado.

Factura clasificada.

Expediente creado.

Pago registrado.

Dashboard actualizado.

Usuario conectado.

Empresa creada.

---

# 5. Estructura

Todo evento tendrá:

UUID

Nombre

Tipo

Origen

Destino

Prioridad

Fecha

Hora

Usuario

Gestor

Expediente

Documento

Payload

Estado

---

# 6. Tipos de Eventos

Documentales

Triburarios

Financieros

Sistema

Usuarios

Seguridad

IA

Dashboard

Notificaciones

Aprendizaje

Auditoría

---

# 7. Ejemplo

DOCUMENT_UPLOADED

↓

OCR_REQUESTED

↓

OCR_COMPLETED

↓

DOCUMENT_CLASSIFIED

↓

EXPEDIENT_UPDATED

↓

MISSION_UPDATED

↓

DASHBOARD_REFRESH

↓

NOTIFICATION_SENT

---

# 8. Publicadores

Podrán publicar eventos:

Frontend.

Backend.

NEXUS.

Agentes.

OCR.

IA.

APIs.

Usuarios.

Scheduler.

Mission Engine.

---

# 9. Suscriptores

Podrán escuchar eventos:

OCR.

Documental.

Expedientes.

Dashboard.

Pagos.

Tributario.

Auditor.

Learning.

Digital Twin.

---

# 10. Prioridades

Crítica

Alta

Media

Baja

Background

---

# 11. Persistencia

Todos los eventos importantes deberán quedar registrados.

Los eventos efímeros podrán descartarse una vez procesados.

---

# 12. Reintentos

Si un evento falla:

NEXUS podrá

Reintentar.

Reencolar.

Delegar.

Escalar.

Cancelar.

Notificar.

---

# 13. Orden

El Event Bus garantizará:

Orden lógico.

Integridad.

No duplicidad.

Entrega confiable.

---

# 14. Eventos Encadenados

Un evento podrá generar otros eventos.

Ejemplo

Documento recibido

↓

OCR

↓

IA

↓

Expediente

↓

Dashboard

↓

Notificación

↓

Aprendizaje

---

# 15. Eventos Programados

El Scheduler podrá generar eventos automáticamente.

Cada hora.

Cada día.

Cada semana.

Cada mes.

---

# 16. Auditoría

Todo evento registrará:

Origen.

Destino.

Tiempo.

Resultado.

Usuario.

Agente.

Estado.

---

# 17. Seguridad

Cada evento deberá validar:

Permisos.

Autenticación.

Integridad.

Firma.

Origen.

---

# 18. Monitoreo

NEXUS supervisará:

Eventos por minuto.

Tiempo promedio.

Eventos fallidos.

Eventos pendientes.

Eventos repetidos.

Cola.

Rendimiento.

---

# 19. Escalabilidad

El Event Bus permitirá incorporar nuevos motores sin modificar los existentes.

Nuevos módulos únicamente deberán:

Publicar eventos.

Escuchar eventos.

---

# 20. Regla Suprema

Nada ocurrirá directamente dentro de FACT CENTRAL.

Todo ocurrirá mediante eventos coordinados por NEXUS.

El Event Bus constituye el Sistema Nervioso del ERP.
