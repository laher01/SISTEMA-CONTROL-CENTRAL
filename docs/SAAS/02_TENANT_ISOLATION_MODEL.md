# 02_TENANT_ISOLATION_MODEL.md

# FACT CENTRAL SaaS

# TENANT ISOLATION MODEL

Versión 1.0

---

# 1. Objetivo

Definir el modelo oficial de aislamiento de información de FACT CENTRAL SaaS.

El objetivo principal es garantizar que la información perteneciente a un Tenant nunca pueda ser visualizada, modificada o utilizada por otro Tenant.

El aislamiento deberá mantenerse durante toda la vida útil del sistema.

---

# 2. Regla Suprema

Toda información pertenece a un único Tenant.

Ningún dato podrá existir sin estar asociado a un tenant_id.

Todo acceso deberá validar obligatoriamente:

- identidad;
- tenant;
- rol;
- permisos.

---

# 3. Definición

TENANT

=

ESPACIO DE TRABAJO INDEPENDIENTE

administrado por un Administrador Propietario.

No representa:

- Empresa
- Cliente
- Proveedor
- Usuario
- Gestor

Representa todo el universo operativo de un Administrador.

---

# 4. Identificador

Cada Tenant tendrá un identificador único.

Ejemplo:

FC-01J8R7K5W3X9

El tenant_id será:

- único
- permanente
- inmodificable
- no reutilizable
- generado automáticamente

---

# 5. Principio Universal

Todo objeto deberá pertenecer exactamente a un Tenant.

Ejemplos

Tenant

↓

Clientes

↓

Proveedores

↓

Usuarios

↓

Gestores

↓

Documentos

↓

Expedientes

↓

Pedidos

↓

Productos

↓

Alertas

↓

Pagos

↓

Auditoría

---

# 6. Toda tabla deberá contener tenant_id

Ejemplos

clientes

tenant_id

proveedores

tenant_id

usuarios

tenant_id

gestores

tenant_id

documentos

tenant_id

expedientes

tenant_id

pagos

tenant_id

productos

tenant_id

alertas

tenant_id

No existirán tablas operativas sin tenant_id.

---

# 7. Aislamiento en PostgreSQL

Toda consulta deberá filtrar por tenant_id.

Nunca deberá ejecutarse una consulta del tipo:

SELECT * FROM documentos

Siempre deberá existir:

tenant_id

+

permisos

+

rol

Ejemplo conceptual

Buscar documentos

↓

tenant_id = FC-XXXX

↓

usuario autorizado

↓

resultado

---

# 8. Aislamiento del Storage

Todos los archivos digitales pertenecerán únicamente a un Tenant.

Ejemplo lógico

Storage

├── FC-000001
├── FC-000002
├── FC-000003

Cada Tenant tendrá su espacio lógico independiente.

Los usuarios nunca accederán directamente al almacenamiento físico.

---

# 9. Organización del Storage

Ejemplo

FC-000001

↓

Clientes

↓

Expedientes

↓

Documentos

↓

Imágenes

↓

Vouchers

↓

Contratos

↓

Correos

↓

WhatsApp

↓

Evidencias

Esta organización es únicamente lógica.

La relación oficial estará almacenada en PostgreSQL.

---

# 10. Descargas

Ningún usuario descargará archivos directamente.

Toda descarga será autorizada por FACT CENTRAL.

Proceso

Usuario

↓

Solicita archivo

↓

Validación

tenant

↓

rol

↓

permisos

↓

Generar enlace temporal

↓

Descarga

Los enlaces deberán expirar automáticamente.

---

# 11. Subida de documentos

Antes de guardar un archivo el sistema ya conocerá:

tenant

usuario

gestor (si existe)

canal

fecha

hora

El archivo nunca podrá almacenarse fuera del Tenant correspondiente.

---

# 12. Gestores

Un Gestor solamente podrá visualizar:

- documentos propios
- expedientes autorizados
- asignaciones propias
- alertas propias

