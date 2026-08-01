# FACT CENTRAL SaaS

## CICLO DE VIDA DEL TENANT

Versión 1.0

---

# 1. Objetivo

Definir el ciclo de vida completo de cada espacio de trabajo
contratado dentro de FACT CENTRAL SaaS.

El Tenant representa el espacio independiente administrado
por un Administrador suscrito.

El Tenant NO representa:

- una empresa receptora;
- una empresa proveedora;
- un Cliente;
- un Usuario;
- un Gestor.

El Tenant representa todo el universo de trabajo de un Administrador.

---

# 2. Definición oficial

TENANT
=
ESPACIO DE TRABAJO INDEPENDIENTE
ASOCIADO A UN ADMINISTRADOR PROPIETARIO.

Dentro del Tenant podrán existir:

- múltiples Clientes/Receptores;
- múltiples Proveedores/Emisores;
- múltiples Usuarios;
- múltiples Gestores;
- uno o más Gerentes;
- una o más Secretarías;
- documentos;
- expedientes;
- pedidos;
- pagos;
- alertas;
- configuraciones.

---

# 3. Identidad del Tenant

Cada Tenant tendrá una identidad interna única.

Ejemplo:

tenant_id interno:

FC-01J8R7K5W3X9

El identificador:

- no será secuencial públicamente;
- no podrá ser elegido por el usuario;
- no podrá modificarse;
- acompañará a toda información del Tenant;
- será generado automáticamente por FACT CENTRAL.

Toda entidad operativa deberá relacionarse con un tenant_id.

Ejemplos:

tenant_id + cliente_id
tenant_id + proveedor_id
tenant_id + usuario_id
tenant_id + documento_id
tenant_id + expediente_id
tenant_id + pago_id

---

# 4. Registro público

La página pública ofrecerá:

INICIAR SESIÓN

PROBAR FACT CENTRAL

CREAR ESPACIO DE TRABAJO

La persona que seleccione crear un espacio se registrará inicialmente
como ADMINISTRADOR PROPIETARIO.

---

# 5. Datos obligatorios de registro

El Administrador deberá proporcionar:

- nombres y apellidos;
- tipo y número de documento;
- correo electrónico;
- número de celular;
- número de WhatsApp;
- país;
- contraseña;
- aceptación de términos;
- aceptación de política de privacidad.

Opcionalmente podrá registrar:

- RUC;
- razón social;
- nombre comercial;
- dirección;
- datos de facturación.

---

# 6. Verificación de identidad y contacto

El registro deberá verificar obligatoriamente:

## Correo electrónico

Se enviará un código temporal.

Estado:

PENDIENTE
VERIFICADO
VENCIDO
BLOQUEADO

## Número celular

Se enviará un código por SMS cuando el servicio esté disponible.

## WhatsApp

Podrá enviarse un código mediante integración oficial.

Correo y celular serán los canales principales.

WhatsApp será un canal adicional verificado.

---

# 7. Creación del Tenant

Cuando el Administrador complete las verificaciones requeridas,
FACT CENTRAL generará automáticamente:

- tenant_id;
- Administrador propietario;
- espacio lógico de almacenamiento;
- configuración inicial;
- plan de prueba;
- límites iniciales;
- auditoría de creación;
- claves y relaciones internas;
- subdominio o URL lógica opcional.

Ejemplo visible:

https://app.factcentral.pe/w/FC-A7K92M

La URL pública no revelará necesariamente el tenant_id interno real.

---

# 8. Estado inicial

Todo Tenant nuevo comenzará en estado:

TRIAL_ACTIVE

Durante la prueba podrá utilizar las funciones permitidas por el plan.

Ejemplo configurable:

Prueba gratuita:
15 días

Los días de prueba deberán ser configurables desde Superadmin.

---

# 9. Estados oficiales del Tenant

Los estados serán:

## REGISTRATION_PENDING

Registro incompleto.

## VERIFICATION_PENDING

Falta verificar correo, celular u otro requisito.

## TRIAL_ACTIVE

Prueba gratuita activa.

## ACTIVE

Suscripción pagada y operativa.

## PAYMENT_PENDING

Pago pendiente de confirmación.

## GRACE_PERIOD

Periodo de gracia posterior al vencimiento.

