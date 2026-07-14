# Motores del ERP – FACT CENTRAL

## Objetivo

Definir los motores principales del ERP, sus responsabilidades y la relación entre ellos.

---

# Motor 1. Seguridad

## Función

Controlar la autenticación y autorización del sistema.

## Entrada

- Usuario
- Contraseña
- Token

## Salida

- Sesión válida
- Permisos del usuario

## Depende de

- Base de Datos

---

# Motor 2. Usuarios

## Función

Administrar Administradores, Secretarias, Usuarios y Gestores.

## Entrada

- Datos personales
- Rol
- Estado

## Salida

- Usuarios activos
- Jerarquía de acceso

## Depende de

- Seguridad

---

# Motor 3. Empresas

## Función

Administrar empresas receptoras y emisoras.

## Entrada

- Facturas
- RUC
- Consulta APIPERU

## Salida

- Empresa creada
- Empresa actualizada

## Depende de

- IA
- Base de Datos

---

# Motor 4. Documental

## Función

Recibir todos los archivos subidos.

Tipos aceptados:

- Facturas
- RHE
- Guías
- Voucher
- Correos
- WhatsApp
- Retenciones
- Cotizaciones

## Salida

Documento registrado.

---

# Motor 5. IA

## Función

Leer documentos y extraer información.

Detecta:

- Tipo
- Serie
- Número
- RUC
- Empresa
- Fecha
- Productos
- Importes

También propone relaciones entre documentos.

---

# Motor 6. Expedientes

## Función

Crear el expediente único.

Relacionar todos los documentos.

Estado del expediente.

---

# Motor 7. Tributario

## Función

Validaciones SUNAT.

- Bancarización
- Detracciones
- Retenciones
- Agente de Retención
- RUC
- Duplicados

---

# Motor 8. Pagos

## Función

Calcular pagos.

- Gestores
- Usuarios
- Comisión
- Adelantos

---

# Motor 9. Dashboard

## Función

Mostrar estadísticas en tiempo real.

---

# Motor 10. Reportes

## Función

Generar reportes PDF, Excel y consultas.

---

# Motor 11. Auditoría

## Función

Registrar absolutamente todas las acciones.

---

# Motor 12. API

## Función

Comunicar el ERP con el exterior.

- APIPERU
- OpenAI
- SUNAT
- WhatsApp
- Correo
