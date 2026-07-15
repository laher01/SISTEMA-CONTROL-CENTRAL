# DATA MODEL
# FACT CENTRAL
## Modelo Conceptual de Datos

---

## 1. Objetivo

Definir las entidades principales de FACT CENTRAL y la forma en que se relacionan entre sí.

Este documento describe el modelo conceptual del ERP antes de convertirlo en tablas de PostgreSQL.

---

## 2. Principio Central

FACT CENTRAL gira alrededor del EXPEDIENTE.

El expediente representa una operación completa y reúne todos los documentos, validaciones, pagos, productos, responsables y estados relacionados.

---

## 3. Entidades Principales

- Usuario
- Rol
- Permiso
- Gestor
- Empresa
- Emisor
- Receptor
- Expediente
- Documento
- Documento Principal
- Documento Complementario
- Factura
- RHE
- Guía Remitente
- Guía Transportista
- Voucher
- Retención
- Producto
- Detalle de Producto
- Pago
- Adelanto
- Cuenta de Pago
- Procesamiento
- Duplicado
- Auditoría
- Configuración
- Regla de Negocio
- Conversación IA
- Corrección IA

---

## 4. Usuario

Representa a toda persona que accede al sistema.

### Tipos

- Administrador
- Secretaría
- Usuario
- Gestor

### Relaciones

Un Usuario:

- pertenece a un Rol;
- tiene Permisos;
- puede administrar Gestores;
- puede subir Documentos;
- puede consultar Expedientes;
- puede generar Reportes;
- puede ejecutar acciones auditadas.

---

## 5. Rol

Define el nivel principal de acceso.

### Roles iniciales

- Administrador
- Secretaría
- Usuario
- Gestor

### Relaciones

Un Rol:

- tiene múltiples Permisos;
- puede pertenecer a múltiples Usuarios.

---

## 6. Permiso

Define una acción específica permitida.

### Ejemplos

- ver todos los expedientes;
- crear usuarios;
- crear gestores;
- modificar empresas;
- eliminar lógicamente documentos;
- resolver duplicados;
- aprobar empresas nuevas;
- modificar porcentajes;
- consultar reportes;
- administrar IA.

---

## 7. Gestor

Representa a la persona que realiza la carga y gestión operativa de documentos.

### Relaciones

Un Gestor:

- pertenece a un Usuario;
- sube Documentos;
- genera Expedientes;
- acumula montos;
- tiene porcentajes de pago;
- puede recibir Adelantos;
- puede tener múltiples Cuentas de Pago.

---

## 8. Empresa

Entidad maestra para cualquier empresa o persona con RUC.

### Tipos

- Emisor
- Receptor
- Ambos
- Proveedor RHE

### Datos principales

- RUC;
- razón social;
- nombre comercial;
- estado;
- condición;
- dirección;
- trabaja con nosotros;
- agente de retención;
- aplica detracción;
- fecha de verificación;
- fuente de verificación.

---

## 9. Emisor

Empresa o persona que emite una Factura o un RHE.

### Relaciones

Un Emisor:

- puede tener múltiples Expedientes;
- puede vender múltiples Productos;
- puede pertenecer a uno o varios Gestores;
- puede emitir Facturas, RHE y Guías.

---

## 10. Receptor

Empresa que recibe el comprobante.

### Relaciones

Un Receptor:

- puede tener múltiples Expedientes;
- acumula montos mensuales;
- puede ser agente de retención;
- puede tener operaciones con detracción;
- puede recibir productos de múltiples Emisores.

---

## 11. Expediente

Entidad principal del ERP.

### Identificación lógica

RUC Receptor  
+ Tipo de comprobante  
+ Serie-Correlativo  
+ RUC Emisor

### Identificación interna

UUID único.

### Relaciones

Un Expediente:

- pertenece a un Receptor;
- pertenece a un Emisor;
- pertenece a un Gestor;
- pertenece a un Usuario;
- contiene múltiples Documentos;
- contiene Productos o Servicios;
- puede tener uno o varios Pagos;
- puede tener Retenciones;
- puede tener observaciones;
- tiene estado documental;
- tiene estado tributario;
- tiene porcentaje de completitud;
- aparece en el Dashboard.

---

## 12. Documento

Representa cualquier archivo subido al sistema.