## SUSPENDED

Acceso operativo suspendido.

## READ_ONLY

Solo consulta y descarga, sin nuevas cargas ni modificaciones.

## CANCELLED

Suscripción cancelada.

## DELETION_PENDING

Eliminación solicitada y en periodo de espera.

## ARCHIVED

Información archivada según política aplicable.

## DELETED

Tenant eliminado según proceso autorizado.

---

# 10. Entrada al espacio vacío

Una vez creado, el Administrador verá:

CLIENTES                    0
PROVEEDORES                 0
USUARIOS                    0
GESTORES                    0
DOCUMENTOS                  0
EXPEDIENTES                 0
PEDIDOS                     0
ALERTAS                     0

El sistema podrá mostrar un asistente inicial:

1. Configurar datos generales.
2. Crear o importar Clientes.
3. Invitar Usuarios.
4. Invitar Gerente.
5. Invitar Secretaría.
6. Configurar reglas.
7. Comenzar carga documental.

---

# 11. Invitaciones

El Administrador podrá invitar:

- Gerente;
- Secretaría;
- Usuario.

El Usuario podrá invitar:

- Gestores asociados a sí mismo.

Cada invitación contendrá internamente:

- tenant_id;
- rol autorizado;
- usuario superior cuando corresponda;
- fecha de creación;
- fecha de expiración;
- token único;
- estado.

La invitación no deberá permitir cambiar libremente de Tenant ni de rol.

---

# 12. Uso de múltiples roles

Una misma persona podrá tener más de un rol.

Ejemplo:

Luis Arévalo:

ADMINISTRADOR
USUARIO

Pero cada sesión operativa deberá tener un contexto de rol activo.

Ejemplo:

INGRESAR COMO:

ADMINISTRADOR

USUARIO

Toda acción deberá registrar:

- persona;
- tenant;
- rol utilizado;
- fecha;
- hora;
- dispositivo;
- dirección IP;
- acción realizada.

---

# 13. Regla del Administrador

El Administrador administra.

No será un canal operativo de carga documental.

Si desea cargar documentos:

- deberá tener también rol Usuario;
- deberá cambiar al contexto Usuario;
- la acción quedará registrada bajo ese rol.

---

# 14. Inicio de suscripción

Antes de vencer la prueba, FACT CENTRAL deberá mostrar:

- días restantes;
- plan actual;
- límites;
- opciones de pago;
- fecha de vencimiento.

El Administrador podrá elegir un plan.

---

# 15. Planes

Los planes podrán limitar:

- cantidad de Usuarios;
- cantidad de Gestores;
- documentos por mes;
- almacenamiento;
- OCR;
- IA;
- integraciones;
- historial;
- soporte;
- número de Clientes;
- número de Proveedores;
- funcionalidades especiales.

Los planes deberán ser configurables desde Superadmin.

---

# 16. Pagos de suscripción

FACT CENTRAL podrá integrar diferentes pasarelas.

Estados de pago:

CREATED
PENDING
CONFIRMED
FAILED
EXPIRED
REFUNDED
CANCELLED

Medios posibles:

- tarjeta de crédito;
- tarjeta de débito;
- transferencia;
- billeteras autorizadas;
- PayPal;
- otros proveedores.

No se deberá construir la lógica de cada medio dentro del ERP.

Se utilizará una capa de pasarela intercambiable.

---

# 17. Vencimiento

Cuando llegue la fecha de vencimiento:

Si el pago está confirmado:

ACTIVE

Si no está confirmado:

GRACE_PERIOD

Durante el periodo de gracia podrá permitirse:

- consulta;
- carga limitada;
- pago;
- exportación;
- acceso administrativo.

La duración será configurable.

---

# 18. Suspensión

Al terminar el periodo de gracia sin pago:

SUSPENDED

Durante suspensión:

- no se reciben nuevos documentos;
- no se ejecutan nuevos procesos;
- no se generan nuevas asignaciones;
- no se permite modificar información;
- se conserva la información;
- se permite renovar la suscripción;
- se permite solicitar exportación según política.

La suspensión no elimina información.

---

# 19. Modo de solo lectura

Superadmin podrá establecer temporalmente:

READ_ONLY

El Tenant podrá:

- iniciar sesión;
- consultar información;
- buscar expedientes;
- descargar documentos;
- revisar reportes.

No podrá:

- cargar;
- modificar;
- eliminar;
- generar nuevas operaciones.

---

# 20. Reactivación

Cuando se confirme el pago:

SUSPENDED
→
ACTIVE

El sistema deberá:

- restablecer permisos;
- reactivar procesamiento;
- reactivar integraciones;
- conservar historial;
- registrar el evento;
- notificar al Administrador.

La reactivación no crea un nuevo Tenant.

---

# 21. Cancelación voluntaria

El Administrador podrá cancelar la renovación.

Estado:

CANCELLED

La cancelación podrá significar:

- no renovación futura;
- acceso hasta el fin del periodo pagado;
- posterior transición a READ_ONLY o SUSPENDED.

Cancelar no significa eliminar inmediatamente la información.

---

# 22. Exportación total

El Administrador propietario podrá solicitar:

EXPORTACIÓN COMPLETA

La exportación podrá incluir:

- Clientes;
- Proveedores;
- Usuarios autorizados;
- documentos;
- expedientes;
- productos;
- pedidos;
- alertas;
- pagos;
- auditoría;
- metadatos;
- archivos digitales.

Formatos posibles:

- ZIP;
- CSV;
- JSON;
- PDF;
- estructura de carpetas normalizada.

---

# 23. Solicitud de eliminación

La eliminación no será inmediata.

Flujo:

SOLICITUD
↓
CONFIRMACIÓN REFORZADA
↓
DELETION_PENDING
↓
PERIODO DE ESPERA
↓
ÚLTIMA EXPORTACIÓN OPCIONAL
↓
ELIMINACIÓN AUTORIZADA

Para confirmar se podrá exigir:

- contraseña;
- código por correo;
- código por celular;
- MFA;
- aceptación expresa.

---

# 24. Conservación y eliminación

La eliminación deberá respetar:

- obligaciones legales;
- políticas de retención;
- contratos;
- copias de seguridad;
- auditorías;
- periodos de gracia;
- obligaciones de protección de datos.

La eliminación de producción no deberá implicar
borrado inmediato de backups históricos.

Los backups seguirán su propia política de expiración.

---

# 25. Aislamiento

En todos los estados del Tenant se mantendrá:

- aislamiento lógico;
- aislamiento de almacenamiento;
- aislamiento de permisos;
- aislamiento de consultas;
- aislamiento de auditoría.

Ningún Tenant podrá ver información de otro.

---

# 26. Seguridad

Todo acceso deberá validar:

- tenant_id;
- identidad;
- rol;
- permiso;
- relación;
- estado del Tenant;
- estado de la suscripción.

Un Tenant suspendido no podrá evadir restricciones
utilizando una API directa.

---

# 27. Auditoría

Se registrarán, entre otros:

- creación;
- verificación;
- cambios de plan;
- pagos;
- vencimientos;
- suspensión;
- reactivación;
- invitaciones;
- cambios de roles;
- exportaciones;
- solicitudes de eliminación;
- cancelaciones;
- accesos administrativos.

---

# 28. Notificaciones

El Administrador recibirá avisos sobre:

- creación del Tenant;
- fin próximo de prueba;
- vencimiento;
- pago confirmado;
- pago fallido;
- periodo de gracia;
- suspensión;
- reactivación;
- cambios de plan;
- exportaciones;
- eliminación solicitada.

Canales:

- FACT CENTRAL;
- correo;
- SMS;
- WhatsApp según configuración.

---

# 29. Regla de continuidad

La suspensión, cancelación o caída de un servidor
no deberá eliminar ni corromper el Tenant.

La información deberá mantenerse protegida mediante:

- replicación;
- backups;
- almacenamiento redundante;
- restauración verificable.

---

# 30. Regla Suprema

UN TENANT ES UN ESPACIO DE TRABAJO INDEPENDIENTE
CONTRATADO Y ADMINISTRADO POR UN ADMINISTRADOR PROPIETARIO.

Dentro del Tenant pueden existir múltiples empresas,
Clientes, Proveedores, Usuarios, Gestores y Expedientes.

La información de un Tenant nunca podrá mezclarse
ni ser visible desde otro Tenant.
