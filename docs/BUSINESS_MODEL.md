# BUSINESS MODEL
# FACT CENTRAL

## Modelo de Negocio Oficial del ERP

Versión 2.0

---

# 1. Propósito

FACT CENTRAL es un ERP inteligente orientado al control comercial,
documental, fiscal y económico de las operaciones realizadas para
EMPRESAS RECEPTORAS o CLIENTES.

La razón principal de existencia del sistema es:

> PROTEGER, CONTROLAR Y MANTENER ORGANIZADA LA INFORMACIÓN
> FISCAL Y DOCUMENTAL DE CADA CLIENTE/RECEPTOR.

FACT CENTRAL recibirá información digital desde diferentes canales,
la procesará automáticamente, la convertirá en datos estructurados,
la relacionará con cada operación y construirá Expedientes Digitales.

El sistema deberá mostrar en tiempo real cuánto compra cada Cliente,
cuánto emite cada Emisor, cuánto produce cada Usuario y Gestor,
qué documentos sustentan cada operación y qué obligaciones
documentales siguen pendientes.

---

# 2. Centro del modelo de negocio

El centro de FACT CENTRAL es:

CLIENTE / RECEPTOR

Ejemplos actuales:

- FISHO
- FRUTTI
- JANROS
- TIMANA
- CAVIAPETS
- DEL MAR
- FPA
- HERNANDEZ
- HERVER
- MAIK FISHING
- MAREUF EIRL
- PORCELLUS
- REQUE
- SAMARITANO
- SEÑOR MILAGROS
- YATAMURI
- YATDIZ
- BORISO
- LATINO
- MUSA
- TECNOLOGICOS

La lista deberá ser ampliable sin modificar el código.

Todo Pedido, Distribución, Factura, Expediente, Bancarización,
Detracción, Pago y Reporte deberá poder relacionarse finalmente
con uno o más Clientes/Receptores según la operación.

---

# 3. Cadena principal del negocio

El flujo comercial oficial será:

CLIENTE / RECEPTOR
        ↓
OBJETIVO DE COMPRA
        ↓
PEDIDO
        ↓
DISTRIBUCIÓN
        ↓
USUARIO
        ↓
GESTOR
        ↓
EMISORA / PROVEEDORA
        ↓
EJECUCIÓN
        ↓
DOCUMENTACIÓN DIGITAL
        ↓
EXPEDIENTE
        ↓
CONTROL EN TIEMPO REAL

---

# 4. Objetivo de compra del Cliente

Administración podrá establecer para cada Cliente y periodo:

- monto objetivo;
- monto máximo;
- pedidos adicionales;
- monto asignado;
- monto ejecutado;
- saldo pendiente;
- alertas de exceso.

Ejemplo:

FRUTTI
Periodo: Julio 2026
Objetivo: S/ 150,000

El sistema deberá conocer permanentemente:

OBJETIVO
ASIGNADO
EJECUTADO
PENDIENTE
PORCENTAJE DE AVANCE

---

# 5. Pedido

El Pedido representa la necesidad económica que debe cubrirse
para un Cliente/Receptor durante un periodo determinado.

Un Cliente podrá tener:

- un pedido;
- varios pedidos;
- ampliaciones;
- reducciones;
- reprogramaciones.

Los pedidos deberán conservar historial.

---

# 6. Distribución

El Pedido se distribuirá entre Usuarios.

Ejemplo:

FRUTTI
S/ 150,000

WILLI01   → S/ 60,000
JAVIER01  → S/ 40,000
JOSE01    → S/ 25,000
MAGO01    → S/ 25,000

El sistema deberá impedir que una distribución sea confundida
con producción real.

Se manejarán por separado:

- monto objetivo;
- monto asignado;
- monto ejecutado.

---

# 7. Usuarios

Los códigos actuales:

- EDUARDO01
- JOSE01
- MARIO01
- JAVIER01
- LUIS01
- MAGO01
- WILLI01
- VITUCHO01

representan USUARIOS.

NO representan Gestores.

Cada Usuario podrá tener:

- uno o varios Gestores;
- una o varias Empresas Emisoras/Proveedoras;
- asignaciones;
- producción;
- pagos;
- límites;
- reportes.

---

# 8. Gestores

Los Gestores dependen de un Usuario.

Jerarquía:

ADMINISTRADOR
    ↓
USUARIO
    ↓
GESTOR

El Gestor será responsable de proporcionar información y
documentación al sistema mediante los canales autorizados.

Podrá:

- subir documentos;
- enviar información;
- revisar observaciones;
- consultar su producción;
- consultar su asignación;
- consultar saldo disponible.

El Gestor no deberá alterar información consolidada fuera de
sus permisos.

---

# 9. Empresas Emisoras / Proveedoras

Cada Usuario podrá tener múltiples Empresas Emisoras.

Ejemplos:

WILLI01
    ↓
LABERTEC S.A.C.
otras emisoras asociadas

LUIS01
    ↓
LUIS AREVALO HERRERA
NEXOMAR NEGOCIOS EIRL

