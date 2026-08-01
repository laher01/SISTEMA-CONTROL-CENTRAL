# 03_IDENTITY_AND_ACCESS_MODEL.md

# FACT CENTRAL SaaS

## IDENTITY AND ACCESS MODEL

Versión 1.0

---

# 1. Objetivo

Definir el modelo oficial de identidad, autenticación, membresía,
roles y acceso de FACT CENTRAL SaaS.

Este documento establece:

- cómo se registra una persona;
- cómo se verifica su identidad;
- cómo se relaciona con un Tenant;
- cómo recibe uno o varios roles;
- cómo cambia de contexto operativo;
- cómo se autoriza cada acción;
- cómo se bloquea un acceso;
- cómo se audita toda actividad.

---

# 2. Principio fundamental

FACT CENTRAL separará los siguientes conceptos:

PERSONA

CUENTA DE ACCESO

TENANT

MEMBRESÍA

ROL

PERMISO

SESIÓN

Una persona no será creada nuevamente por cada función que desempeñe.

Existirá una identidad principal y podrá recibir diferentes
membresías y roles autorizados.

---

# 3. Persona

PERSONA representa al ser humano identificado dentro de FACT CENTRAL.

Datos posibles:

- nombres;
- apellidos;
- tipo de documento;
- número de documento;
- país;
- fecha de nacimiento, cuando corresponda;
- fotografía de perfil opcional;
- estado de identidad.

La Persona no determina por sí sola qué puede hacer.

Los permisos se obtienen mediante:

PERSONA
↓
MEMBRESÍA EN TENANT
↓
ROL
↓
PERMISOS

---

# 4. Cuenta de acceso

La Cuenta de Acceso contendrá:

- correo principal;
- celular principal;
- WhatsApp;
- contraseña protegida;
- métodos MFA;
- dispositivos conocidos;
- sesiones activas;
- fecha del último acceso;
- estado de seguridad.

La contraseña nunca deberá almacenarse en texto plano.

---

# 5. Identidad global y membresía por Tenant

Una Persona podrá utilizar una sola identidad de acceso y,
cuando sea autorizado, pertenecer a uno o varios Tenants.

Ejemplo:

Luis Arévalo
│
├── Tenant FC-A7K92M
│   ├── Administrador
│   └── Usuario
│
└── Tenant FC-P4N81X
    └── Usuario

Cada relación con un Tenant será una MEMBRESÍA independiente.

Los permisos de un Tenant nunca se trasladarán automáticamente a otro.

---

# 6. Membresía

La Membresía relacionará:

- persona_id;
- tenant_id;
- estado;
- fecha de ingreso;
- forma de incorporación;
- persona que invitó;
- fecha de activación;
- fecha de suspensión;
- roles asignados.

Estados:

INVITED

REGISTRATION_PENDING

VERIFICATION_PENDING

PENDING_APPROVAL

ACTIVE

SUSPENDED

REVOKED

EXPIRED

---

# 7. Roles oficiales iniciales

FACT CENTRAL tendrá los siguientes roles base:

- SUPERADMIN;
- ADMINISTRADOR;
- GERENTE;
- SECRETARÍA;
- USUARIO;
- GESTOR.

Los roles base no deberán confundirse con cargos legales
o laborales externos.

Representan funciones y permisos dentro de FACT CENTRAL.

---

# 8. Superadmin

SUPERADMIN pertenece a la plataforma FACT CENTRAL SaaS.

No pertenece al organigrama interno de un Tenant.

Puede:

- administrar Tenants;
- administrar planes;
- administrar suscripciones;
- supervisar infraestructura;
- suspender o reactivar espacios;
- revisar seguridad;
- gestionar incidencias de plataforma.

No deberá utilizarse para operar documentos empresariales.

El acceso Superadmin deberá exigir seguridad reforzada.

---

# 9. Administrador

El Administrador controla su Tenant.

Puede:

- configurar el Tenant;
- aprobar altas;
- invitar Gerentes;
- invitar Secretarías;
- invitar Usuarios;
- asignar roles;
- configurar Clientes;
- configurar reglas;
- configurar pedidos;
- configurar porcentajes;
- configurar planes de liquidación;
- revisar alertas;
- aprobar operaciones;
- ver auditoría;
- administrar permisos autorizados.

Regla:

> El Administrador administra, pero no es un canal operativo
> de carga documental.

