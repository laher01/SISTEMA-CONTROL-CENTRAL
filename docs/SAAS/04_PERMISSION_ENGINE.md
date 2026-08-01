# 04_PERMISSION_ENGINE.md

# FACT CENTRAL SaaS

## PERMISSION ENGINE

Versión 1.0

---

# 1. Objetivo

Definir el motor oficial de autorización y permisos de FACT CENTRAL SaaS.

Este documento establece:

- cómo se crean los permisos;
- cómo se asignan a Roles;
- cómo se validan las acciones;
- cómo se restringen por Tenant;
- cómo se restringen por relación;
- cómo se restringen por estado;
- cómo se registran las denegaciones;
- cómo se evita la acumulación indebida de privilegios.

El Motor de Permisos deberá ser utilizado por:

- Frontend;
- Backend;
- APIs;
- Workers;
- NEXUS;
- exportaciones;
- integraciones;
- almacenamiento;
- notificaciones;
- procesos programados.

---

# 2. Principio fundamental

Toda acción estará:

DENEGADA POR DEFECTO.

Una acción solamente podrá ejecutarse cuando exista:

- identidad autenticada;
- Tenant válido;
- membresía activa;
- rol activo;
- permiso explícito;
- relación válida con el recurso;
- estado compatible;
- suscripción habilitada;
- contexto de seguridad válido.

---

# 3. Fórmula oficial de autorización

Una operación será permitida solamente cuando se cumpla:

AUTORIZACIÓN
=
IDENTIDAD VÁLIDA
+
TENANT VÁLIDO
+
MEMBRESÍA ACTIVA
+
ROL ACTIVO
+
PERMISO EXPLÍCITO
+
RELACIÓN CON EL RECURSO
+
ESTADO PERMITIDO
+
CONDICIONES DE SEGURIDAD

Si falta cualquiera de los componentes:

ACCESO DENEGADO.

---

# 4. Permiso

Un Permiso representa una acción concreta que puede ejecutarse
sobre un recurso.

Ejemplos:

document.upload

document.view

document.edit

document.validate

expedient.view

expedient.alert.create

tenant.user.invite

payment.execute

commission.rule.edit

audit.view

Los permisos deberán ser:

- únicos;
- descriptivos;
- estables;
- versionables;
- auditables;
- independientes del nombre visual de las pantallas.

---

# 5. Estructura del nombre de permiso

Formato oficial:

DOMINIO.RECURSO.ACCIÓN

Ejemplos:

tenant.member.invite

tenant.member.approve

client.view

client.create

supplier.view

document.upload

document.validate

expedient.close

payment.account.edit

payment.execute

alert.create

audit.view

subscription.manage

---

# 6. Acciones estándar

Las acciones base serán:

VIEW

LIST

SEARCH

CREATE

UPLOAD

EDIT

VALIDATE

APPROVE

REJECT

CLOSE

REOPEN

DELETE_LOGICAL

EXPORT

DOWNLOAD

EXECUTE

ASSIGN

INVITE

SUSPEND

REACTIVATE

CONFIGURE

MANAGE

Las acciones deberán traducirse internamente a permisos específicos.

---

# 7. Alcance del permiso

Un permiso no define por sí solo todo el alcance.

Ejemplo:

document.view

deberá combinarse con:

- Tenant;
- Usuario;
- Gestor;
- Cliente;
- Proveedor;
- Expediente;
- rol activo;
- relación autorizada.

Por tanto:

PERMISO
+
ALCANCE
=
AUTORIZACIÓN REAL.

---

# 8. Alcances oficiales

Los alcances posibles serán:

## SELF

Solo recursos propios.

## OWN_RELATIONSHIP

Recursos relacionados directamente con la Persona.

## OWN_USER

Recursos pertenecientes al Usuario.

## OWN_GESTORS

Recursos pertenecientes a Gestores del Usuario.

## TENANT_OPERATIONAL

Recursos operativos autorizados del Tenant.

## TENANT_FULL

Todos los recursos del Tenant.

## PLATFORM

Recursos de la plataforma SaaS.

---

