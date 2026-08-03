# 01_RULE_ENGINE.md

# FACT CENTRAL SaaS

## RULE ENGINE — MOTOR CENTRAL DE REGLAS

Versión 1.0

---

# 1. Objetivo

Definir el Motor Central de Reglas de FACT CENTRAL.

El Rule Engine será responsable de evaluar y aplicar de manera:

- consistente;
- configurable;
- versionada;
- auditable;
- determinística;
- segura;
- multi-tenant;

las reglas que gobiernan el comportamiento del sistema.

El Rule Engine deberá evitar que las reglas del negocio queden
dispersas o repetidas dentro del código de:

- Backend;
- Frontend;
- Workers;
- NEXUS;
- expedientes;
- pagos;
- pedidos;
- alertas;
- cumplimiento;
- dashboards;
- suscripciones.

---

# 2. Principio fundamental

FACT CENTRAL es un sistema gobernado por reglas.

Ejemplos:

- si un CPE requiere bancarización, se solicitará Voucher;
- si un Cliente es agente de retención, se evaluará la constancia;
- si un Proveedor aparece en SSCO, se generará una alerta;
- si un Expediente está incompleto, no podrá cerrarse;
- si un Proveedor supera su monto asignado, se generará una alerta;
- si un CPE ya existe, no se contabilizará nuevamente;
- si cambia una tasa, la nueva regla se aplicará desde su vigencia;
- si una liquidación está cerrada, no se modificará silenciosamente.

Estas decisiones no deberán implementarse de manera aislada
en diferentes módulos.

Deberán ser evaluadas mediante un Motor Central de Reglas.

---

# 3. Regla oficial

Una Regla representa una condición evaluable que puede producir:

- una decisión;
- una clasificación;
- una obligación;
- una prohibición;
- una advertencia;
- una alerta;
- una acción propuesta;
- un cambio de estado;
- un cálculo;
- una solicitud de aprobación.

---

# 4. Fórmula conceptual

```text
EVENTO O SOLICITUD
        ↓
CONTEXTO
        ↓
REGLAS APLICABLES
        ↓
EVALUACIÓN DE CONDICIONES
        ↓
RESOLUCIÓN DE PRIORIDAD
        ↓
RESULTADO
        ↓
ACCIÓN / ALERTA / BLOQUEO / RECOMENDACIÓN
        ↓
AUDITORÍA
```

---

# 5. Fuente de verdad

El Rule Engine será la fuente oficial para las reglas configurables
del negocio.

No deberán existir múltiples versiones independientes
de una misma regla en:

- Frontend;
- Backend;
- Worker;
- NEXUS;
- hojas de cálculo;
- scripts auxiliares.

El Frontend podrá mostrar el resultado.

El Backend deberá ejecutar y validar la decisión oficial.

---

# 6. Tipos de reglas

Las reglas se clasificarán inicialmente en:

## 6.1 Reglas legales o tributarias

Derivadas de normas, disposiciones o criterios tributarios.

Ejemplos:

- bancarización;
- detracción;
- retención;
- documentación de sustento;
- conservación de registros;
- requisitos del CPE.

Estas reglas deberán tener:

- fuente normativa;
- vigencia;
- responsable de actualización;
- versión;
- jurisdicción;
- estado.

---

## 6.2 Reglas de plataforma

Aplican a FACT CENTRAL SaaS.

Ejemplos:

- límites del Plan;
- suspensión de Tenant;
- control de consumo;
- validación de membresía;
- aislamiento multi-tenant;
- restricciones de seguridad.

---

## 6.3 Reglas del Tenant

Son configuradas por el Administrador para su espacio de trabajo.

Ejemplos:

- límite de concentración;
- ventana de rotación;
- documentos exigidos;
- tolerancia de pedidos;
- reglas de aprobación;
- severidad de alertas.

---

## 6.4 Reglas comerciales

Gobiernan pedidos, distribución y producción.

Ejemplos:

- monto mensual por Cliente;
- reparto entre Usuarios;
- monto asignado por Proveedor;
- porcentaje bancarizado objetivo;
- concentración máxima;
- rotación Proveedor → Cliente.

---

## 6.5 Reglas documentales

Gobiernan documentos y Expedientes.

Ejemplos:

- documento obligatorio;
- documento condicional;
- evidencia recomendada;
- documento no aplicable;
- conflicto entre Factura y Guía;
- Expediente completo o incompleto.

---

## 6.6 Reglas de liquidación

Gobiernan comisiones y pagos ERP.

Ejemplos:

- fórmula estándar;
- fórmula especial;
- componentes de comisión;
- adelantos;
- ajustes;
- vigencias;
- distribución en cuentas.

---

## 6.7 Reglas de seguridad

Gobiernan accesos y operaciones sensibles.

Ejemplos:

- exigir MFA;
- bloquear sesión;
- limitar intentos;
- impedir acceso entre Tenants;
- exigir reautenticación;
- congelar una operación.

---

## 6.8 Reglas de infraestructura

Gobiernan capacidad y continuidad.

Ejemplos:

- escalar Workers;
- activar modo seguro;
- bloquear nuevas cargas;
- mover datos;
- emitir alerta por capacidad;
- solicitar aprobación administrativa.

---

# 7. Ámbito de una Regla

Una Regla podrá tener uno de los siguientes ámbitos:

## GLOBAL

Aplica a toda la plataforma.

## JURISDICTION

Aplica a un país o jurisdicción.

## PLATFORM

Aplica a la operación SaaS.

## PLAN

Aplica a determinados Planes.

## TENANT

Aplica a un Tenant.

## ROLE

Aplica a determinados roles.

## CLIENT

Aplica a un Cliente/Receptor.

## SUPPLIER

Aplica a un Proveedor/Emisor.

## USER

Aplica a un Usuario.

## DOCUMENT_TYPE

Aplica a un tipo documental.

## EXPEDIENT_TYPE

Aplica a un tipo de Expediente.

## PERIOD

Aplica a un periodo determinado.

---

# 8. Jerarquía de aplicación

Cuando varias reglas sean aplicables, se utilizará la siguiente
jerarquía general:

```text
SEGURIDAD Y AISLAMIENTO
        ↓
NORMA LEGAL VIGENTE
        ↓
REGLA GLOBAL DE PLATAFORMA
        ↓
REGLA DEL PLAN
        ↓
REGLA DEL TENANT
        ↓
REGLA ESPECÍFICA DEL RECURSO
        ↓
EXCEPCIÓN APROBADA
```

Una regla inferior no podrá anular una obligación superior
cuando ello comprometa:

- seguridad;
- aislamiento;
- integridad;
- cumplimiento legal;
- auditoría;
- conservación de datos.

---

# 9. Estructura de una Regla

Toda Regla deberá contener:

- rule_id;
- code;
- name;
- description;
- category;
- scope;
- tenant_id, cuando corresponda;
- jurisdiction;
- priority;
- conditions;
- actions;
- severity;
- version;
- effective_from;
- effective_to;
- status;
- source;
- created_by;
- approved_by;
- created_at;
- approved_at;
- reason;
- metadata.

---

# 10. Código de Regla

Cada Regla tendrá un código estable.

Formato conceptual:

```text
DOMINIO.SUBDOMINIO.REGLA
```

Ejemplos:

```text
DOCUMENT.DUPLICATE.CPE_IDENTITY
EXPEDIENT.BANKING.VOUCHER_REQUIRED
COMPLIANCE.SSCO.SUPPLIER_BLOCK
ORDER.CONCENTRATION.MAXIMUM
PAYMENT.LIQUIDATION.STANDARD
SECURITY.MFA.ADMIN_REQUIRED
SAAS.SUBSCRIPTION.UPLOAD_BLOCKED
```

El código no deberá cambiar aunque cambie el nombre visible.

---

# 11. Estado de una Regla

Los estados oficiales serán:

## DRAFT

Regla en preparación.

## UNDER_REVIEW

Regla pendiente de revisión.

## APPROVED

Regla aprobada, todavía sin vigencia.

## ACTIVE

Regla vigente.

## SUSPENDED

Regla temporalmente suspendida.

## REPLACED

Regla reemplazada por una nueva versión.

## EXPIRED

Regla cuya vigencia terminó.

## REJECTED

Regla rechazada.

## ARCHIVED

Regla conservada únicamente por historial.

---

# 12. Vigencia

Toda Regla deberá indicar:

- fecha y hora desde la que se aplica;
- fecha y hora hasta la que se aplica, cuando corresponda;
- zona horaria;
- versión vigente;
- motivo del cambio.

Una nueva Regla no deberá modificar resultados históricos.

Ejemplo:

```text
Regla versión 1
Vigencia:
01/07/2026 al 31/08/2026

Regla versión 2
Vigencia:
desde 01/09/2026
```

Las operaciones de julio y agosto conservarán la versión 1.

---

# 13. Versionado

Las reglas no deberán editarse destruyendo la versión anterior.

Flujo:

```text
REGLA V1 ACTIVA
        ↓
PROPUESTA DE CAMBIO
        ↓
REGLA V2 EN REVISIÓN
        ↓
APROBACIÓN
        ↓
V1 REPLACED
V2 ACTIVE
```

Toda evaluación deberá registrar la versión utilizada.

---

# 14. Inmutabilidad histórica

Una operación histórica deberá conservar:

- rule_id;
- rule_version;
- condiciones evaluadas;
- datos de entrada;
- resultado;
- fecha;
- actor;
- motivo;
- acciones generadas.