Si desea subir documentos deberá poseer también el rol Usuario
y cambiar expresamente a ese contexto.

---

# 10. Gerente

El Gerente tendrá una vista ejecutiva y económica.

Podrá:

- ver totales generales;
- consultar Clientes;
- consultar Proveedores;
- filtrar por mes, trimestre, semestre y año;
- abrir el detalle Cliente → Proveedores;
- abrir el detalle Proveedor → Clientes;
- consultar resúmenes económicos;
- consultar pagos preparados;
- ver cuentas habilitadas para pago;
- adjuntar vouchers;
- registrar pagos parciales;
- marcar pagos ejecutados;
- revisar diferencias de conciliación.

No podrá:

- modificar fórmulas;
- modificar porcentajes;
- modificar planes de liquidación;
- crear Usuarios;
- cambiar cuentas registradas por los Usuarios;
- alterar montos preparados por Administración;
- acceder a configuración de plataforma.

---

# 11. Secretaría

Secretaría trabaja sobre la información documental y operativa.

Podrá:

- ver Clientes;
- ver Proveedores;
- ver CPE;
- ver Guías;
- ver Vouchers documentales;
- ver expedientes;
- revisar productos y servicios;
- validar documentación;
- identificar inconsistencias;
- crear alertas;
- adjuntar observaciones;
- solicitar correcciones;
- verificar el estado documental.

No podrá ver:

- Usuarios;
- Gestores;
- Gerente;
- estructura interna de asignaciones;
- comisiones;
- cuentas de pago;
- planes de liquidación;
- fórmulas;
- módulo de Pagos;
- configuración de roles.

Secretaría podrá generar una alerta relacionada con un documento.

FACT CENTRAL determinará internamente el Usuario y Gestor
que deben recibirla, sin revelar esa estructura a Secretaría.

---

# 12. Usuario

El Usuario depende del Tenant y puede tener uno o varios Gestores.

Podrá:

- subir documentos;
- revisar sus documentos;
- revisar sus expedientes autorizados;
- consultar su producción;
- consultar su liquidación;
- ver porcentajes visibles autorizados;
- ver adelantos;
- ver saldo;
- consultar sus alertas;
- registrar sus cuentas de pago;
- editar sus cuentas de pago;
- activar o desactivar sus propias cuentas;
- definir montos o distribución entre cuentas;
- invitar Gestores;
- administrar sus Gestores;
- consultar sus Proveedores/Emisores asociados.

No podrá:

- modificar fórmulas internas;
- modificar porcentajes de comisión;
- alterar liquidaciones cerradas;
- ver producción de otros Usuarios;
- acceder a cuentas de otros Usuarios;
- modificar reglas generales del Tenant.

---

# 13. Gestor

El Gestor depende de un Usuario.

Podrá:

- subir documentos;
- revisar los documentos que haya suministrado;
- ver sus asignaciones;
- ver su producción operativa;
- consultar saldos de asignación;
- revisar alertas relacionadas;
- responder observaciones;
- corregir o volver a subir evidencia cuando tenga permiso.

No podrá:

- ver liquidaciones del Usuario;
- ver comisiones;
- ver cuentas bancarias;
- ver el módulo de Pagos;
- administrar otros Gestores;
- ver información de otros Usuarios;
- modificar reglas.

---

# 14. Una persona con múltiples roles

Una Persona podrá tener varios roles dentro del mismo Tenant.

Ejemplo:

Luis Arévalo

- Administrador;
- Usuario.

Al iniciar sesión deberá seleccionar el contexto:

INGRESAR COMO:

[ ADMINISTRADOR ]

[ USUARIO ]

El sistema activará únicamente los permisos del rol seleccionado.

Cuando Luis ingrese como Usuario:

- podrá subir documentos;
- podrá ver su producción;
- no podrá modificar porcentajes;
- no podrá utilizar permisos administrativos.

Cuando ingrese como Administrador:

- podrá configurar el Tenant;
- no podrá cargar documentos como si fuera Usuario.

---

# 15. Cambio de rol activo

El cambio de rol deberá realizarse mediante una acción explícita.

Ejemplo:

CAMBIAR CONTEXTO

Administrador
→
Usuario

El cambio deberá:

- cerrar el contexto anterior;
- emitir un nuevo contexto autorizado;
- registrar el evento;
- actualizar permisos;
- conservar la misma identidad;
- impedir la combinación simultánea de permisos.

---

# 16. Regla de no acumulación de privilegios