Las Emisoras suministran documentos comerciales a los
Clientes/Receptores.

El sistema deberá controlar por Emisor:

- monto emitido;
- cantidad de comprobantes;
- Clientes atendidos;
- concentración por Cliente;
- límites;
- periodos;
- disponibilidad futura.

La regla de rotación periódica podrá configurarse posteriormente
en el Motor de Distribución.

---

# 10. Canales de entrada

FACT CENTRAL recibirá información desde tres canales principales:

1. Gestor de archivos / carga masiva.
2. WhatsApp.
3. Correo electrónico.

Todos los canales deberán alimentar el mismo Motor de Ingesta.

El sistema deberá aceptar información desordenada.

El Gestor NO tendrá que clasificar previamente los archivos.

---

# 11. Tipos de información digital

FACT CENTRAL administrará información DIGITAL.

Podrá recibir:

- Facturas PDF.
- RHE.
- Guías de Remisión.
- Vouchers.
- Comprobantes de Retención.
- Constancias de Detracción.
- Cotizaciones.
- Órdenes de Compra.
- Requerimientos.
- Correos.
- Adjuntos.
- Imágenes.
- Fotografías.
- Evidencias de transporte.
- Evidencias de entrega.
- Evidencias provenientes de WhatsApp.
- Otros documentos relacionados.

Los documentos físicos, cuando existan, permanecen fuera del ERP
bajo custodia de sus propietarios.

FACT CENTRAL administra únicamente su representación y evidencia digital.

---

# 12. Procesamiento

Toda información recibida deberá pasar por un flujo común:

RECEPCIÓN
    ↓
IDENTIFICACIÓN
    ↓
EXTRACCIÓN
    ↓
VALIDACIÓN
    ↓
CONTROL DE DUPLICADOS
    ↓
REGISTRO EN BASE DE DATOS
    ↓
RELACIÓN DOCUMENTAL
    ↓
EXPEDIENTE
    ↓
CÁLCULOS
    ↓
DASHBOARD

---

# 13. Control de duplicados

Una misma Factura podrá recibirse varias veces:

- por carga masiva;
- por WhatsApp;
- por correo;
- como PDF;
- como imagen;
- como fotografía.

Pero:

> UNA FACTURA FISCAL SOLO PODRÁ PRODUCIR UN REGISTRO ECONÓMICO.

Una segunda recepción no deberá volver a incrementar:

- compras del Cliente;
- producción del Usuario;
- producción del Gestor;
- monto del Emisor;
- cantidad de Facturas;
- comisión;
- pago.

El sistema podrá conservar trazabilidad de las diferentes recepciones,
pero no duplicará el efecto económico.

---

# 14. Expediente Digital

El Expediente es la unidad documental que demuestra y relaciona
una operación realizada para un Cliente/Receptor.

La Factura será normalmente el eje económico principal del Expediente.

Un Expediente podrá contener:

- Factura;
- RHE;
- Guía Remitente;
- Guía Transportista;
- Voucher;
- Retención;
- Detracción;
- Cotización;
- Orden de Compra;
- Requerimiento;
- Correo;
- WhatsApp;
- Fotografías;
- Evidencias de transporte;
- Evidencias de entrega;
- Observaciones;
- otros sustentos.

Los documentos podrán llegar antes o después de la Factura.

Cuando todavía no exista suficiente información para relacionarlos,
permanecerán como:

PENDIENTE DE ASOCIACIÓN

hasta que FACT CENTRAL pueda asociarlos correctamente.

---

# 15. Relación entre Base de Datos y Documentos

PostgreSQL almacenará la información estructurada.

El repositorio documental almacenará las evidencias digitales.

La unión se realizará mediante identificadores lógicos como:

document_id
expediente_id
storage_key
checksum

La identidad del documento no dependerá de una carpeta física
ni de una letra de disco.

---

# 16. Control Comercial en tiempo real

Cada Factura válida deberá actualizar automáticamente:

CLIENTE / RECEPTOR
→ monto comprado.

EMISOR
→ monto emitido.

USUARIO
→ producción.

GESTOR
→ ejecución de su asignación.

PEDIDO
→ avance y saldo.

REGISTROS
→ cantidad de comprobantes válidos.

PAGOS
→ producción computable.

DASHBOARD
→ indicadores en tiempo real.

---

# 17. Límites

FACT CENTRAL permitirá establecer límites para:

- Cliente/Receptor;
- Pedido;
- Usuario;
- Gestor;
- Emisor;
- relación Emisor → Receptor.

El sistema podrá generar alertas antes de superar los límites.

Ejemplo:

NORMAL
ATENCIÓN
CERCA DEL LÍMITE
LÍMITE ALCANZADO
EXCEDIDO

---

# 18. Bancarización

Regla operativa actual:

> Toda Factura superior a S/ 1,999.99 deberá ser controlada como
> operación que requiere bancarización y deberá contar con Voucher.

Por tanto:

Factura ≤ S/ 1,999.99
→ no exige Voucher por esta regla.

Factura > S/ 1,999.99
→ requiere Voucher.