### Tipos

- FACT
- RHE
- GRR
- GRT
- VCHR
- RET
- EMAIL
- WSP
- COT
- OC
- REQ
- FOTO
- OTRO

### Relaciones

Un Documento:

- es subido por un Usuario o Gestor;
- puede pertenecer a un Expediente;
- tiene un archivo original;
- tiene un HASH;
- tiene estado de procesamiento;
- puede tener texto OCR;
- puede tener resultado IA;
- puede ser duplicado;
- puede estar pendiente de relación.

---

## 13. Documento Principal

Documento que define el núcleo básico del expediente.

### Documentos principales

- FACT o RHE
- GRR
- VCHR

### Regla

Estos tres documentos determinan el estado básico del expediente.

---

## 14. Documento Importante

Documento relevante según la operación.

### Tipos

- GRT
- RET

No siempre serán obligatorios, pero sí deben validarse cuando correspondan.

---

## 15. Documento Complementario

Documento de soporte opcional.

### Tipos

- EMAIL
- WSP
- COT
- OC
- REQ
- FOTO

---

## 16. Factura

Documento principal de una operación comercial.

### Relaciones

Una Factura:

- pertenece a un Expediente;
- tiene Emisor;
- tiene Receptor;
- tiene serie y correlativo;
- tiene fecha;
- tiene importe total;
- tiene moneda;
- puede tener múltiples Detalles de Producto;
- puede tener uno o varios Pagos;
- puede estar asociada a una GRR;
- puede estar asociada a una GRT;
- puede estar asociada a una RET.

---

## 17. RHE

Recibo por Honorarios Electrónico.

### Relaciones

Un RHE:

- pertenece a un Expediente;
- tiene Emisor persona natural;
- tiene Receptor;
- tiene fecha;
- tiene importe;
- puede tener Voucher;
- no requiere Guía de Remisión.

---

## 18. Guía Remitente

Documento principal para operaciones de bienes cuando corresponda.

### Relaciones

Una GRR:

- pertenece a un Expediente;
- referencia una Factura;
- tiene Emisor;
- tiene Receptor;
- tiene punto de partida;
- tiene punto de llegada;
- tiene productos transportados.

---

## 19. Guía Transportista

Documento importante relacionado al traslado.

### Relaciones

Una GRT:

- pertenece a un Expediente;
- puede estar relacionada con una o varias GRR;
- tiene transportista;
- tiene vehículo;
- tiene conductor;
- tiene fecha;
- tiene punto de partida y llegada.

---

## 20. Voucher

Documento principal que sustenta el pago.

### Relaciones

Un Voucher:

- puede pertenecer a uno o varios Expedientes;
- puede pagar una o varias Facturas;
- puede representar pago total o parcial;
- tiene monto;
- tiene fecha;
- tiene banco;
- tiene número de operación;
- tiene cuenta origen;
- tiene cuenta destino.

---

## 21. Retención

Documento importante cuando el receptor es agente de retención.

### Relaciones

Una Retención:

- puede aplicarse a una o varias Facturas;
- tiene monto retenido;
- tiene porcentaje;
- tiene fecha;
- tiene constancia;
- afecta el monto esperado del Voucher.

---

## 22. Producto

Entidad maestra para normalizar productos y servicios.

### Datos principales

- nombre normalizado;
- descripción;
- marca;
- presentación;
- unidad;
- código interno;
- código SUNAT;
- estado.

### Relaciones

Un Producto:

- puede aparecer en múltiples Facturas;
- puede ser vendido por múltiples Emisores;
- puede ser recibido por múltiples Receptores.

---

## 23. Detalle de Producto

Representa cada línea de una Factura.

### Datos

- producto;
- descripción original;
- cantidad;
- unidad;
- precio unitario;
- subtotal;
- IGV;
- total;
- moneda.

### Relaciones

Un Detalle de Producto:

- pertenece a una Factura;
- referencia un Producto normalizado;
- pertenece indirectamente a un Emisor y Receptor.

---

## 24. Pago

Representa un monto aplicado a uno o varios Expedientes.

### Datos

- monto total;
- monto aplicado;
- fecha;
- banco;
- estado;
- tipo de pago;
- bancarizado;
- no bancarizado;
- con retención;
- sin retención;
- con detracción;
- sin detracción.

