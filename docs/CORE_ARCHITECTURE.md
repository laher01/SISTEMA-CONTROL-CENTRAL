# CORE ARCHITECTURE
# FACT CENTRAL
## Núcleo de Arquitectura del ERP

---

# 1. Objetivo

Definir la arquitectura central del ERP FACT CENTRAL.

Este documento establece los motores principales del sistema, sus responsabilidades, dependencias y la forma en que interactúan entre sí.

Todo el desarrollo del ERP deberá respetar esta arquitectura.

---

# 2. Filosofía del ERP

FACT CENTRAL no gira alrededor de las facturas.

FACT CENTRAL gira alrededor del EXPEDIENTE.

Cada expediente representa una operación comercial completa y concentra toda la información documental, tributaria, financiera y administrativa relacionada.

Los documentos son únicamente evidencias que conforman el expediente.

---

# 3. Principios Fundamentales

1. Todo documento pertenece a un expediente.
2. Todo expediente tiene un responsable.
3. Toda acción queda registrada.
4. La IA propone, el usuario decide.
5. Nunca se elimina el documento original.
6. El sistema trabaja por módulos independientes.
7. Si un módulo falla, el resto continúa funcionando.

---

# 4. Motor 1. Seguridad

## Función

Controlar la autenticación y autorización del sistema.

## Entrada

- Usuario
- Contraseña
- Token

## Salida

- Sesión válida
- Token de sesión
- Permisos del usuario

## Depende de

- Base de Datos

---

# 5. Motor 2. Usuarios

## Función

Administrar la estructura jerárquica del sistema.

## Roles

- Administrador
- Secretaría
- Usuario
- Gestor

## Entrada

- Datos personales
- Rol
- Estado
- Permisos

## Salida

- Usuarios activos
- Jerarquía
- Permisos

## Depende de

- Seguridad

---

# 6. Motor 3. Empresas

## Función

Administrar Empresas Emisoras y Empresas Receptoras.

## Entrada

- Facturas
- RUC
- Consulta APIPERU

## Salida

- Empresa creada
- Empresa actualizada
- Historial comercial

## Depende de

- Inteligencia Artificial
- Base de Datos

---

# 7. Motor 4. Gestión Documental

## Función

Recibir y administrar todos los documentos del sistema.

## Documentos aceptados

- Facturas
- Recibos por Honorarios (RHE)
- Guías de Remisión Remitente
- Guías de Remisión Transportista
- Voucher de Pago
- Constancias de Retención
- Correos Electrónicos
- Conversaciones de WhatsApp
- Cotizaciones
- Órdenes de Compra
- Requerimientos
- Fotografías

## Responsabilidades

- Registrar archivo original.
- Generar HASH del archivo.
- Detectar duplicados.
- Clasificar documento.
- Enviar a IA para análisis.

## Salida

Documento registrado correctamente.

---

# 8. Motor 5. Inteligencia Artificial

## Función

Analizar automáticamente todos los documentos.

## Extrae

- Tipo de documento
- Serie
- Número
- Fecha
- Empresa Emisora
- Empresa Receptora
- RUC Emisor
- RUC Receptor
- Productos
- Cantidades
- Importes
- Bancos
- Voucher
- Retenciones
- Detracciones

## Además

- Relaciona documentos.
- Sugiere expedientes.
- Detecta inconsistencias.
- Aprende nuevos formatos.
- Calcula probabilidades de coincidencia.

---

# 9. Motor 6. Expedientes

## Función

Crear y administrar el Expediente Único.

Cada expediente agrupa todos los documentos relacionados con una operación.

## Documentos principales

- Factura
- Guía Remitente
- Voucher

## Documentos complementarios

- Guía Transportista
- Constancia de Retención
- Correos
- WhatsApp
- Cotizaciones
- Fotografías
- Requerimientos

## Identificador Único

RUC Receptor
+
Tipo Documento
+
Serie-Correlativo
+
RUC Emisor

Internamente utilizará un UUID.

---

# 10. Motor 7. Tributario

## Función

Validar el cumplimiento tributario.

## Procesa

- Bancarización
- Detracciones
- Retenciones
- Agentes de Retención
- Validación SUNAT
- Validación APIPERU

---

# 11. Motor 8. Pagos

## Función

Calcular automáticamente las liquidaciones.

## Calcula

- Comisión por Gestor
- Comisión por Usuario
- Adelantos
- Saldos
- Retenciones
- Detracciones

---

# 12. Motor 9. Dashboard

## Función

Mostrar información en tiempo real.

## Indicadores

- Facturas procesadas
- Expedientes completos
- Expedientes incompletos
- Bancarizado
- No bancarizado
- Con detracción
- Sin detracción
- Con retención
- Sin retención
- Producción por Gestor
- Producción por Usuario
- Producción por Empresa Receptora
- Producción por Empresa Emisora

---

# 13. Motor 10. Reportes

## Función

Generar información consolidada.

## Reportes

- PDF
- Excel
- Dashboard
- Estadísticas
- Consultas

---

# 14. Motor 11. Auditoría

## Función

Registrar absolutamente todas las acciones del sistema.

## Registra

- Inicio de sesión
- Creación
- Modificación
- Eliminación lógica
- Restauración
- Comparación de documentos
- Procesamiento IA
- Cambios de permisos

---

# 15. Motor 12. API

## Función

Comunicar FACT CENTRAL con servicios externos.

## APIs

- APIPERU
- OpenAI
- SUNAT (cuando esté disponible)
- WhatsApp Business
- Correo Electrónico
- Cloudflare
- GitHub (automatizaciones futuras)

---

# 16. Relación entre Motores

Seguridad

↓

Usuarios

↓

Empresas

↓

Gestión Documental

↓

Inteligencia Artificial

↓

Expedientes

↓

Tributario

↓

Pagos

↓

Dashboard

↓

Reportes

↓

Auditoría

La API se comunica transversalmente con todos los motores.

---

# 17. Reglas Fundamentales

1. El Expediente es el corazón del ERP.
2. Ningún documento existe sin pertenecer a un expediente.
3. Nunca se elimina el archivo original.
4. Todo documento conserva su HASH para detectar duplicados.
5. Todo cambio queda registrado en Auditoría.
6. La IA propone relaciones; el usuario confirma cuando exista duda.
7. Los módulos funcionan de manera independiente.
8. Un fallo en un módulo no debe detener el funcionamiento del resto del sistema.
9. El Dashboard refleja el estado del sistema en tiempo real.
10. Toda la información se almacena de forma segura y trazable.

---

# Arquitectura Central

El Expediente es el núcleo del ERP.

Todos los motores giran alrededor del expediente.

Toda decisión, validación, cálculo, consulta, reporte e inteligencia del sistema se realiza sobre el expediente y nunca sobre un documento individual.
