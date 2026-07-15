# EXPEDIENT_ENGINE.md

# FACT CENTRAL

## Motor de Expedientes

---

# 1. Objetivo

Definir el funcionamiento del núcleo principal del ERP FACT CENTRAL.

El Expediente es la entidad central del sistema.

Todo documento, cálculo, validación, pago, reporte e inteligencia gira alrededor del Expediente.

---

# 2. Filosofía

FACT CENTRAL NO administra facturas.

FACT CENTRAL administra Expedientes.

Las facturas solamente alimentan un Expediente.

Los Expedientes representan una operación comercial completa.

---

# 3. ¿Qué es un Expediente?

Un Expediente es el conjunto organizado de todos los documentos y eventos relacionados con una operación comercial.

Ejemplo

Factura

↓

Guía Remitente

↓

Voucher

↓

Retención

↓

Detracción

↓

WhatsApp

↓

Correo

↓

Productos

↓

Pagos

↓

Observaciones

↓

Auditoría

↓

Historial

Todo pertenece al mismo Expediente.

---

# 4. Identidad

Cada Expediente tendrá:

UUID

Código interno

Fecha de creación

Usuario propietario

Gestor propietario

Empresa Receptora

Empresa Emisora

Estado

Nivel de confianza IA

Fecha última actualización

---

# 5. Creación

Un Expediente podrá crearse de tres maneras.

## Automática

Cuando la IA detecte que un documento inicia una nueva operación.

## Manual

Creado por un usuario autorizado.

## Asistida

Cuando la IA sugiera crear un Expediente y el usuario confirme.

---

# 6. Alimentación

Un Expediente podrá recibir documentos durante toda su vida.

Ejemplos

Factura

Guía

Voucher

RHE

Retención

Detracción

Correo

WhatsApp

Fotografías

Cotizaciones

Órdenes de Compra

Actas

Observaciones

---

# 7. Relación Inteligente

La IA deberá relacionar automáticamente documentos mediante:

RUC

Serie

Correlativo

Monto

Fecha

Productos

Empresa

Texto

Número de operación

Voucher

Coincidencias históricas

---

# 8. Estado del Expediente

Todo Expediente tendrá un estado.

Borrador

En Proceso

Pendiente

Observado

Validado

Pagado

Tributariamente Conforme

Cerrado

Archivado

---

# 9. Nivel de Completitud

El ERP calculará automáticamente el porcentaje de completitud.

Ejemplo

Factura

Guía

Voucher

Retención

Correo

WhatsApp

Observaciones

Resultado

85%

100%

65%

etc.

---

# 10. Semáforo Inteligente

Cada Expediente tendrá un color.

🟢 Completo

🟡 Incompleto

🟠 Observado

🔴 Crítico

⚫ Archivado

---

# 11. Documentos Obligatorios

Por defecto.

Factura

Guía Remitente

Voucher

Estos requisitos podrán modificarse según el tipo de operación.

---

# 12. Documentos Opcionales

Retención

Detracción

Correo

WhatsApp

Fotografías

Orden Compra

Cotización

Actas

RHE

Otros

---

# 13. Validaciones

El Expediente será validado continuamente.

Duplicados

Empresa

SUNAT

Bancarización

Retención

Detracción

Productos

Totales

Fechas

OCR

IA

---

# 14. Motor Tributario

El Expediente será enviado automáticamente al Motor Tributario.

Este calculará:

Bancarización

Retención

Detracción

ITF

Alertas SUNAT

---

# 15. Motor de Pagos

El Expediente enviará información al Motor de Pagos.

Calculará:

Comisiones

Gestor

Usuario

Retención

Porcentajes

Liquidaciones

---

# 16. Dashboard

Cada Expediente actualizará automáticamente el Dashboard.

Indicadores

Producción

Alertas

Pendientes

Empresas

Gestores

Montos

Pagos

---

# 17. Auditoría

Todo cambio quedará registrado.

Usuario

Fecha

Hora

IP

Acción

Motivo

Estado Anterior

Estado Nuevo

---

# 18. Cierre

Un Expediente podrá cerrarse únicamente cuando:

Todos los documentos obligatorios existan.

Las validaciones estén conformes.

Los pagos estén conciliados.

No existan observaciones críticas.

---

# 19. Reapertura

Un Expediente cerrado podrá reabrirse únicamente por usuarios autorizados.

Toda reapertura quedará registrada.

---

# 20. Archivado

Los Expedientes cerrados pasarán al Archivo Maestro.

Seguirán disponibles para:

Consultas

Reportes

Auditoría

IA

---

# 21. Regla Suprema

El Expediente es el corazón de FACT CENTRAL.

Todo documento debe pertenecer a un Expediente.

Toda consulta debe poder llegar a un Expediente.

Todo cálculo debe originarse desde un Expediente.

Toda inteligencia del ERP deberá construirse alrededor del Expediente.