Los permisos de varios roles no se sumarán silenciosamente
durante una operación.

La sesión tendrá un único rol operativo activo.

Ejemplo:

Una persona con rol Administrador y Usuario que ingrese como Usuario
no podrá ejecutar acciones administrativas utilizando la misma sesión.

---

# 17. Registro del Administrador propietario

El primer registro público crea:

- Persona;
- Cuenta de acceso;
- Tenant;
- Membresía;
- rol Administrador Propietario;
- periodo de prueba;
- auditoría inicial.

El Administrador deberá verificar los medios obligatorios
antes de activar plenamente el Tenant.

---

# 18. Invitaciones

El Administrador podrá invitar:

- Gerente;
- Secretaría;
- Usuario.

El Usuario podrá invitar:

- Gestor asociado a sí mismo.

Una invitación contendrá:

- tenant_id;
- rol ofrecido;
- usuario_padre_id, si corresponde;
- token único;
- correo o celular invitado;
- fecha de creación;
- fecha de expiración;
- estado;
- persona que invitó.

---

# 19. Enlaces de invitación

Ejemplo conceptual:

https://app.factcentral.pe/invite/7YK9-QP4X-...

El enlace deberá ser:

- único;
- temporal;
- no predecible;
- revocable;
- de un solo uso;
- asociado a un Tenant;
- asociado a un rol específico.

El invitado no podrá cambiar el rol ni el Tenant contenidos
en la invitación.

---

# 20. Alta mediante invitación

Flujo:

INVITACIÓN
↓
REGISTRO DE PERSONA
↓
VERIFICACIÓN DE CORREO
↓
VERIFICACIÓN DE CELULAR
↓
VERIFICACIÓN DE WHATSAPP, SI APLICA
↓
ACEPTACIÓN DE TÉRMINOS
↓
PENDIENTE DE APROBACIÓN
↓
ACTIVACIÓN
↓
ACCESO AL TENANT

El sistema deberá mostrar:

A LA ESPERA DEL ALTA CORRESPONDIENTE

hasta que el responsable apruebe.

---

# 21. Responsables de alta

El Administrador aprobará:

- Gerente;
- Secretaría;
- Usuario.

El Usuario aprobará:

- sus Gestores.

El Administrador podrá revocar o intervenir en cualquier
membresía dentro de su Tenant.

---

# 22. Datos obligatorios del registro

Toda persona deberá registrar:

- nombres;
- apellidos;
- documento;
- correo;
- celular;
- contraseña;
- país;
- aceptación de términos.

Según el rol, podrán solicitarse:

- WhatsApp;
- dirección;
- datos laborales;
- código interno;
- observaciones.

Correo y celular serán obligatorios.

---

# 23. Verificación de correo

FACT CENTRAL enviará un código temporal.

Ejemplo:

483921

Características:

- un solo uso;
- duración limitada;
- número máximo de intentos;
- bloqueo temporal por abuso;
- registro de envío;
- registro de verificación.

---

# 24. Verificación de celular

Se enviará un código mediante SMS cuando la integración esté habilitada.

El número se normalizará con:

- país;
- prefijo internacional;
- número;
- estado de verificación.

---

# 25. Verificación de WhatsApp

Podrá utilizarse una integración oficial de WhatsApp Business.

WhatsApp será un canal adicional.

No reemplazará obligatoriamente al correo o celular salvo
configuración expresa de seguridad.

---

# 26. Autenticación

FACT CENTRAL deberá permitir autenticación segura mediante:

- correo y contraseña;
- MFA;
- código temporal;
- recuperación segura;
- dispositivos confiables, cuando corresponda.

La autenticación no será suficiente para autorizar una acción.

Después de autenticar, el sistema deberá validar:

- Tenant;
- membresía;
- rol activo;
- permisos;
- estado de la cuenta;
- estado del Tenant.

---

# 27. MFA

El segundo factor será obligatorio para:

- Superadmin;
- Administrador;
- Gerente.

Podrá ser obligatorio para otros roles según el plan o configuración.

Métodos posibles:

- aplicación autenticadora;
- correo;
- SMS;
- llave de seguridad;
- passkey;
- otros mecanismos autorizados.

Para privilegios altos se preferirán mecanismos más resistentes
que SMS.

---

# 28. Acciones sensibles

Las siguientes acciones podrán exigir verificación reforzada:

- cambiar contraseña;
- cambiar correo;
- cambiar celular;
- cambiar WhatsApp;
- desactivar MFA;
- agregar Administrador;
- cambiar porcentajes;
- cambiar planes de liquidación;
- modificar cuentas bancarias;
- cerrar pagos;
- reabrir periodos;
- exportar toda la información;
- solicitar eliminación del Tenant.

---

# 29. Sesión

Toda sesión deberá registrar:

- session_id;
- persona_id;
- tenant_id;
- membresía;
- rol activo;
- fecha de inicio;
- última actividad;
- dispositivo;
- navegador;
- dirección IP;
- ubicación aproximada cuando sea legalmente permitido;
- fecha de expiración.

---

# 30. Duración de sesión

La duración será configurable según nivel de riesgo.

Ejemplo:

Superadmin
→ sesión corta.

Administrador
→ sesión controlada.

Usuario/Gestor
→ sesión operativa.

Una sesión inactiva deberá expirar.

---

# 31. Revocación de sesiones

Una Persona podrá cerrar:

- sesión actual;
- otras sesiones;
- todos los dispositivos.

Administración podrá revocar las sesiones de miembros de su Tenant.

Superadmin podrá revocar sesiones por incidentes de seguridad.

---

# 32. Cambio de credenciales

Cuando se cambie:

- contraseña;
- correo;
- celular;
- MFA;

el sistema podrá:

- revocar sesiones activas;
- notificar al propietario;
- exigir nueva autenticación;
- registrar el evento.

---

# 33. Autorización por acciones

FACT CENTRAL no autorizará únicamente por pantalla.

Cada operación tendrá un permiso específico.

Ejemplos:

tenant.user.invite

tenant.user.approve

document.upload

document.view

document.validate

expedient.view

expedient.alert.create

payment.account.create

payment.account.edit

payment.execute

payment.voucher.upload

commission.rule.view

commission.rule.edit

audit.view

---

# 34. Regla del Backend

Ocultar un botón en el Frontend no representa seguridad.

El Backend validará cada solicitud.

Aunque una persona llame directamente a una API:

- sin permiso;
- con otro Tenant;
- con otro rol;
- con membresía suspendida;

la operación deberá ser rechazada.

---

# 35. Roles personalizados

En una fase posterior, el Administrador podrá crear roles personalizados.

Ejemplo:

SUPERVISOR DOCUMENTAL

Permisos:

- ver expedientes;
- revisar documentos;
- crear alertas;
- no modificar pagos;
- no ver Usuarios;
- no administrar Tenant.

Los roles personalizados no podrán otorgar permisos superiores
a los que el Administrador tenga derecho a delegar.

---

# 36. Principio de mínimo privilegio

Toda persona recibirá únicamente los permisos necesarios
para realizar su función.

Por defecto:

DENEGAR

La autorización deberá ser explícita.

---

# 37. Restricción por relación

Además del rol, se validará la relación con los datos.

Ejemplo:

Un Gestor puede tener permiso:

document.view

pero solamente podrá ver documentos:

- de su Tenant;
- asociados a su Usuario;
- relacionados con su ámbito;
- autorizados por las reglas aplicables.

---

# 38. Restricción por estado

Una acción podrá negarse cuando:

- la Persona esté suspendida;
- la Membresía esté pendiente;
- el Tenant esté suspendido;
- la suscripción esté vencida;
- el periodo esté cerrado;
- el registro esté bloqueado;
- exista una medida de seguridad.

---

# 39. Cuentas bancarias del Usuario

Las cuentas de pago serán responsabilidad del Usuario.

El Usuario podrá:

- registrarlas;
- editarlas;
- activarlas;
- desactivarlas;
- indicar montos;
- indicar porcentajes.

El Administrador podrá verlas y supervisarlas.

El Gerente verá únicamente las cuentas activas y preparadas
para el pago correspondiente.

El Gestor y Secretaría no tendrán acceso.

---

# 40. Congelamiento de cuentas para un pago

Cuando Administración cierre una programación de pago,
FACT CENTRAL generará una fotografía lógica de:

- titular;
- banco;
- cuenta;
- CCI;
- monto;
- distribución.

Los cambios posteriores realizados por el Usuario no modificarán
silenciosamente la programación ya cerrada.

---

# 41. Alertas creadas por Secretaría

Secretaría podrá crear una alerta desde:

- Factura;
- Guía;
- Voucher;
- Expediente;
- evidencia;
- producto;
- inconsistencia.