Aunque la Regla cambie posteriormente, deberá ser posible explicar:

> ¿Por qué FACT CENTRAL tomó esta decisión en esa fecha?

---

# 15. Condiciones

Una Regla podrá evaluar condiciones como:

- igualdad;
- diferencia;
- mayor que;
- menor que;
- mayor o igual;
- menor o igual;
- pertenencia a lista;
- existencia;
- ausencia;
- estado;
- fecha;
- rango;
- porcentaje;
- cantidad;
- relación;
- acumulado;
- clasificación;
- resultado previo;
- condición compuesta.

---

# 16. Condiciones compuestas

Las condiciones podrán combinarse mediante:

- AND;
- OR;
- NOT;
- grupos;
- subreglas;
- dependencias.

Ejemplo:

```text
SI

tipo_documento = FACTURA

AND

monto > umbral_bancarizacion

AND

estado_documento = VALIDADO

ENTONCES

voucher = OBLIGATORIO
```

---

# 17. Acciones de una Regla

Una Regla podrá producir:

## ALLOW

Permitir operación.

## DENY

Denegar operación.

## REQUIRE

Exigir condición, documento o aprobación.

## WARN

Mostrar advertencia.

## ALERT

Crear alerta.

## CLASSIFY

Clasificar un recurso.

## CALCULATE

Calcular resultado.

## ASSIGN

Asignar recurso o responsable.

## CHANGE_STATE

Solicitar transición de estado.

## REQUEST_APPROVAL

Solicitar autorización.

## RECOMMEND

Proponer una acción.

## SCHEDULE

Programar una revisión futura.

## HOLD

Retener temporalmente una operación.

---

# 18. Acciones destructivas

El Rule Engine no ejecutará directamente acciones destructivas
irreversibles sin controles adicionales.

Ejemplos:

- eliminación física;
- cierre definitivo;
- eliminación de Tenant;
- borrado de backup;
- transferencia económica;
- modificación de información fiscal consolidada.

Estas acciones requerirán:

- permiso;
- aprobación;
- reautenticación;
- auditoría;
- proceso especializado.

---

# 19. Determinismo

Cuando una Regla reciba el mismo:

- contexto;
- versión;
- datos;
- periodo;
- configuración;

deberá producir el mismo resultado.

Las decisiones económicas, fiscales y de permisos
no dependerán de respuestas impredecibles de IA.

---

# 20. Relación con NEXUS

NEXUS podrá:

- sugerir una Regla;
- identificar anomalías;
- recomendar umbrales;
- detectar patrones;
- simular resultados;
- proponer una nueva versión.

NEXUS no podrá:

- activar reglas legales;
- modificar porcentajes;
- cambiar liquidaciones;
- eliminar controles;
- aprobar una Regla crítica;

sin la autorización correspondiente.

---

# 21. IA y reglas

La IA podrá participar en:

- clasificación;
- extracción;
- detección;
- recomendación;
- estimación;
- normalización.

Pero una decisión crítica deberá apoyarse en:

- datos verificados;
- reglas determinísticas;
- umbrales;
- permisos;
- aprobaciones.

Ejemplo:

```text
IA detecta posible Factura
        ↓
confidence = 68 %
        ↓
Regla:
si confidence < límite
        ↓
REVISIÓN HUMANA
```

---

# 22. Prioridad

Cada Regla tendrá prioridad.

Ejemplo conceptual:

```text
1000  Seguridad crítica
900   Cumplimiento legal
800   Integridad fiscal
700   Aislamiento Tenant
600   Reglas de plataforma
500   Reglas del Tenant
400   Reglas comerciales
300   Reglas operativas
200   Recomendaciones
100   Informativas
```

Los valores exactos serán configurables dentro de límites seguros.

---

# 23. Resolución de conflictos

Existe conflicto cuando dos reglas aplicables producen
resultados incompatibles.

Ejemplo:

```text
Regla A:
PERMITIR CIERRE

Regla B:
IMPEDIR CIERRE POR VOUCHER FALTANTE
```

El Motor deberá resolver utilizando:

1. criticidad;
2. jerarquía;
3. prioridad;
4. especificidad;
5. vigencia;
6. excepción autorizada.

Por defecto:

```text
DENY
```

tendrá precedencia sobre:

```text
ALLOW
```

cuando esté involucrada:

- seguridad;
- integridad;
- cumplimiento;
- información incompleta;
- riesgo fiscal.

---

# 24. Regla más específica

Cuando dos reglas de igual jerarquía sean compatibles,
podrá prevalecer la más específica.

Ejemplo:

```text
Regla general del Tenant
+
Regla específica del Cliente
```

La específica podrá ajustar el comportamiento siempre que
no contradiga una regla superior.

---

# 25. Excepciones

