# DOCUMENT_LIFECYCLE.md

# FACT CENTRAL

## Ciclo de Vida del Documento

---

# 1. Objetivo

Definir todas las etapas por las que pasa un documento dentro del ERP FACT CENTRAL.

Todo documento tendrá un ciclo de vida completamente trazable desde que ingresa al sistema hasta su archivado definitivo.

---

# 2. Filosofía

Un documento nunca "aparece" dentro del ERP.

Todo documento nace.

Es procesado.

Es validado.

Es relacionado.

Es utilizado.

Es auditado.

Finalmente queda archivado.

Todo ese recorrido deberá conservarse.

---

# 3. Ciclo General

```
Documento

↓

Recepción

↓

Registro

↓

Procesamiento

↓

OCR

↓

IA

↓

Clasificación

↓

Validaciones

↓

Relación con Expediente

↓

Aprobación

↓

Archivo Maestro

↓

Consultas

↓

Reportes

↓

Auditoría

↓

Archivado Histórico
```

---

# 4. Estado 1 - Recepcionado

El documento acaba de ingresar al sistema.

Aún no ha sido leído.

No pertenece a ningún Expediente.

---

# 5. Estado 2 - Registrado

El documento recibe:

UUID

HASH

Fecha

Usuario

Gestor

Ruta Física

Estado Inicial

---

# 6. Estado 3 - Procesando

El sistema comienza automáticamente:

OCR

Corrección

Lectura

Análisis

Extracción

---

# 7. Estado 4 - Leído por IA

La Inteligencia Artificial identifica:

Tipo Documento

Serie

Número

RUC

Empresa

Fecha

Importe

Productos

Observaciones

Nivel de confianza

---

# 8. Estado 5 - Clasificado

El documento obtiene una categoría.

Ejemplo

Factura

Guía

Voucher

Retención

Detracción

Correo

WhatsApp

RHE

Cotización

Otro

---

# 9. Estado 6 - Validado

Se ejecutan las reglas del ERP.

Duplicados

RUC

SUNAT

Bancarización

Retenciones

Detracciones

Integridad

Formato

---

# 10. Estado 7 - Relacionado

El documento se relaciona con:

Empresa

Expediente

Factura

Guía

Voucher

Productos

Pagos

Otros documentos

---

# 11. Estado 8 - Observado

Si existe algún problema:

Información incompleta

Error OCR

Duplicado

Monto inconsistente

Empresa inexistente

Documento ilegible

Quedará pendiente de revisión.

---

# 12. Estado 9 - Aprobado

El usuario autorizado confirma que el documento es válido.

A partir de aquí forma parte oficial del Expediente.

---

# 13. Estado 10 - Archivado

El documento es enviado al Archivo Maestro.

Queda disponible para:

Consultas

Dashboard

Reportes

Auditoría

IA

---

# 14. Estado 11 - Histórico

El documento deja de utilizarse activamente.

Pero nunca se elimina.

Siempre permanecerá disponible.

---

# 15. Eliminación

Nunca existirá eliminación física.

Únicamente:

Eliminación lógica.

El documento conservará:

Fecha

Usuario

Motivo

Historial

---

# 16. Restauración

Todo documento eliminado lógicamente podrá restaurarse.

Toda restauración quedará auditada.

---

# 17. Auditoría

Cada cambio registrará:

Usuario

Fecha

Hora

IP

Acción

Estado anterior

Estado nuevo

Observaciones

---

# 18. Versiones

Cada modificación generará una nueva versión.

El historial completo permanecerá disponible.

---

# 19. Integración

Durante su ciclo de vida el documento podrá interactuar con:

Motor IA

Motor OCR

Motor Tributario

Motor de Pagos

Dashboard

API

Auditoría

Reportes

---

# 20. Regla Suprema

Todo documento debe ser completamente trazable desde el momento en que ingresa al ERP hasta su archivado definitivo.

Nunca deberá existir un documento sin historial, sin propietario o sin Expediente (salvo que aún se encuentre en proceso de clasificación).
