# FILE_STORAGE.md

# FACT CENTRAL

## Arquitectura del Almacenamiento Documental

---

# 1. Objetivo

Definir la arquitectura física y lógica del almacenamiento documental del ERP FACT CENTRAL.

El almacenamiento debe permitir:

- recibir millones de documentos;
- procesarlos automáticamente;
- clasificarlos mediante IA;
- relacionarlos con Expedientes;
- conservar todas las versiones;
- nunca perder información.

---

# 2. Filosofía

FACT CENTRAL NO gira alrededor de los archivos.

FACT CENTRAL gira alrededor del Expediente.

Los archivos únicamente alimentan el Expediente.

Una vez procesados, pasan a formar parte de la inteligencia documental del ERP.

---

# 3. Arquitectura General

El almacenamiento estará dividido en cuatro niveles.

```
GESTORES

↓

ÁREA DE INGESTA

↓

ÁREA DE PROCESAMIENTO

↓

ARCHIVO MAESTRO

↓

BASE DE DATOS

↓

DASHBOARD
```

---

# 4. Nivel 1 — Área de Ingesta

Es la puerta de entrada del ERP.

Todo documento llega aquí.

No importa:

- formato;
- tamaño;
- nombre;
- orden;
- cantidad.

Aceptará:

- PDF
- JPG
- PNG
- TIFF
- DOC
- DOCX
- XLS
- XLSX
- CSV
- XML
- ZIP
- RAR
- Correos
- WhatsApp
- Fotografías
- Capturas

Los documentos aún NO pertenecen a ningún Expediente.

---

# 5. Nivel 2 — Área de Procesamiento

Aquí comienza la inteligencia.

Cada documento será procesado automáticamente.

Proceso:

Recepción

↓

OCR

↓

Corrección

↓

Lectura IA

↓

Clasificación

↓

Extracción de datos

↓

Validación

↓

Detección de duplicados

↓

Relación con Expediente

↓

Registro

Aquí ningún documento es definitivo.

---

# 6. Nivel 3 — Archivo Maestro

El Archivo Maestro será el repositorio definitivo.

Aquí únicamente llegan documentos completamente procesados.

Nunca recibirá archivos directamente desde los usuarios.

Toda organización será automática.

---

# 7. Organización del Archivo Maestro

Cada Expediente tendrá una carpeta única.

Ejemplo

EXP-00000001

Dentro existirán carpetas especializadas.

FACTURAS

GUIAS_REMITENTE

GUIAS_TRANSPORTISTA

VOUCHERS

RETENCIONES

DETRACCIONES

RHE

CORREOS

WHATSAPP

FOTOGRAFIAS

COTIZACIONES

OTROS

---

# 8. Documento Original

Todo documento conservará:

archivo original

fecha de ingreso

usuario

gestor

hash

UUID

Nunca será modificado.

---

# 9. Documento Procesado

El ERP podrá generar:

OCR

JSON

Miniaturas

Versiones corregidas

Versiones optimizadas

Estos archivos nunca reemplazarán al original.

---

# 10. Versionado

Cada modificación generará una nueva versión.

V1

V2

V3

...

Siempre será posible recuperar cualquier versión anterior.

---

# 11. Identidad del Documento

Cada archivo tendrá:

UUID

HASH SHA-256

Nombre original

Nombre interno

Ruta

Estado

Tipo

Tamaño

Fecha

Usuario

Gestor

Expediente

---

# 12. Duplicados

El sistema nunca eliminará automáticamente documentos repetidos.

Los marcará como:

Posible duplicado

Duplicado confirmado

Documento relacionado

Documento reemplazado

La decisión final siempre será del usuario autorizado.

---

# 13. Integridad

Todo documento deberá poder verificarse mediante HASH.

Si un archivo cambia fuera del ERP, el sistema deberá detectarlo.

---

# 14. Base de Datos

PostgreSQL NO almacenará archivos.

Solo almacenará:

metadatos

UUID

HASH

rutas

estado

relaciones

índices

---

# 15. Archivo Físico

Los documentos vivirán fuera de PostgreSQL.

La Base de Datos únicamente conocerá su ubicación.

---

# 16. Seguridad

Ningún usuario accederá directamente al disco.

Todo acceso será mediante el Backend.

Las rutas físicas nunca serán visibles.

---

# 17. Backups

El almacenamiento deberá soportar:

Backup diario

Backup semanal

Backup mensual

Backup anual

Los respaldos serán automáticos.

---

# 18. Escalabilidad

La arquitectura deberá soportar:

Más de 10 millones de documentos.

Más de 100 millones de archivos.

Décadas de funcionamiento.

Sin cambiar la estructura.

---

# 19. Integración

El almacenamiento será utilizado por:

Motor IA

Motor OCR

Motor Tributario

Motor de Pagos

Dashboard

Reportes

Auditoría

API

---

# 20. Regla Suprema

Todo archivo físico debe poder localizarse desde un Expediente.

Y todo Expediente debe poder acceder inmediatamente a todos sus documentos físicos.

El Archivo Maestro será la fuente oficial de conservación documental del ERP FACT CENTRAL.