Una excepción será una autorización controlada
para apartarse temporalmente de una Regla.

Toda excepción deberá contener:

- exception_id;
- rule_id;
- tenant_id;
- recurso;
- alcance;
- motivo;
- persona que solicita;
- persona que aprueba;
- inicio;
- expiración;
- restricciones;
- evidencia;
- auditoría.

---

# 26. Excepciones prohibidas

No se permitirán excepciones que vulneren:

- aislamiento multi-tenant;
- conservación obligatoria;
- integridad de auditoría;
- prohibiciones de seguridad;
- eliminación de evidencia;
- unicidad fiscal del CPE;
- protección de datos.

---

# 27. Regla de duplicados

La identidad fiscal de un CPE será:

```text
RUC EMISOR
+
TIPO CPE
+
SERIE
+
CORRELATIVO
```

Regla:

```text
1 IDENTIDAD FISCAL
=
1 CPE LÓGICO
=
1 IMPACTO ECONÓMICO
```

Podrán existir múltiples archivos asociados,
pero no múltiples contabilizaciones.

---

# 28. Conflicto fiscal

Si dos archivos presentan:

- misma identidad fiscal;
- datos económicos incompatibles;

el sistema deberá producir:

```text
CONFLICTO DE IDENTIDAD FISCAL
```

y no deberá:

- crear un segundo CPE;
- escoger silenciosamente;
- contabilizar ambos;
- eliminar evidencia.

---

# 29. Regla de Bancarización

La Regla deberá utilizar:

- jurisdicción;
- norma;
- umbral vigente;
- moneda;
- fecha;
- naturaleza de la operación;
- condiciones aplicables.

No deberá existir un número permanente escrito directamente
en el código.

El umbral tendrá versión y vigencia.

---

# 30. Regla de expediente documental

El Motor podrá determinar si un documento es:

- OBLIGATORIO;
- CONDICIONAL;
- RECOMENDADO;
- NO APLICA.

Ejemplo:

```text
Factura bancarizada
→ Voucher obligatorio.

Operación con traslado de bienes
→ Guía según condición.

Cliente agente de retención
→ Constancia de retención cuando corresponda.
```

---

# 31. Regla de cierre de Expediente

Un Expediente podrá cerrarse cuando:

- todos los documentos obligatorios estén presentes;
- no existan conflictos críticos abiertos;
- los documentos estén correctamente relacionados;
- las validaciones exigidas hayan terminado;
- las reglas de cumplimiento se satisfagan;
- el actor tenga permiso.

Si falta una condición:

```text
CIERRE DENEGADO
```

o:

```text
CIERRE CON OBSERVACIÓN
```

según política.

---

# 32. Regla de Pedidos

El Administrador registrará el monto mensual por Cliente.

El Motor evaluará:

- periodo;
- monto solicitado;
- monto ejecutado;
- saldo;
- exceso;
- Usuarios asignados;
- Gestores;
- Proveedores;
- rotación;
- concentración;
- modalidad del Proveedor;
- cumplimiento.

---

# 33. Regla de concentración

El Motor podrá calcular la participación de cada Proveedor
dentro de:

- Cliente;
- Usuario;
- Gestor;
- periodo;
- producto.

Los límites podrán ser:

- fijos;
- proporcionales;
- adaptativos;
- recomendados por NEXUS;
- aprobados por Administración.

---

# 34. Regla de rotación

La ventana de rotación será configurable por vigencia.

Ejemplo:

```text
Proveedor A
emitió a Cliente X en julio.

Ventana:
3 meses.

El sistema evita nueva asignación
hasta completar la ventana,
salvo excepción autorizada.
```

---

# 35. Regla de modalidad del Proveedor

Los Proveedores podrán operar bajo:

## SIN RESTRICCIÓN

No requieren un Pedido previo.

## POR PEDIDO

Requieren monto asignado.

La modalidad:

- tendrá vigencia;
- podrá cambiar;
- no modificará periodos anteriores;
- quedará auditada.

---

# 36. Regla de liquidación

Cada Usuario tendrá un Plan de Liquidación vigente.

El Motor podrá ejecutar:

- cálculo estándar;
- cálculo por componentes;
- cálculo especial;
- adelantos;
- ajustes;
- distribución;
- saldo.

No deberá existir código como:

```text
SI usuario = JAVIER01
```

Deberá existir:

```text
usuario
→ plan de liquidación vigente
→ reglas del plan
```

---

# 37. Fórmulas de liquidación

Las fórmulas no deberán introducirse como código libre
ni como fórmulas de Excel sin control.

Se utilizarán componentes estructurados:

- base;
- porcentaje;
- condición;
- suma;
- resta;
- distribución;
- redondeo;
- límite;
- orden;
- vigencia.

---

# 38. Porcentajes visibles

El Usuario podrá ver:

- porcentajes autorizados visibles;
- vigencia;
- producción;
- comisión;
- adelantos;
- saldo;
- resultado.

No verá necesariamente:

- fórmula interna completa;
- composición técnica;
- reglas reservadas;
- lógica de otros Usuarios.

---

# 39. Reglas SaaS

El Rule Engine también evaluará:

- Plan activo;
- Tenant suspendido;
- cuota disponible;
- funcionalidad habilitada;
- consumo;
- periodo de gracia;
- solo lectura;
- permisos de exportación.

Ejemplo:

```text
Tenant SUSPENDED
+
intenta document.upload
        ↓
DENY
```

---

# 40. Multi-tenant

Toda Regla deberá ejecutarse dentro de un Tenant,
salvo reglas de plataforma.

El contexto deberá incluir:

- tenant_id;
- membership_id;
- role;
- resource_id;
- periodo;
- jurisdicción.

Una Regla nunca deberá usar datos de otro Tenant.

---

# 41. Reglas globales y reglas por Tenant

Las reglas globales podrán definir límites que un Tenant
no podrá debilitar.

Ejemplo:

```text
Regla global:
No permitir acceso entre Tenants.

Regla Tenant:
Permitir acceso total a Administrador.

Resultado:
Administrador ve todo su Tenant,
pero nunca otro Tenant.
```

---

# 42. Contexto de evaluación

El contexto podrá contener:

- tenant;
- persona;
- rol;
- Cliente;
- Proveedor;
- Usuario;
- Gestor;
- documento;
- CPE;
- Expediente;
- pedido;
- producto;
- periodo;
- plan;
- suscripción;
- estado;
- valores calculados;
- eventos anteriores.

El contexto deberá ser explícito y auditable.

---

# 43. Evaluación síncrona

Se usará cuando la respuesta sea necesaria antes de continuar.

Ejemplos:

- autorización de acceso;
- cierre de Expediente;
- modificación de porcentaje;
- aceptación de cuenta bancaria;
- validación de Tenant;
- control de duplicado.

---

# 44. Evaluación asíncrona

Se usará cuando la operación pueda continuar mediante colas.

Ejemplos:

- generación de alertas;
- recalcular Dashboard;
- revisión periódica de SSCO;
- analizar concentración;
- detectar anomalías;
- solicitar documentos pendientes.

---

# 45. Idempotencia

La misma evaluación no deberá generar repetidamente:

- alertas duplicadas;
- cargos duplicados;
- pagos duplicados;
- cambios de estado repetidos;
- documentos duplicados.

Toda acción derivada deberá utilizar una clave de idempotencia.

---

# 46. Simulación

El Administrador podrá simular una Regla antes de activarla.

Ejemplo:

```text
Nueva concentración máxima:
20 %

Simular en julio 2026
        ↓
Proveedores afectados: 18
Alertas generadas: 7
Asignaciones bloqueadas: 3
```

La simulación:

- no modificará datos;
- no enviará alertas reales;
- no ejecutará pagos;
- no cambiará estados;
- quedará registrada.

---

# 47. Shadow Mode

Una Regla podrá ejecutarse en modo sombra.

En Shadow Mode:

- evalúa casos reales;
- registra qué habría decidido;
- no modifica producción;
- no bloquea operaciones;
- no envía acciones externas;
- permite comparar resultados.

Esto será útil antes de activar:

- nuevas reglas;
- nuevos umbrales;
- automatizaciones;
- recomendaciones de NEXUS.

---

# 48. Pruebas de Regla

Toda Regla deberá poder probarse con:

- casos positivos;
- casos negativos;
- límites;
- conflictos;
- datos incompletos;
- periodos históricos;
- múltiples Tenants;
- múltiples roles.

Una Regla crítica no podrá activarse sin pruebas aprobadas.

---

# 49. Casos de prueba mínimos

Ejemplo para bancarización:

```text
Caso 1:
monto inferior al umbral
→ Voucher no obligatorio por esta Regla.

Caso 2:
monto igual al umbral
→ aplicar condición exacta vigente.

Caso 3:
monto superior al umbral
→ Voucher obligatorio.

Caso 4:
moneda distinta
→ convertir o evaluar según norma vigente.

Caso 5:
Regla histórica
→ conservar resultado original.
```

---

# 50. Aprobación de reglas

Podrán existir distintos niveles:

## AUTOMATIC_APPROVAL

Para reglas informativas no críticas.

## ADMIN_APPROVAL

Aprobación del Administrador del Tenant.

## SUPERADMIN_APPROVAL

Para reglas globales de plataforma.

## DUAL_APPROVAL

Para reglas críticas.

## LEGAL_REVIEW

Para reglas tributarias o regulatorias.

---

# 51. Responsabilidades

## Superadmin

Puede administrar:

- reglas globales;
- reglas SaaS;
- seguridad;
- plataforma;
- Planes;
- jurisdicciones.

## Administrador

Puede administrar:

- reglas de su Tenant;
- pedidos;
- alertas;
- límites;
- liquidaciones;
- rotación;
- configuración documental.

## Gerente

Puede consultar resultados autorizados.

No modifica reglas.

## Secretaría

Puede ejecutar revisiones y crear alertas.

No configura fórmulas ni pagos.

## Usuario

Puede consultar sus resultados y condiciones visibles.

No modifica reglas de comisión.

## Gestor

Puede consultar resultados operativos propios.

No administra reglas.

---

# 52. Interfaz de Administración

El panel podrá mostrar:

```text
REGLAS DEL TENANT

Código
Nombre
Categoría
Versión
Vigencia
Prioridad
Estado
Última modificación
Responsable
```

Acciones autorizadas:

- ver;
- crear borrador;
- duplicar;
- simular;
- enviar a revisión;
- aprobar;
- activar;
- suspender;
- reemplazar;
- consultar historial.

---

# 53. Reglas predeterminadas

FACT CENTRAL podrá ofrecer plantillas.

Ejemplos:

- bancarización;
- Expediente completo;
- duplicado fiscal;
- SSCO;
- concentración;
- rotación;
- cuenta bancaria faltante;
- Tenant suspendido;
- MFA obligatorio.

El Administrador podrá configurar los parámetros permitidos,
sin modificar la estructura protegida de la Regla.

---

# 54. Parámetros

Los parámetros permitirán cambiar valores sin crear código nuevo.

Ejemplos:

- porcentaje;
- monto;
- días;
- cantidad;
- severidad;
- tolerancia;
- ventana de rotación;
- límite;
- canal de notificación.

Todo cambio de parámetro tendrá:

- vigencia;
- versión;
- responsable;
- motivo;
- auditoría.

---

# 55. Redondeo

Las reglas económicas deberán definir:

- precisión;
- método de redondeo;
- moneda;
- escala decimal;
- momento del redondeo.

No deberá dejarse al comportamiento predeterminado
de cada lenguaje o interfaz.

---

# 56. Fuentes de datos

Una Regla podrá consumir datos de:

- PostgreSQL;
- resultados verificados del OCR;
- información del CPE;
- APIPERU;
- SUNAT o integraciones autorizadas;
- Billing;
- Subscription Engine;
- Event Bus;
- configuraciones del Tenant.

Toda fuente deberá registrar:

- origen;
- fecha;
- confiabilidad;
- versión;
- estado.

---

# 57. Datos desconocidos

Cuando una condición requiera un dato que no existe,
el resultado no deberá asumirse arbitrariamente.

Estados posibles:

```text
TRUE
FALSE
UNKNOWN
ERROR
```

Ejemplo:

```text
¿Cliente es agente de retención?

Dato no disponible
        ↓
UNKNOWN
        ↓
solicitar revisión o consulta
```

---

# 58. Evaluación segura

Cuando exista incertidumbre en una Regla crítica,
el comportamiento predeterminado será conservador.

Ejemplo:

```text
No se puede comprobar si el Expediente está completo
        ↓
NO CERRAR AUTOMÁTICAMENTE
```

---

# 59. Eventos

El Rule Engine podrá reaccionar a eventos como:

- document.received;
- document.processed;
- cpe.identified;
- cpe.conflict.detected;
- expedient.updated;
- order.amount.exceeded;
- supplier.ssco.detected;
- liquidation.calculated;
- payment.account.changed;
- tenant.subscription.expired.

Cada evento deberá incluir Tenant y contexto.

---

# 60. Integración con Workflow Engine

El Rule Engine decide.

El Workflow Engine coordina los pasos.

Ejemplo:

```text
Rule Engine:
Voucher obligatorio y faltante.

Resultado:
REQUIRE voucher.

Workflow Engine:
crear tarea
→ notificar
→ esperar documento
→ reevaluar
→ continuar.
```

El Rule Engine no deberá asumir toda la orquestación.

---

# 61. Integración con Notification Engine

Una Regla podrá solicitar una notificación.

Ejemplo:

```text
Proveedor detectado en SSCO
        ↓
alerta crítica
        ↓
Notification Engine decide:
bandeja interna
correo
WhatsApp
SMS
```

El Rule Engine define la necesidad.

El Notification Engine ejecuta el canal.

---

# 62. Integración con Time Engine

Las reglas temporales utilizarán el Time Engine.

Ejemplos:

- después de 24 horas;
- al inicio del mes;
- en quincena;
- al vencer una Regla;
- al concluir periodo de gracia;
- cada 3 meses;
- al cerrar ejercicio.

El Rule Engine no deberá crear temporizadores independientes.

---

