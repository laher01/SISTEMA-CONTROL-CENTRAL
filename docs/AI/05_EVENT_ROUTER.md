# 05_EVENT_ROUTER.md

# FACT CENTRAL

## EVENT ROUTER

### Motor Inteligente de Enrutamiento de Eventos

---

# 1. Objetivo

El Event Router es el componente encargado de analizar, clasificar, priorizar, distribuir y supervisar todos los eventos que circulan por FACT CENTRAL.

Mientras el Event Bus transporta los eventos, el Event Router decide hacia dónde deben ir.

El Event Router constituye el centro de coordinación operativa de NEXUS.

---

# 2. Filosofía

Un evento no debe llegar a todos los módulos.

Debe llegar únicamente a quienes realmente lo necesitan.

El Event Router evita:

- procesamiento innecesario;
- duplicidad;
- conflictos;
- sobrecarga;
- llamadas repetidas.

---

# 3. Arquitectura

```
               EVENT BUS

                    │

                    ▼

             EVENT ROUTER

                    │

     ┌──────────────┼──────────────┐

     ▼              ▼              ▼

OCR          DOCUMENTAL      EXPEDIENTES

     ▼              ▼              ▼

TRIBUTARIO      PAGOS      DASHBOARD

     ▼              ▼              ▼

AUDITOR       APRENDIZAJE     DIGITAL TWIN
```

---

# 4. Funciones

El Event Router deberá:

- recibir eventos;
- clasificarlos;
- validar su estructura;
- eliminar duplicados;
- priorizarlos;
- decidir destinatarios;
- controlar dependencias;
- generar nuevos eventos;
- registrar auditoría.

---

# 5. Clasificación

Los eventos serán clasificados en:

Documentales.

Tributarios.

Financieros.

Usuarios.

Sistema.

Seguridad.

Aprendizaje.

Notificaciones.

Auditoría.

Infraestructura.

---

# 6. Priorización

Cada evento tendrá un nivel de prioridad.

Crítica

Alta

Media

Baja

Background

La prioridad podrá modificarse dinámicamente.

---

# 7. Enrutamiento Inteligente

El Router decidirá automáticamente qué motores deben intervenir.

Ejemplo

DOCUMENT_UPLOADED

↓

OCR

↓

DOCUMENTAL

↓

EXPEDIENTES

↓

MISSION ENGINE

↓

DIGITAL TWIN

↓

DASHBOARD

---

# 8. Dependencias

Algunos eventos dependerán de otros.

Ejemplo

No podrá ejecutarse:

PAYMENT_CALCULATED

hasta que exista

EXPEDIENT_COMPLETED

---

# 9. Agrupación

El Router podrá agrupar eventos similares.

Ejemplo

100 facturas cargadas.

↓

Un único lote.

↓

Procesamiento masivo.

---

# 10. Duplicados

Detectará automáticamente

Eventos repetidos.

Eventos ya ejecutados.

Eventos inválidos.

Eventos expirados.

---

# 11. Balanceo

Distribuirá la carga entre Agentes.

Si un Agente está ocupado,

podrá asignar otro disponible.

---

# 12. Reintentos

Si un proceso falla

podrá

Reintentar.

Esperar.

Delegar.

Escalar.

Cancelar.

Notificar.

---

# 13. Colas

Administrará múltiples colas.

Urgente.

Normal.

Background.

Programadas.

Aprendizaje.

Auditoría.

---

# 14. Tiempos

Controlará

Tiempo de espera.

Tiempo de procesamiento.

Tiempo total.

Eventos bloqueados.

Eventos vencidos.

---

# 15. Monitoreo

Supervisará continuamente

Eventos activos.

Eventos pendientes.

Eventos procesados.

Eventos fallidos.

Eventos cancelados.

---

# 16. Auditoría

Cada decisión registrará

Evento.

Origen.

Destino.

Hora.

Tiempo.

Resultado.

Motivo.

---

# 17. Seguridad

Todo evento será validado.

Autenticación.

Permisos.

Firma.

Integridad.

Organización.

Usuario.

---

# 18. Integración

El Event Router trabajará con

Event Bus.

Mission Engine.

Scheduler.

Rules Engine.

State Engine.

Memory System.

Knowledge Graph.

Decision Engine.

Todos los Agentes.

---

# 19. Escalabilidad

El Router deberá soportar

millones de eventos diarios.

Nuevos motores podrán agregarse sin modificar su arquitectura.

---

# 20. Regla Suprema

Todo evento deberá ser analizado por el Event Router antes de ser ejecutado.

Ningún agente podrá procesar eventos directamente desde el Event Bus.

El Event Router constituye el Centro Inteligente de Distribución de Procesos de NEXUS.