Nunca podrá visualizar documentos de:

otros Gestores

otros Usuarios

otros Tenants

---

# 13. Usuarios

Un Usuario podrá visualizar únicamente:

sus Gestores

sus Proveedores

sus documentos

sus expedientes

sus pedidos

sus pagos

No visualizará información perteneciente a otros Usuarios salvo autorización expresa.

---

# 14. Secretaría

Secretaría podrá consultar únicamente:

documentación

expedientes

observaciones

alertas

No podrá acceder a:

Usuarios

Gestores

Pagos

Configuraciones

---

# 15. Gerente

El Gerente visualizará únicamente la información autorizada por el Administrador.

Podrá acceder a:

Dashboard General

Pagos

Reportes

Expedientes autorizados

No podrá administrar la plataforma.

---

# 16. Administrador

El Administrador visualizará todo su Tenant.

Nunca visualizará otro Tenant.

Aunque existan miles de Tenants.

---

# 17. Superadmin

El Superadmin administra la plataforma.

No utilizará el sistema para operar documentos.

Podrá:

crear

suspender

reactivar

administrar planes

administrar infraestructura

No modificará información operativa salvo tareas administrativas autorizadas.

---

# 18. API

Toda API deberá validar:

tenant_id

rol

permisos

estado del Tenant

estado de suscripción

antes de ejecutar cualquier operación.

---

# 19. Caché

Redis nunca mezclará información entre Tenants.

Las claves deberán incorporar tenant_id.

Ejemplo

FC-000001:dashboard

FC-000001:cliente

FC-000002:dashboard

---

# 20. Workers

Todo Worker procesará únicamente trabajos pertenecientes al Tenant recibido.

Nunca podrá cambiar de Tenant durante la ejecución.

---

# 21. Colas

Las colas deberán registrar:

tenant

trabajo

prioridad

estado

fecha

Todos los procesos conservarán la pertenencia al Tenant.

---

# 22. OCR

OCR procesará únicamente documentos pertenecientes al Tenant que originó la solicitud.

---

# 23. IA

Los modelos IA nunca compartirán contexto entre Tenants.

Toda memoria utilizada por IA deberá pertenecer exclusivamente al Tenant activo.

---

# 24. Auditoría

Todas las acciones registrarán:

tenant

persona

rol

fecha

hora

IP

dispositivo

acción

resultado

---

# 25. Exportaciones

Toda exportación incluirá únicamente información perteneciente al Tenant solicitante.

Nunca se exportarán datos cruzados.

---

# 26. Backups

Los Backups podrán almacenarse físicamente juntos.

Pero deberán conservar aislamiento lógico.

Durante la restauración solamente podrá recuperarse el Tenant solicitado.

---

# 27. Búsquedas

Toda búsqueda incluirá automáticamente tenant_id.

Nunca existirán búsquedas globales para usuarios normales.

---

# 28. URLs

Las URLs nunca deberán permitir descubrir otros Tenants.

Los identificadores visibles serán independientes del tenant_id interno.

---

# 29. Seguridad

Si un atacante obtiene acceso a un Tenant:

No deberá poder visualizar:

otros Tenants

otras Bases

otros Documentos

otros Usuarios

La seguridad deberá impedir el movimiento lateral entre Tenants.

---

# 30. Escalabilidad

FACT CENTRAL deberá soportar:

10

100

1.000

10.000

100.000

Tenants

sin modificar el algoritmo de aislamiento.

Solo deberá crecer la infraestructura.

---

# 31. Regla Suprema

Toda información pertenece exactamente a un Tenant.

Todo acceso deberá validar:

tenant_id

rol

permisos

relación

estado del Tenant

Ninguna operación podrá ejecutarse sin verificar estas condiciones.

FACT CENTRAL garantizará que la información de un Tenant jamás pueda ser consultada, modificada o utilizada por otro Tenant, independientemente de la cantidad de usuarios, documentos, servidores o nodos que existan en la plataforma.