# 63. Integración con Permission Engine

Antes de crear, modificar, aprobar o activar una Regla,
se deberá comprobar:

- Tenant;
- rol;
- permiso;
- alcance;
- estado;
- MFA cuando corresponda.

---

# 64. Rendimiento

El Rule Engine deberá soportar:

- evaluación en tiempo real;
- evaluación masiva;
- procesamiento asíncrono;
- caché de reglas vigentes;
- invalidación de caché;
- aislamiento por Tenant;
- escalado horizontal.

---

# 65. Caché

Las reglas activas podrán mantenerse en caché.

Las claves deberán incluir:

- tenant_id;
- rule_code;
- version;
- scope;
- effective_date.

Al activar una nueva versión,
la caché anterior deberá invalidarse correctamente.

---

# 66. Auditoría

Toda evaluación relevante registrará:

- evaluation_id;
- tenant_id;
- rule_id;
- rule_version;
- contexto;
- recurso;
- condiciones;
- resultado;
- acción;
- fecha;
- duración;
- persona o servicio;
- estado;
- error, si existe.

---

# 67. Explicabilidad

El sistema deberá poder explicar una decisión.

Ejemplo:

```text
CIERRE DENEGADO

Regla:
EXPEDIENT.BANKING.VOUCHER_REQUIRED

Versión:
3

Motivo:
El monto de la operación requiere sustento de pago
y el Expediente no contiene Voucher validado.

Fecha de evaluación:
03/08/2026 18:45
```

---

# 68. Privacidad

La explicación deberá respetar permisos.

Un Usuario podrá ver:

- la razón de su propio resultado;
- la condición visible;
- el documento faltante.

No necesariamente verá:

- reglas internas de otros Usuarios;
- fórmulas reservadas;
- datos bancarios ajenos;
- configuración completa del Tenant.

---

# 69. Errores

Resultados posibles:

```text
RULE_MATCHED
RULE_NOT_MATCHED
RULE_SKIPPED
RULE_CONFLICT
RULE_DATA_UNKNOWN
RULE_EXECUTION_ERROR
RULE_APPROVAL_REQUIRED
```

Los errores no deberán provocar decisiones económicas silenciosas.

---

# 70. Reprocesamiento

Cuando una Regla cambie, el Administrador podrá solicitar:

- no reprocesar histórico;
- simular histórico;
- reprocesar periodo abierto;
- recalcular elementos pendientes;
- generar informe de impacto.

Nunca se modificará silenciosamente un periodo cerrado.

---

# 71. Regla de periodos cerrados

En un periodo cerrado:

- se conserva la Regla utilizada;
- se conserva el resultado;
- no se recalcula automáticamente;
- cualquier reapertura requiere permiso;
- cualquier ajuste genera auditoría.

---

# 72. Portabilidad

Las reglas deberán representarse mediante una estructura
portable y versionada.

No deberán depender exclusivamente de:

- hojas de Excel;
- código Python;
- interfaz gráfica;
- proveedor de IA;
- plataforma externa.

---

# 73. Escalabilidad

El Motor deberá soportar:

- pocos Tenants;
- miles de Tenants;
- millones de evaluaciones;
- reglas globales;
- reglas específicas;
- ejecución distribuida.

Sin cambiar la lógica central.

---

# 74. Seguridad

No se permitirá:

- ejecutar código arbitrario desde una Regla;
- introducir scripts sin validación;
- acceder a otro Tenant;
- modificar reglas activas sin versionar;
- omitir auditoría;
- alterar históricos;
- ejecutar acciones críticas sin permiso.

---

# 75. Regla de no código libre

Los Administradores configurarán reglas mediante:

- plantillas;
- parámetros;
- condiciones aprobadas;
- componentes;
- operadores permitidos.

No podrán insertar:

- Python;
- JavaScript;
- SQL;
- comandos del sistema;
- fórmulas arbitrarias ejecutables.

---

# 76. Validación previa a activación

Antes de activar una Regla se verificará:

- sintaxis;
- consistencia;
- campos existentes;
- conflictos;
- permisos;
- vigencia;
- impacto;
- casos de prueba;
- aprobación;
- compatibilidad con reglas superiores.

---

# 77. Ciclo de vida

```text
CREAR BORRADOR
        ↓
CONFIGURAR
        ↓
VALIDAR
        ↓
SIMULAR
        ↓
REVISAR
        ↓
APROBAR
        ↓
PROGRAMAR VIGENCIA
        ↓
ACTIVAR
        ↓
EVALUAR
        ↓
AUDITAR
        ↓
REEMPLAZAR O EXPIRAR
```

---

# 78. Ejemplo completo: Voucher obligatorio