---

## 25. Adelanto

Monto entregado previamente a un Gestor o Usuario.

### Relaciones

Un Adelanto:

- pertenece a un Gestor o Usuario;
- se descuenta de una liquidación;
- tiene fecha;
- tiene monto;
- tiene sustento;
- queda auditado.

---

## 26. Cuenta de Pago

Cuenta bancaria o medio de pago asociado a un Gestor o Usuario.

### Datos

- titular;
- banco;
- tipo de cuenta;
- moneda;
- número de cuenta;
- CCI;
- porcentaje de distribución;
- estado.

---

## 27. Procesamiento

Representa cada intento de análisis de un Documento.

### Estados

- pendiente;
- en cola;
- procesando;
- procesado;
- error;
- requiere revisión;
- validado.

### Datos

- motor utilizado;
- OCR utilizado;
- perfil utilizado;
- confianza;
- resultado JSON;
- fecha de inicio;
- fecha de fin;
- error.

---

## 28. Duplicado

Representa una posible repetición documental.

### Comparaciones

- HASH exacto;
- HASH visual;
- RUC Emisor;
- RUC Receptor;
- serie-correlativo;
- fecha;
- importe;
- similitud de contenido.

### Estados

- pendiente;
- confirmado;
- no duplicado;
- conservar ambos;
- reemplazar;
- descartar nuevo.

---

## 29. Auditoría

Registra toda acción importante.

### Datos

- usuario;
- rol;
- acción;
- entidad;
- registro afectado;
- valores anteriores;
- valores nuevos;
- fecha;
- IP;
- dispositivo;
- resultado.

---

## 30. Configuración

Guarda parámetros del sistema.

### Ejemplos

- día límite de expediente;
- porcentajes por Gestor;
- reglas de retención;
- reglas de detracción;
- límite de bancarización;
- niveles de confianza IA;
- rutas de almacenamiento;
- estados permitidos;
- colores del Dashboard.

---

## 31. Regla de Negocio

Entidad que almacena reglas configurables.

### Ejemplos

- expediente completo;
- expediente vencido;
- porcentaje por Gestor;
- documento obligatorio;
- documento opcional;
- regla de asociación;
- regla de duplicidad.

---

## 32. Conversación IA

Guarda las conversaciones del Asistente Nexomar.

### Relaciones

Una Conversación IA:

- pertenece a un Usuario;
- contiene mensajes;
- puede ejecutar herramientas;
- respeta permisos;
- puede consultar Expedientes;
- queda auditada.

---

## 33. Corrección IA

Registra cuando un usuario corrige una decisión automática.

### Datos

- documento;
- resultado original;
- resultado corregido;
- usuario que corrigió;
- fecha;
- motivo;
- formato documental;
- nivel de confianza.

---

## 34. Relaciones Principales