Estados posibles:

NO REQUIERE
PENDIENTE DE BANCARIZACIÓN
BANCARIZADA
OBSERVADA

El umbral deberá mantenerse como parámetro administrativo configurable.

---

# 19. Detracción

El sistema deberá identificar si una operación:

- está sujeta a detracción;
- no está sujeta;
- está pendiente de determinar;
- tiene constancia;
- está pendiente de constancia.

La detracción deberá relacionarse con:

- Factura;
- Expediente;
- Usuario;
- Cliente;
- pago generado.

---

# 20. Motor de Pagos

Los Usuarios reciben pago de acuerdo con su producción válida.

El cálculo podrá considerar:

- monto producido;
- Facturas válidas;
- con detracción;
- sin detracción;
- porcentaje aplicable;
- adelantos;
- ajustes;
- pagos realizados;
- saldo pendiente.

Una Factura duplicada nunca podrá generar doble pago.

La distribución del pago entre cuentas bancarias del Usuario
será configurable.

---

# 21. Dashboard

El Dashboard deberá mostrar información en tiempo real.

## Por Cliente/Receptor

- objetivo;
- asignado;
- comprado;
- pendiente;
- porcentaje de avance;
- bancarizado;
- no bancarizado;
- con detracción;
- sin detracción;
- expedientes completos;
- expedientes pendientes.

## Por Usuario

- asignación;
- producción;
- saldo;
- cantidad de registros;
- Gestores;
- Emisoras;
- pago generado.

## Por Gestor

- asignado;
- ejecutado;
- saldo;
- documentos enviados;
- observaciones.

## Por Emisor

- monto emitido;
- cantidad de Facturas;
- Clientes;
- concentración;
- límites.

---

# 22. Administrador

El Administrador tendrá visión global del sistema.

Podrá visualizar:

- todos los Clientes;
- todos los Usuarios;
- todos los Gestores;
- todas las Emisoras;
- todos los Expedientes;
- toda la producción;
- pagos;
- límites;
- auditoría;
- configuración.

Las modificaciones sensibles estarán restringidas a sus permisos.

---

# 23. Secretaría

Secretaría podrá visualizar globalmente la información necesaria
para supervisión.

Como regla general:

> Secretaría podrá VER la información consolidada pero NO modificarla,
> salvo permisos específicos que Administración habilite posteriormente.

---

# 24. Inteligencia Artificial y NEXUS

NEXUS NO será la fuente de verdad económica.

La fuente de verdad será la base de datos de FACT CENTRAL.

NEXUS utilizará esa información para:

- analizar;
- detectar anomalías;
- predecir;
- alertar;
- recomendar;
- ayudar a distribuir;
- detectar concentración;
- detectar faltantes;
- supervisar infraestructura.

Ejemplos:

"FRUTTI está al 91 % de su objetivo."

"WILLI01 tiene S/ 32,000 pendientes."

"Existen Facturas superiores a S/ 1,999.99 sin Voucher."

"Un Emisor está concentrando demasiado volumen en un solo Receptor."

---

# 25. Almacenamiento y replicación

Después de integrar un documento al sistema, su evidencia digital
podrá mantenerse en múltiples nodos.

FACT CENTRAL deberá conocer dónde existen copias disponibles.

Si una ubicación no está disponible, podrá obtener el documento
desde otra copia válida.

La replicación protege disponibilidad.

Los backups protegen recuperación histórica.

---

# 26. Principios fundamentales

1. El Cliente/Receptor es el centro comercial del ERP.

2. El Expediente es el centro documental de una operación.

3. El Usuario está por encima del Gestor.

4. Las Emisoras están relacionadas con los Usuarios.

5. La información puede llegar desordenada.

6. Ordenarla es responsabilidad de FACT CENTRAL.

7. Una Factura válida solo produce un impacto económico.

8. Todo cálculo debe actualizarse en tiempo real.

9. La Base de Datos es la fuente de verdad estructurada.

10. NEXUS analiza y recomienda sobre datos reales del ERP.

11. La información digital debe permanecer localizable,
    relacionada y auditable.

---

# 27. Algoritmo de negocio resumido

PLANIFICAR
Cliente → Pedido

DISTRIBUIR
Pedido → Usuario → Gestor → Emisor

RECIBIR
Web / WhatsApp / Correo

ORGANIZAR
Identificar → Extraer → Validar → No duplicar

RELACIONAR
Factura → Expediente → Evidencias

CONTROLAR
Compras → Producción → Límites → Bancarización
→ Detracción → Pagos

PROTEGER
Almacenar → Replicar → Recuperar

SUPERVISAR
Dashboard → NEXUS

---

# 28. Regla Suprema

> FACT CENTRAL EXISTE PARA PROTEGER Y CONTROLAR LA OPERACIÓN
> COMERCIAL, FISCAL Y DOCUMENTAL DEL CLIENTE/RECEPTOR.

El Expediente será la evidencia digital organizada que demuestra
cada operación y permite localizar, auditar y reconstruir
la información que la sustenta.