```text
Código:
EXPEDIENT.BANKING.VOUCHER_REQUIRED

Categoría:
DOCUMENTAL / CUMPLIMIENTO

Ámbito:
JURISDICTION + TENANT

Condiciones:
- documento principal es CPE válido;
- operación alcanza condición de bancarización;
- Expediente no contiene Voucher validado.

Resultado:
REQUIRE voucher.

Acciones:
- marcar Expediente incompleto;
- crear alerta;
- impedir cierre automático;
- notificar a responsables.

Prioridad:
Alta.

Vigencia:
según norma y configuración.

Auditoría:
obligatoria.
```

---

# 79. Ejemplo completo: concentración

```text
Código:
ORDER.SUPPLIER.CONCENTRATION_LIMIT

Condiciones:
- periodo activo;
- Proveedor pertenece al Usuario;
- monto ejecutado / monto total supera límite.

Resultado:
ALERT.

Acciones:
- mostrar porcentaje;
- identificar facturas;
- recomendar redistribución;
- solicitar aprobación si continúa.

El sistema no acusará fraude automáticamente.

Mostrará el comportamiento objetivo.
```

---

# 80. Ejemplo completo: Cuenta de pago

```text
Código:
PAYMENT.ACCOUNT.REQUIRED

Condiciones:
- liquidación cerrada;
- saldo pagable mayor a cero;
- Usuario sin cuentas activas válidas.

Resultado:
HOLD.

Mensaje:
PAGO NO PROGRAMABLE.

Motivo:
El Usuario no registró cuentas de pago activas.
```

---

# 81. Métricas

El Rule Engine medirá:

- evaluaciones totales;
- tiempo de evaluación;
- reglas activas;
- conflictos;
- errores;
- alertas generadas;
- acciones bloqueadas;
- reglas sin uso;
- reglas con alto impacto;
- porcentaje de revisión humana.

---

# 82. Observabilidad

El sistema deberá permitir consultar:

- qué Regla se ejecutó;
- cuánto tardó;
- qué decidió;
- qué datos utilizó;
- qué acción generó;
- si falló;
- si fue simulación;
- si fue Shadow Mode;
- si produjo conflicto.

---

# 83. Regla Suprema de diseño

El Rule Engine decidirá sobre condiciones.

No reemplazará:

- Workflow Engine;
- Event Bus;
- Notification Engine;
- Time Engine;
- Permission Engine;
- Payment Engine;
- Storage Manager.

Cada componente mantendrá su responsabilidad.

---

# 84. Reglas supremas

## Regla Suprema 1

TODA REGLA CONFIGURABLE DE FACT CENTRAL DEBERÁ ESTAR VERSIONADA.

## Regla Suprema 2

NINGUNA REGLA NUEVA MODIFICARÁ SILENCIOSAMENTE EL HISTORIAL.

## Regla Suprema 3

LAS REGLAS LEGALES, DE SEGURIDAD E INTEGRIDAD
TIENEN PRIORIDAD SOBRE LAS REGLAS COMERCIALES.

## Regla Suprema 4

EL RULE ENGINE SERÁ DETERMINÍSTICO PARA DECISIONES CRÍTICAS.

## Regla Suprema 5

LA IA PUEDE RECOMENDAR, PERO NO CAMBIAR REGLAS CRÍTICAS
SIN AUTORIZACIÓN.

## Regla Suprema 6

NINGÚN ADMINISTRADOR PODRÁ INTRODUCIR CÓDIGO LIBRE EJECUTABLE.

## Regla Suprema 7

TODA REGLA OPERARÁ DENTRO DEL TENANT CORRESPONDIENTE.

## Regla Suprema 8

TODA DECISIÓN IMPORTANTE DEBERÁ SER EXPLICABLE Y AUDITABLE.

## Regla Suprema 9

CUANDO EXISTA CONFLICTO CRÍTICO, EL SISTEMA ACTUARÁ
DE MANERA CONSERVADORA.

## Regla Suprema 10

UN CPE LÓGICO SOLO PODRÁ GENERAR UN IMPACTO ECONÓMICO.

## Regla Suprema 11

LAS EXCEPCIONES SERÁN TEMPORALES, JUSTIFICADAS Y AUDITADAS.

## Regla Suprema 12

EL RULE ENGINE DECIDE; OTROS MOTORES EJECUTAN,
ORQUESTAN, NOTIFICAN O PROGRAMAN.

## Regla Suprema 13

LOS RESULTADOS DE PERIODOS CERRADOS NO SE RECALCULARÁN
AUTOMÁTICAMENTE.

## Regla Suprema 14

TODOS LOS CAMBIOS DE PARÁMETROS TENDRÁN VIGENCIA E HISTORIAL.

## Regla Suprema 15

FACT CENTRAL NO DEPENDERÁ DE EXCEL NI DE REGLAS
DISPERSAS EN EL CÓDIGO PARA GOBERNAR EL NEGOCIO.