# 9. Regla del Tenant

Todo permiso empresarial estará limitado al Tenant activo.

Nunca se autorizará una operación solamente por:

- document_id;
- client_id;
- supplier_id;
- expedient_id;
- payment_id.

Siempre deberá comprobarse:

tenant_id del recurso
=
tenant_id de la sesión.

---

# 10. Regla del rol activo

Una sesión tendrá un solo rol operativo activo.

Los permisos de otros roles asignados a la Persona no se acumularán
mientras opere con un rol diferente.

Ejemplo:

Luis tiene:

- Administrador;
- Usuario.

Ingresa como Usuario.

Entonces:

- puede cargar documentos;
- puede ver su producción;
- no puede editar porcentajes;
- no puede administrar miembros;
- no puede usar permisos de Administrador.

---

# 11. Roles oficiales

Los roles base serán:

- SUPERADMIN;
- ADMINISTRADOR;
- GERENTE;
- SECRETARÍA;
- USUARIO;
- GESTOR.

Los permisos base estarán definidos por este documento.

---

# 12. Superadmin

El Superadmin tendrá alcance:

PLATFORM

Podrá:

- administrar Tenants;
- administrar planes;
- administrar suscripciones;
- suspender Tenants;
- reactivar Tenants;
- revisar infraestructura;
- revisar seguridad;
- consultar auditoría de plataforma;
- intervenir en incidencias autorizadas.

No utilizará permisos operativos normales del ERP.

No deberá:

- cargar facturas;
- modificar expedientes empresariales;
- ejecutar pagos de un Tenant;
- modificar producción empresarial;
- operar como Usuario o Gestor.

---

# 13. Administrador

El Administrador tendrá alcance:

TENANT_FULL

Podrá:

- ver todo su Tenant;
- configurar reglas;
- crear y aprobar miembros;
- configurar Clientes;
- configurar Proveedores;
- configurar pedidos;
- configurar porcentajes;
- configurar planes de liquidación;
- revisar alertas;
- aprobar operaciones;
- cerrar periodos;
- consultar auditoría;
- administrar permisos autorizados;
- exportar información;
- configurar integraciones;
- gestionar suscripción.

No podrá cargar documentos mientras opere como Administrador.

Para cargar documentos deberá cambiar al rol Usuario.

---

# 14. Gerente

El Gerente tendrá alcance:

TENANT_EXECUTIVE

Podrá:

- ver Dashboard Gerencial;
- ver Clientes;
- ver Proveedores;
- ver totales;
- filtrar por periodo;
- revisar pagos preparados;
- ver cuentas habilitadas;
- adjuntar vouchers de pago;
- registrar pagos parciales;
- marcar pagos ejecutados;
- consultar conciliaciones;
- consultar reportes autorizados.

No podrá:

- modificar porcentajes;
- modificar fórmulas;
- modificar planes de liquidación;
- modificar cuentas de los Usuarios;
- crear Usuarios;
- acceder al módulo de configuración;
- acceder a datos de otros Tenants.

---

# 15. Secretaría

Secretaría tendrá alcance:

TENANT_OPERATIONAL_DOCUMENTAL

Podrá:

- ver Clientes;
- ver Proveedores;
- ver CPE;
- ver Guías;
- ver Vouchers documentales;
- ver expedientes;
- revisar productos;
- revisar servicios;
- validar documentos;
- crear alertas;
- adjuntar observaciones;
- solicitar correcciones;
- revisar evidencias;
- cambiar estados documentales autorizados.

No podrá:

- ver Usuarios;
- ver Gestores;
- ver Gerente;
- ver comisiones;
- ver cuentas de pago;
- ver porcentajes internos;
- ver fórmulas;
- acceder al módulo de Pagos;
- modificar reglas del Tenant;
- administrar roles.

---

# 16. Usuario

El Usuario tendrá alcance:

OWN_USER

Podrá:

- subir documentos;
- revisar sus documentos;
- consultar sus expedientes;
- consultar sus Proveedores;
- consultar sus Gestores;
- consultar su producción;
- consultar su liquidación;
- ver porcentajes visibles autorizados;
- ver adelantos;
- ver saldos;
- registrar cuentas de pago;
- editar cuentas propias;
- activar o desactivar cuentas propias;
- definir distribución de sus cuentas;
- invitar Gestores;
- aprobar Gestores propios;
- responder alertas;
- corregir documentación propia.

No podrá:

- ver información de otros Usuarios;
- modificar fórmulas;
- modificar porcentajes;
- alterar liquidaciones cerradas;
- modificar reglas generales;
- ejecutar pagos;
- acceder a auditoría completa.

---

# 17. Gestor

El Gestor tendrá alcance:

OWN_RELATIONSHIP

Podrá:

- subir documentos;
- revisar documentos propios;
- consultar asignaciones;
- consultar producción operativa;
- consultar saldos de asignación;
- ver alertas relacionadas;
- responder observaciones;
- volver a subir evidencias;
- corregir información autorizada.

No podrá:

- ver liquidaciones;
- ver comisiones;
- ver cuentas bancarias;
- ver pagos;
- administrar otros Gestores;
- ver documentos de otros Usuarios;
- modificar reglas;
- ver auditoría general.

---

# 18. Matriz general de permisos

| Módulo / Acción | Superadmin | Administrador | Gerente | Secretaría | Usuario | Gestor |
|---|---:|---:|---:|---:|---:|---:|
| Ver plataforma SaaS | Sí | No | No | No | No | No |
| Administrar Tenant | Sí | Sí, propio | No | No | No | No |
| Ver Clientes | No operativo | Sí | Sí | Sí | Según relación | Según relación |
| Crear Clientes | No operativo | Sí | No | No | No | No |
| Editar Clientes | No operativo | Sí | No | No | No | No |
| Ver Proveedores | No operativo | Sí | Sí | Sí | Propios | Relacionados |
| Crear Proveedor automático | Sistema | Sí validar | No | No | No | No |
| Subir documentos | No | No | No | No | Sí | Sí |
| Ver documentos | No operativo | Sí | Limitado | Sí | Propios | Propios |
| Validar documentos | No | Sí | No | Sí | Limitado | No |
| Crear alerta documental | No | Sí | No | Sí | Sí, propia | Sí, propia |
| Ver expedientes | No operativo | Sí | Autorizados | Sí | Propios | Relacionados |
| Cerrar expediente | No | Sí | No | Según permiso | No | No |
| Ver producción | No | Sí | General | Totales autorizados | Propia | Propia |
| Ver liquidación | No | Sí | Resumen autorizado | No | Propia | No |
| Editar porcentajes | No | Sí | No | No | No | No |
| Editar fórmula | No | Sí | No | No | No | No |
| Registrar cuentas de pago | No | Ver | No | No | Sí | No |
| Editar cuentas de pago | No | Supervisar | No | No | Sí | No |
| Ejecutar pago | No | Preparar / aprobar | Sí | No | No | No |
| Adjuntar voucher de pago | No | Sí | Sí | No | No | No |
| Ver auditoría | Plataforma | Sí | Limitada | No | Propia | Propia limitada |
| Exportar Tenant completo | Soporte autorizado | Sí | No | No | No | No |
| Invitar Gerente | No | Sí | No | No | No | No |
| Invitar Secretaría | No | Sí | No | No | No | No |
| Invitar Usuario | No | Sí | No | No | No | No |
| Invitar Gestor | No | Intervenir | No | No | Sí | No |
| Aprobar Gestor | No | Intervenir | No | No | Sí | No |

---

# 19. Permisos del dominio Tenant

## Administrador

tenant.view

tenant.configure

tenant.member.list

tenant.member.invite

tenant.member.approve

tenant.member.suspend

tenant.member.revoke

tenant.role.assign

tenant.settings.edit

tenant.export.request

tenant.audit.view

## Superadmin

platform.tenant.list

platform.tenant.create

platform.tenant.suspend

platform.tenant.reactivate

platform.tenant.plan.change

platform.tenant.security.review

---

# 20. Permisos del dominio Clientes

client.list