```text
ROL
  └── USUARIO
        └── GESTOR
              └── DOCUMENTO
                    └── EXPEDIENTE
                          ├── EMISOR
                          ├── RECEPTOR
                          ├── FACTURA o RHE
                          ├── GRR
                          ├── GRT
                          ├── VCHR
                          ├── RET
                          ├── PRODUCTOS
                          ├── PAGOS
                          └── AUDITORÍA

# 35. Regla de Propiedad

Cada Documento y cada Expediente debe registrar obligatoriamente:

- Usuario propietario.
- Gestor propietario.
- Usuario que realizó la carga.
- Fecha de creación.
- Fecha de modificación.
- Estado.
- Historial completo de cambios.

---

# 36. Regla de Visibilidad

## Administrador

Tiene acceso total al sistema.

Puede crear, modificar, eliminar lógicamente y restaurar información.

---

## Secretaría

Visualiza toda la información.

Solo podrá modificar aquello que Administración le autorice mediante permisos específicos.

---

## Usuario

Visualiza únicamente:

- Sus Gestores.
- Sus Empresas.
- Sus Expedientes.
- Sus Documentos.
- Sus Reportes.
- Sus Pagos.

Nunca podrá visualizar información perteneciente a otros Usuarios.

---

## Gestor

Visualiza únicamente:

- Lo que él mismo subió.
- Sus Expedientes.
- Sus Documentos.
- Sus observaciones.
- Sus pagos.

---

# 37. Regla de Almacenamiento

La Base de Datos únicamente almacenará metadatos.

Los archivos físicos serán almacenados en el repositorio documental.

Cada archivo deberá registrar:

- UUID
- HASH
- Ruta física
- Nombre original
- Nombre procesado
- Tamaño
- Tipo
- Fecha de carga
- Estado

---

# 38. Regla de Eliminación

Toda eliminación será lógica.

Siempre deberá conservar:

- Fecha de eliminación.
- Usuario que eliminó.
- Motivo.
- Estado.
- Posibilidad de restauración.
- Auditoría.

---

# 39. Regla Suprema

El Expediente es la entidad principal del ERP.

Toda relación, cálculo, consulta, validación, reporte e inteligencia debe poder llegar siempre al Expediente correspondiente.

---

# 40. Regla de Integridad

Ningún Documento podrá pertenecer a dos Expedientes diferentes.

---

# 41. Regla de Duplicidad

La detección de duplicados utilizará:

- HASH.
- Contenido OCR.
- Serie.
- Correlativo.
- RUC Emisor.
- RUC Receptor.
- Fecha.
- Importe.
- Similitud IA.

Nunca dependerá únicamente del nombre del archivo.

---

# 42. Regla de Versionado

Si un Documento es reemplazado,

el original permanecerá almacenado.

Se creará una nueva versión.

Nunca se sobrescribirá.

---

# 43. Regla de Procesamiento

Todo Documento deberá pasar por:

Ingreso

↓

OCR

↓

Clasificación

↓

Extracción IA

↓

Validación

↓

Relación con Expediente

↓

Archivado

---

# 44. Regla de Estados

Todo Documento deberá tener un estado.

Ejemplo:

- Pendiente.
- Procesando.
- Clasificado.
- Relacionado.
- Observado.
- Validado.
- Archivado.

---

# 45. Regla de Expediente

Todo Expediente deberá tener un porcentaje de completitud.

Ejemplo

0 %

25 %

50 %

75 %

100 %

---

# 46. Regla del Semáforo

Verde

Expediente completo.

Amarillo

Solo faltan documentos opcionales.

Naranja

Falta un documento principal.

Rojo

Expediente vencido o con documentación crítica pendiente.

---

# 47. Regla de IA

La IA nunca eliminará información.

Solo propondrá:

- Clasificaciones.
- Relaciones.
- Correcciones.
- Coincidencias.
- Observaciones.

---

# 48. Regla de Aprendizaje

Toda corrección realizada por un usuario autorizado podrá utilizarse para mejorar los modelos futuros.

---

# 49. Regla de Auditoría

Toda acción importante quedará registrada.

Sin excepción.

---

# 50. Regla de Trazabilidad

Desde cualquier Documento deberá ser posible llegar al Expediente.

Desde cualquier Expediente deberá ser posible llegar a todos sus Documentos.

---

# 51. Regla de Consistencia

Toda modificación deberá mantener la integridad referencial.

Nunca podrán existir referencias rotas.

---

# 52. Regla de Rendimiento

Las consultas frecuentes deberán ejecutarse mediante índices optimizados.

---

# 53. Regla de Escalabilidad

La arquitectura deberá soportar millones de documentos sin modificar el modelo conceptual.

---

# 54. Regla de Seguridad

Toda consulta deberá validar previamente los permisos del usuario autenticado.

---

# 55. Regla de APIs

Ningún módulo accederá directamente a otro módulo.

Toda comunicación será mediante APIs o servicios internos.

---

# 56. Regla de Configuración

Los porcentajes, límites y parámetros deberán almacenarse en Configuración y nunca quedar escritos de forma fija en el código.

---

# 57. Regla de Históricos

Nunca se perderá información histórica.

Todo cambio conservará trazabilidad.

---

# 58. Regla de Recuperación

Todo Documento eliminado lógicamente podrá restaurarse mientras el Administrador lo autorice.

---

# 59. Regla de Modularidad

Cada Motor del ERP deberá funcionar independientemente.

Si uno falla, los demás continuarán operando.

---

# 60. Regla Final

Todo desarrollo futuro deberá respetar las reglas contenidas en este documento.

Estas reglas constituyen el comportamiento oficial del modelo de datos de FACT CENTRAL.
