# 25_AGENT_CATALOG.md

# FACT CENTRAL

# AGENT CATALOG

## Catálogo Oficial de Agentes de NEXUS

Versión 1.0

---

# Objetivo

Definir el catálogo oficial de Agentes Inteligentes que forman parte del Sistema Operativo Empresarial NEXUS.

Cada agente representa una unidad especializada capaz de ejecutar tareas de manera autónoma, coordinada y auditada.

---

# Filosofía

Los motores piensan.

Los agentes ejecutan.

Los motores toman decisiones.

Los agentes realizan el trabajo.

Todos los agentes trabajan coordinados mediante:

- Event Bus
- Event Router
- Scheduler
- Orchestration Engine

Nunca directamente entre ellos.

---

# Principios

Todo agente deberá ser:

- autónomo;
- especializado;
- reutilizable;
- observable;
- auditable;
- escalable;
- reemplazable.

---

# Arquitectura

```
Usuario

↓

Frontend

↓

API

↓

NEXUS

↓

Motor

↓

Agente

↓

Evento

↓

Respuesta
```

---

# Estructura Base

Todo agente deberá tener:

UUID

Nombre

Descripción

Versión

Estado

Motor Responsable

Eventos que consume

Eventos que publica

Herramientas

Permisos

Prioridad

SLA

Métricas

Nivel de Autonomía

Capacidad de Aprendizaje

---

# Estados

CREATED

READY

RUNNING

WAITING

SUSPENDED

FAILED

STOPPED

ARCHIVED

---

# Niveles de Autonomía

Nivel 1

Asistido.

Siempre requiere validación humana.

Nivel 2

Semi Autónomo.

Puede ejecutar tareas simples.

Nivel 3

Autónomo.

Ejecuta tareas operativas.

Nivel 4

Colaborativo.

Trabaja con otros agentes.

Nivel 5

Estratégico.

Puede proponer mejoras y estrategias.

---

# Catálogo Oficial

---

## AGENT_OCR

### Misión

Leer documentos.

### Funciones

OCR.

Preprocesamiento.

Detección de páginas.

Corrección de orientación.

Extracción de texto.

### Consume

DOCUMENT_UPLOADED

DOCUMENT_RECEIVED

### Publica

OCR_COMPLETED

OCR_FAILED

---

## AGENT_DOCUMENT

### Misión

Clasificar documentos.

Funciones

Tipo.

Serie.

Número.

RUC.

Empresa.

Fecha.

Productos.

Duplicados.

### Consume

OCR_COMPLETED

### Publica

DOCUMENT_CLASSIFIED

DOCUMENT_DUPLICATE_DETECTED

---

## AGENT_EXPEDIENT

### Misión

Administrar Expedientes.

Funciones

Crear.

Relacionar.

Actualizar.

Cerrar.

Reabrir.

### Consume

DOCUMENT_CLASSIFIED

### Publica

EXPEDIENT_CREATED

EXPEDIENT_UPDATED

---

## AGENT_COMPANY

### Misión

Administrar Empresas.

Funciones

Crear.

Actualizar.

Consultar.

Relacionar.

APIPERU.

SUNAT.

### Consume

COMPANY_CREATED

DOCUMENT_CLASSIFIED

### Publica

COMPANY_UPDATED

COMPANY_VERIFIED

---

## AGENT_PRODUCT

### Misión

Administrar Productos.

Funciones

Catálogo.

Relaciones.

Normalización.

Unidades.

SUNAT.

---

## AGENT_PAYMENT

### Misión

Administrar pagos.

Funciones

Voucher.

Transferencias.

Detracciones.

Retenciones.

Comisiones.

---

## AGENT_TRIBUTARY

### Misión

Validar cumplimiento tributario.

Funciones

SUNAT.

RUC.

IGV.

ITF.

Retenciones.

Detracciones.

Bancarización.

---

## AGENT_MISSION

### Misión

Ejecutar Misiones.

Funciones

Asignación.

Seguimiento.

Finalización.

Escalamiento.

---

## AGENT_DASHBOARD

### Misión

Actualizar indicadores.

Funciones

KPIs.

Gráficos.

Alertas.

Resumen Ejecutivo.

---

## AGENT_AUDIT

### Misión

Registrar auditoría.

Funciones

Logs.

Historial.

Cambios.

Eventos.

Usuarios.

---

## AGENT_SECURITY

### Misión

Supervisar seguridad.

Funciones

Permisos.

Sesiones.

Ataques.

Tokens.

Alertas.

---

## AGENT_NOTIFICATION

### Misión

Enviar notificaciones.

Funciones

Correo.

WhatsApp.

Push.

SMS.

---

## AGENT_REPORT

### Misión

Generar informes.

Funciones

PDF.

Excel.

Word.

CSV.

---

## AGENT_STORAGE

### Misión

Administrar almacenamiento.

Funciones

Guardar.

Versionar.

HASH.

Backups.

Recuperación.

---

## AGENT_API

### Misión

Gestionar integraciones.

Funciones

SUNAT.

APIPERU.

OpenAI.

Cloudflare.

Correo.

WhatsApp.

---

## AGENT_LEARNING

### Misión

Aprender.

Funciones

Patrones.

Correcciones.

Modelos.

Conocimiento.

---

## AGENT_EXECUTIVE

### Misión

Asistir a la Gerencia.

Funciones

Indicadores.

Predicciones.

Riesgos.

Recomendaciones.

Simulaciones.

---

# Herramientas

Los agentes podrán utilizar:

Motores.

Knowledge Graph.

Memory.

Storage.

OpenAI.

OCR.

APIPERU.

SUNAT.

PostgreSQL.

Dashboard.

---

# SLA

Cada agente tendrá:

Tiempo máximo.

Tiempo promedio.

Disponibilidad.

Porcentaje de éxito.

---

# Métricas

Cantidad de ejecuciones.

Tiempo promedio.

Errores.

Reintentos.

Costo.

Precisión.

Calidad.

---

# Aprendizaje

Los agentes podrán:

Aprender.

Actualizar modelos.

Mejorar precisión.

Detectar patrones.

Proponer optimizaciones.

---

# Coordinación

Los agentes nunca se comunicarán directamente.

Toda coordinación ocurrirá mediante:

Event Bus.

Event Router.

Orchestration Engine.

---

# Seguridad

Todo agente deberá respetar:

Permisos.

Organización.

Auditoría.

Confidencialidad.

Integridad.

---

# Auditoría

Cada ejecución registrará:

Agente.

Usuario.

Motor.

Evento.

Tiempo.

Resultado.

Errores.

Costo.

---

# Escalabilidad

Nuevos agentes podrán añadirse sin modificar la arquitectura principal.

Cada agente deberá registrarse oficialmente en este catálogo.

---

# Regla Suprema

Todo proceso operativo ejecutado por FACT CENTRAL deberá ser realizado por uno o más agentes registrados oficialmente en este catálogo.

Los agentes constituyen la fuerza operativa del Sistema Operativo Empresarial NEXUS y ejecutan las decisiones tomadas por los motores de inteligencia.
