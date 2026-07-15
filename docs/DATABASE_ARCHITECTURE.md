# DATABASE_ARCHITECTURE.md
# FACT CENTRAL
## Arquitectura de Base de Datos

---

# 1. Objetivo

Definir la estructura de la base de datos del ERP FACT CENTRAL.

La base de datos será el núcleo de almacenamiento de toda la información documental, administrativa, tributaria e histórica del sistema.

Motor recomendado:

PostgreSQL

---

# 2. Filosofía

La base de datos gira alrededor del EXPEDIENTE.

No gira alrededor de la factura.

Todo documento pertenece a un expediente.

Todo expediente pertenece a un cliente (Empresa Receptora).

---

# 3. Principios

• Normalización de datos.

• Integridad referencial.

• Auditoría completa.

• Escalabilidad.

• Alto rendimiento.

• Búsquedas rápidas.

• Nunca perder información.

• Todo documento conserva su historial.

---

# 4. Arquitectura General

Usuarios

↓

Gestores

↓

Empresas

↓

Expedientes

↓

Documentos

↓

Productos

↓

Pagos

↓

Auditoría

---

# 5. Tablas Principales

usuarios

roles

gestores

empresas

expedientes

documentos

productos

detalle_productos

pagos

vouchers

retenciones

guias

rhe

cotizaciones

whatsapp

correos

historial

auditoria

configuracion

api_tokens

---

# 6. Tabla Principal

EXPEDIENTES

Será la tabla más importante del ERP.

Cada expediente tendrá un UUID único.

Campos principales

UUID

Empresa Receptora

Empresa Emisora

Serie

Correlativo

Fecha

Estado

Color

Monto

Usuario

Gestor

Fecha Creación

Fecha Actualización

---

# 7. Tabla Documentos

Todo documento del ERP será registrado aquí.

Campos

UUID

Expediente

Tipo

Nombre Original

Nombre Procesado

HASH

Ruta Física

Ruta Procesada

Estado

OCR

JSON IA

Fecha Registro

---

# 8. Tabla Empresas

Campos

UUID

RUC

Razón Social

Tipo

Estado

Dirección

Distrito

Provincia

Departamento

Agente Retención

Buen Contribuyente

Fecha Alta

---

# 9. Tabla Productos

Producto Maestro.

Campos

UUID

Descripción

Unidad

Código Interno

Código SUNAT

Estado

---

# 10. Tabla Detalle Productos

Relaciona

Factura

Producto

Cantidad

Precio

IGV

Subtotal

---

# 11. Tabla Pagos

UUID

Expediente

Monto

Detracción

Retención

Bancarización

Usuario

Gestor

Estado

---

# 12. Tabla Auditoría

Todo quedará registrado.

Usuario

Fecha

IP

Acción

Tabla

Registro

Valores Anteriores

Valores Nuevos

---

# 13. Tabla Configuración

Parámetros generales del ERP.

Porcentajes

Rutas

APIs

Cloudflare

OpenAI

APIPERU

---

# 14. Relaciones

Usuario

↓

Gestor

↓

Empresa

↓

Expediente

↓

Documento

↓

Producto

↓

Pago

---

# 15. Índices

RUC

Serie

Correlativo

Fecha

UUID

HASH

Estado

Tipo Documento

Empresa

Usuario

Gestor

---

# 16. Búsquedas Optimizadas

Por RUC

Por Factura

Por Producto

Por Voucher

Por Guía

Por WhatsApp

Por Correo

Por Fecha

Por Empresa

Por Gestor

Por Usuario

---

# 17. Almacenamiento

La Base de Datos almacenará únicamente metadatos.

Los archivos físicos permanecerán en el almacenamiento documental.

Nunca se guardarán PDFs o imágenes directamente en PostgreSQL.

---

# 18. Integridad

Toda eliminación será lógica.

Nunca física.

Todo registro tendrá

Fecha Creación

Fecha Actualización

Usuario

Estado

---

# 19. Escalabilidad

Diseñada para

10 millones de documentos

100 millones de registros

Más de 500 empresas

Miles de gestores

Décadas de información

---

# 20. Seguridad

UUID en todas las tablas.

Claves foráneas.

Índices.

Restricciones.

Auditoría.

Backups automáticos.

---

# 21. Integración

La Base de Datos se comunicará con

Backend FastAPI

Motor IA

Dashboard

Cloudflare

OpenAI

APIPERU

SUNAT

---

# Regla Suprema

Toda la información del ERP gira alrededor del Expediente.

El Expediente es la unidad principal de almacenamiento del sistema.

La Base de Datos únicamente organiza, relaciona y protege esa información.