client.search

client.view

client.create

client.edit

client.activate

client.deactivate

client.import

client.export

client.order.configure

client.limit.configure

Administrador:

todos dentro de su Tenant.

Gerente:

list, search, view, export autorizado.

Secretaría:

list, search, view.

Usuario:

view limitado a relaciones autorizadas.

Gestor:

view limitado a asignaciones relacionadas.

---

# 21. Permisos del dominio Proveedores

supplier.list

supplier.search

supplier.view

supplier.create

supplier.edit

supplier.activate

supplier.deactivate

supplier.compliance.view

supplier.compliance.edit

supplier.rotation.view

supplier.rotation.configure

supplier.assignment.view

supplier.assignment.configure

Administrador:

todos.

Gerente:

list, search, view.

Secretaría:

list, search, view documental.

Usuario:

view de Proveedores propios.

Gestor:

view de Proveedores relacionados.

---

# 22. Permisos del dominio Documentos

document.list

document.search

document.upload

document.view

document.download

document.edit_metadata

document.classify

document.validate

document.observe

document.reject

document.reprocess

document.link

document.unlink

document.export

document.delete_logical

Reglas:

Administrador no utiliza document.upload en rol Administrador.

Usuario y Gestor pueden usar document.upload.

Secretaría puede validar, observar y solicitar corrección.

El Gestor no puede eliminar registros consolidados.

---

# 23. Permisos del dominio Expedientes

expedient.list

expedient.search

expedient.view

expedient.create

expedient.link_document

expedient.observe

expedient.validate

expedient.close

expedient.reopen

expedient.export

expedient.timeline.view

Administrador:

todos.

Secretaría:

list, search, view, observe, validate y cerrar
solo cuando tenga permiso específico.

Usuario:

view y responder sobre Expedientes propios.

Gestor:

view limitado y responder observaciones.

Gerente:

view autorizado cuando sea necesario.

---

# 24. Permisos del dominio Pedidos

order.list

order.view

order.create

order.edit

order.close

order.reopen

order.amount.configure

order.distribution.generate

order.distribution.edit

order.distribution.approve

order.rebalance

order.alert.view

Administrador:

todos.

Gerente:

view.

Usuario:

view de asignaciones propias.

Gestor:

view de asignaciones propias.

Secretaría:

sin acceso a distribución interna.

---

# 25. Permisos del dominio Productos

product.list

product.search

product.view

product.normalize

product.merge

product.split

product.report.view

product.inventory.view

Administrador:

todos.

Secretaría:

list, search, view y reportes autorizados.

Gerente:

reportes generales.

Usuario:

productos relacionados.

Gestor:

productos de documentos propios.

---

# 26. Permisos del dominio Cumplimiento

compliance.ssco.view

compliance.ssco.upload

compliance.ssco.validate

compliance.itf.view

compliance.itf.upload

compliance.pdt.view

compliance.pdt.upload

compliance.status.change

compliance.alert.create

Administrador:

todos.

Secretaría:

view, validate y crear alertas.

Usuario:

subir ITF/PDT propios o de Proveedores autorizados.

Gestor:

sin acceso salvo permiso específico.

Gerente:

view ejecutivo.

---

# 27. Permisos del dominio Liquidaciones

commission.liquidation.list

commission.liquidation.view

commission.liquidation.close

commission.liquidation.reopen

commission.rule.list

commission.rule.view

commission.rule.create

commission.rule.edit

commission.rule.activate

commission.rule.deactivate

commission.advance.create

commission.adjustment.create

Administrador:

todos.

Usuario:

ver únicamente su liquidación y porcentajes visibles.

Gerente:

ver resumen autorizado, sin fórmula.

Secretaría:

sin acceso.

Gestor:

sin acceso.

---

# 28. Permisos del dominio Cuentas de Pago

payment.account.list

payment.account.view

payment.account.create

payment.account.edit

payment.account.activate

payment.account.deactivate

payment.account.distribution.edit

payment.account.freeze

Usuario:

administra únicamente sus propias cuentas.

Administrador:

ve y supervisa.

Gerente:

ve únicamente las cuentas activas incluidas
en una programación cerrada.

Secretaría y Gestor:

sin acceso.

---

# 29. Permisos del dominio Pagos

payment.batch.list

payment.batch.view

payment.batch.prepare

payment.batch.approve

payment.execute

payment.partial.execute

payment.voucher.upload

payment.voucher.view

payment.reconcile

payment.close

payment.reopen

Administrador:

prepara, aprueba, revisa y cierra.

Gerente:

ve, ejecuta, adjunta Voucher y concilia.

Usuario:

ve estado de su liquidación y pago.

Secretaría y Gestor:

sin acceso.

---

# 30. Permisos del dominio Alertas

alert.list

alert.view

alert.create

alert.assign

alert.respond

alert.resolve

alert.close

alert.reopen

alert.escalate

Secretaría:

crea alertas documentales.

Usuario:

ve y responde alertas relacionadas.

Gestor:

ve y responde alertas relacionadas.

Administrador:

ve, asigna, escala y cierra.

Gerente:

ve alertas ejecutivas autorizadas.

---

# 31. Permisos del dominio Auditoría

audit.self.view

audit.resource.view

audit.tenant.view

audit.platform.view

Gestor:

audit.self.view limitado.

Usuario:

audit.self.view y audit.resource.view propio.

Administrador:

audit.tenant.view.

Superadmin:

audit.platform.view.

Secretaría y Gerente:

solo auditoría específica cuando sea autorizada.

---

# 32. Restricción por propiedad

Un permiso puede existir, pero el recurso deberá estar dentro
del alcance autorizado.

Ejemplo:

Usuario tiene:

document.view

Pero solamente podrá ver:

document.tenant_id = sesión.tenant_id

y

document.usuario_id = sesión.usuario_id

o

document.gestor.usuario_id = sesión.usuario_id

según la regla autorizada.

---

# 33. Restricción por Gestor

El Gestor podrá consultar solamente documentos:

- subidos por él;
- asignados a él;
- relacionados con sus operaciones;
- habilitados por el Usuario.

No podrá utilizar filtros para descubrir documentos de otros Gestores.

---

# 34. Restricción por Cliente y Proveedor

Un Usuario o Gestor no obtendrá acceso global a un Cliente
solo porque uno de sus documentos lo mencione.

El acceso deberá limitarse a:

- Expedientes relacionados;
- periodos autorizados;
- pedidos asignados;
- documentos propios;
- Proveedores relacionados.

---

# 35. Restricción por estado del Tenant

Si el Tenant está:

TRIAL_ACTIVE

se aplican límites del plan de prueba.

ACTIVE

operación normal.

GRACE_PERIOD

operación limitada según configuración.

READ_ONLY

solo view, search, list, download y export autorizado.

SUSPENDED

sin operaciones nuevas.

DELETION_PENDING

acceso restringido y exportación controlada.

---

# 36. Restricción por estado del periodo

Si un periodo está cerrado:

- no se modifican asignaciones;
- no se modifican porcentajes;
- no se modifican liquidaciones;
- no se modifican pagos cerrados;
- no se alteran registros consolidados.

Para reabrir se requerirá:

- permiso específico;
- motivo;
- auditoría;
- autorización reforzada.

---

# 37. Restricción por estado documental

Un Documento podrá estar:

RECEIVED

PROCESSING

PROCESSED

OBSERVED

VALIDATED

REJECTED

ARCHIVED

Cada estado limitará las acciones disponibles.

Ejemplo:

VALIDATED

no podrá editarse libremente.

REJECTED

podrá reemplazarse mediante una nueva versión.

---

# 38. Restricción por seguridad

Una acción podrá ser bloqueada por:

- sesión sospechosa;
- IP bloqueada;
- MFA pendiente;
- demasiados intentos;
- dispositivo no confiable;
- cambio reciente de credenciales;
- alerta crítica;
- incidente de seguridad;
- cuenta suspendida.

---

# 39. Permisos temporales

Podrán existir autorizaciones temporales.

Ejemplo:

Secretaría puede revisar un Expediente específico durante 48 horas.

Todo permiso temporal deberá registrar:

- quién lo otorgó;
- recurso;
- acciones;
- inicio;
- expiración;
- motivo.

---

# 40. Delegación

El Administrador podrá delegar permisos autorizados
sin perder el control del Tenant.

No podrá delegar permisos reservados a Superadmin.

Un Usuario no podrá delegar permisos administrativos a un Gestor.

---

# 41. Roles personalizados

En una fase posterior podrán crearse Roles personalizados.

Ejemplo:

SUPERVISOR DOCUMENTAL

Permisos:

- document.view;
- document.validate;
- expedient.view;
- alert.create.

No podrá recibir:

- commission.rule.edit;
- payment.execute;
- tenant.member.manage;

salvo autorización expresa del Administrador y políticas del sistema.

---

# 42. Plantillas de Roles

FACT CENTRAL podrá ofrecer plantillas:

- Administrador;
- Gerente;
- Secretaría;
- Usuario;
- Gestor;
- Supervisor documental;
- Auditor;
- Solo lectura.

El Administrador podrá duplicar una plantilla y ajustarla
dentro de los límites permitidos.

---

# 43. Evaluación de permisos

El Backend evaluará:

1. ¿La Persona está autenticada?
2. ¿La sesión está vigente?
3. ¿El Tenant coincide?
4. ¿La Membresía está activa?
5. ¿El rol activo es válido?
6. ¿El permiso existe?
7. ¿El permiso está asignado al rol?
8. ¿El recurso pertenece al Tenant?
9. ¿La Persona tiene relación con el recurso?
10. ¿El estado permite la acción?
11. ¿La suscripción permite la función?
12. ¿Las condiciones de seguridad son válidas?

Solo entonces ejecutará la operación.

---

# 44. Decisión del Motor

Resultados posibles:

ALLOW

DENY_NO_AUTHENTICATION

DENY_TENANT_MISMATCH

DENY_MEMBERSHIP_INACTIVE

DENY_ROLE_INVALID

DENY_PERMISSION_MISSING

DENY_SCOPE

DENY_RESOURCE_STATE

DENY_TENANT_STATE

DENY_SUBSCRIPTION

DENY_SECURITY_POLICY

DENY_RATE_LIMIT

---

# 45. Auditoría de denegaciones

Las denegaciones sensibles deberán registrarse.

Ejemplo:

Una Persona intenta acceder a un documento de otro Tenant.

Registrar:

- Persona;
- Tenant activo;
- recurso solicitado;
- Tenant real del recurso;
- IP;
- dispositivo;
- fecha;
- resultado;
- nivel de riesgo.

---

# 46. Frontend

El Frontend podrá ocultar o deshabilitar acciones
que la Persona no tenga autorizadas.

Pero esta función será únicamente de experiencia de usuario.

La seguridad real estará en el Backend.

---

# 47. APIs

Toda API deberá declarar:

- permiso requerido;
- alcance;
- estados permitidos;
- validaciones adicionales.

No existirán endpoints internos sin autorización explícita.

---

# 48. Workers

Los Workers deberán validar:

- Tenant del trabajo;
- servicio autorizado;
- alcance del proceso;
- identidad técnica;
- permiso de servicio.

Un Worker no utilizará permisos de Usuario.

Utilizará una identidad técnica limitada.

---

# 49. NEXUS

NEXUS no tendrá permisos universales.

Cada Agente tendrá:

- identidad técnica;
- Tenant;
- permisos mínimos;
- acciones autorizadas;
- límites;
- auditoría.

NEXUS podrá recomendar una acción sin necesariamente
tener permiso para ejecutarla.

---

# 50. Integraciones externas

Cada integración tendrá permisos específicos.

Ejemplo:

Gmail:

- email.read.authorized;
- email.attachment.import.

WhatsApp:

- message.receive;
- evidence.import;
- alert.send.

Las integraciones no recibirán acceso general al Tenant.

---

# 51. Almacenamiento

Para generar un enlace de archivo se deberá comprobar:

- Tenant;
- permiso de visualización;
- permiso de descarga;
- relación;
- vigencia;
- estado del documento.

Los enlaces serán temporales.

---

# 52. Exportaciones

Las exportaciones deberán validar:

- permiso;
- alcance;
- tamaño;
- datos sensibles;
- estado del Tenant;
- aprobación adicional cuando corresponda.

La exportación completa del Tenant será exclusiva
del Administrador Propietario o un proceso autorizado.

---

# 53. Protección de cuentas bancarias

Los datos bancarios tendrán permisos separados.

Ejemplo:

payment.account.view_full

payment.account.view_masked

payment.account.edit

Gerente podrá recibir solamente la información necesaria
para ejecutar el pago preparado.

Secretaría y Gestor no accederán a estos datos.

---

# 54. Enmascaramiento de datos

Cuando no sea necesario mostrar el dato completo:

Cuenta:

**** **** **** 6984

Correo:

lu***@dominio.com

Celular:

+51 *** *** 125

El permiso específico determinará si se muestra completo
o enmascarado.

---

# 55. Principio de separación de funciones

Las funciones sensibles deberán dividirse cuando sea posible.

Ejemplo:

Administrador:

- configura y aprueba el pago.

Gerente:

- ejecuta y adjunta el Voucher.

Esto reduce errores y abusos.

---

# 56. Acciones críticas

Se considerarán críticas:

- modificar porcentajes;
- modificar fórmula;
- cambiar cuenta bancaria;
- crear Administrador;
- ejecutar pago;
- reabrir periodo;
- exportar Tenant completo;
- eliminar información;
- suspender Tenant;
- cambiar rol privilegiado.

Podrán exigir:

- MFA;
- reautenticación;
- confirmación;
- motivo;
- auditoría;
- doble aprobación.

---

# 57. Regla de mínimo privilegio

Cada Rol recibirá únicamente lo indispensable.

El sistema no deberá otorgar permisos globales
por comodidad de implementación.

---

# 58. Regla de no confianza en el cliente

FACT CENTRAL nunca confiará en:

- parámetros enviados por el navegador;
- tenant_id indicado manualmente;
- rol enviado por el Frontend;
- identificadores de archivos;
- rutas solicitadas;
- permisos ocultos en pantalla.

Todo será recalculado y validado en el Backend.

---

# 59. Regla de consistencia

El mismo permiso deberá producir la misma decisión
en:

- Web;
- API;
- aplicación móvil;
- Worker;
- integración;
- exportación;
- visor documental.

---

# 60. Reglas supremas

## Regla Suprema 1

TODO ESTÁ DENEGADO POR DEFECTO.

## Regla Suprema 2

NINGÚN PERMISO OPERA FUERA DEL TENANT ACTIVO.

## Regla Suprema 3

UN PERMISO NO BASTA SIN UNA RELACIÓN VÁLIDA CON EL RECURSO.

## Regla Suprema 4

UNA SESIÓN UTILIZA UN SOLO ROL ACTIVO.

## Regla Suprema 5

OCULTAR UN BOTÓN NO REPRESENTA SEGURIDAD.

## Regla Suprema 6

EL BACKEND AUTORIZA CADA OPERACIÓN.

## Regla Suprema 7

SECRETARÍA NO ACCEDE A USUARIOS, GESTORES NI PAGOS.

## Regla Suprema 8

EL GESTOR NO ACCEDE A LIQUIDACIONES, COMISIONES NI CUENTAS.

## Regla Suprema 9

EL USUARIO ADMINISTRA ÚNICAMENTE SUS CUENTAS Y SU ÁMBITO.

## Regla Suprema 10

EL GERENTE EJECUTA PAGOS PREPARADOS, PERO NO MODIFICA SUS FÓRMULAS.

## Regla Suprema 11

EL ADMINISTRADOR ADMINISTRA SU TENANT, PERO NO CARGA DOCUMENTOS
MIENTRAS OPERA COMO ADMINISTRADOR.

## Regla Suprema 12

TODA DENEGACIÓN RELEVANTE SERÁ AUDITABLE.