FACT CENTRAL resolverá internamente:

PROVEEDOR
↓
USUARIO
↓
GESTOR

La alerta podrá enviarse a:

- Administrador;
- Usuario;
- Gestor relacionado.

Secretaría no necesitará ver la identidad interna
del Usuario o Gestor para generar la alerta.

---

# 42. Canales de notificación

Las notificaciones podrán enviarse por:

- bandeja interna;
- correo;
- SMS;
- WhatsApp.

La bandeja interna será obligatoria.

Los canales externos serán complementarios.

---

# 43. Protección frente a abuso

FACT CENTRAL aplicará controles como:

- límites de intentos;
- rate limiting;
- bloqueo temporal;
- detección de fuerza bruta;
- detección de sesiones anómalas;
- alertas por acceso desconocido;
- verificación reforzada;
- revocación de tokens.

---

# 44. Recuperación de acceso

La recuperación deberá requerir canales previamente verificados.

No deberá permitir:

- cambiar contraseña solo con datos públicos;
- utilizar invitaciones vencidas;
- omitir MFA en cuentas privilegiadas;
- recuperar acceso mediante un correo no confirmado.

---

# 45. Suspensión de persona o membresía

Se podrá suspender:

- la Cuenta completa de una Persona;
- una Membresía concreta;
- un rol específico;
- todas las sesiones.

Ejemplo:

Una Persona puede ser suspendida en Tenant A
y permanecer activa en Tenant B.

---

# 46. Separación entre eliminación y revocación

Eliminar una Persona no será la primera opción.

Normalmente se utilizará:

REVOKED

La información histórica conservará:

- quién subió el documento;
- quién creó la alerta;
- quién realizó el pago;
- quién modificó el registro.

La trazabilidad no deberá romperse.

---

# 47. Auditoría

Toda acción relevante deberá registrar:

- tenant_id;
- persona_id;
- membresía;
- rol activo;
- permiso utilizado;
- recurso;
- acción;
- fecha;
- hora;
- IP;
- dispositivo;
- resultado;
- motivo de denegación cuando corresponda.

---

# 48. Privacidad

Cada Persona solo visualizará los datos personales necesarios
para su función.

Los datos sensibles estarán restringidos.

Las cuentas bancarias deberán protegerse con permisos específicos.

---

# 49. Regla de aislamiento

Ninguna identidad, membresía o sesión podrá cambiar de Tenant
modificando una URL, parámetro o petición.

El Tenant autorizado será determinado por el contexto seguro
de la sesión y validado por el Backend y PostgreSQL.

---

# 50. Flujo general

PERSONA
↓
CUENTA VERIFICADA
↓
INVITACIÓN O CREACIÓN DE TENANT
↓
MEMBRESÍA
↓
APROBACIÓN
↓
ROL ASIGNADO
↓
INICIO DE SESIÓN
↓
SELECCIÓN DE TENANT
↓
SELECCIÓN DE ROL
↓
PERMISOS
↓
OPERACIÓN
↓
AUDITORÍA

---

# 51. Reglas supremas

## Regla Suprema 1

UNA PERSONA TIENE UNA IDENTIDAD PRINCIPAL.

## Regla Suprema 2

LOS DERECHOS NACEN DE SU MEMBRESÍA Y ROL DENTRO DE UN TENANT.

## Regla Suprema 3

UNA SESIÓN OPERA CON UN SOLO ROL ACTIVO.

## Regla Suprema 4

LOS PERMISOS NO SE SUMAN SILENCIOSAMENTE.

## Regla Suprema 5

EL ADMINISTRADOR ADMINISTRA; PARA CARGAR DOCUMENTOS DEBE ACTUAR COMO USUARIO.

## Regla Suprema 6

SECRETARÍA NO VE USUARIOS, GESTORES NI PAGOS.

## Regla Suprema 7

EL GESTOR NO VE COMISIONES NI CUENTAS DE PAGO.

## Regla Suprema 8

EL USUARIO ADMINISTRA SUS PROPIAS CUENTAS DE PAGO.

## Regla Suprema 9

TODA ACCIÓN SERÁ AUTORIZADA EN EL BACKEND Y AUDITADA.

## Regla Suprema 10

NINGUNA PERSONA PODRÁ ACCEDER A DATOS DE OTRO TENANT
POR CAMBIO DE URL, API, IDENTIFICADOR O ARCHIVO.
