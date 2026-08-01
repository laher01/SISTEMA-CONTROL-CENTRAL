# 06_BILLING_ENGINE.md

# FACT CENTRAL SaaS

## BILLING ENGINE

Versión 1.0

---

# 1. Objetivo

Definir el Motor Oficial de Facturación y Cobro de FACT CENTRAL SaaS.

Este documento establece:

- cómo se generan órdenes de pago;
- cómo se calculan importes;
- cómo se aplican impuestos;
- cómo se manejan monedas;
- cómo se conectan pasarelas;
- cómo se confirman pagos;
- cómo se emiten comprobantes;
- cómo se concilian operaciones;
- cómo se gestionan devoluciones;
- cómo se tratan contracargos;
- cómo se conserva el historial económico;
- cómo se audita toda operación de facturación SaaS.

---

# 2. Principio fundamental

El Billing Engine administrará únicamente los cobros relacionados con:

- suscripciones;
- renovaciones;
- complementos;
- almacenamiento adicional;
- procesamiento adicional;
- integraciones;
- servicios especiales;
- ajustes comerciales;
- cargos autorizados.

No administrará los pagos internos del ERP a Usuarios.

---

# 3. Separación absoluta

FACT CENTRAL tendrá dos motores económicos distintos.

## Billing SaaS

El Administrador paga por utilizar FACT CENTRAL.

## Pagos ERP

El Gerente ejecuta pagos o comisiones a los Usuarios del Tenant.

Nunca deberán mezclarse:

- saldos;
- cuentas;
- comprobantes;
- vouchers;
- reglas;
- periodos;
- reportes;
- conciliaciones.

---

# 4. Relación oficial

TENANT
↓
SUSCRIPCIÓN
↓
PLAN
↓
PERIODO
↓
ORDEN DE COBRO
↓
PAGO
↓
CONFIRMACIÓN
↓
COMPROBANTE
↓
CONCILIACIÓN

---

# 5. Entidades principales

El Billing Engine deberá manejar:

- Customer Billing Profile;
- Billing Account;
- Billing Order;
- Invoice;
- Payment Intent;
- Payment Transaction;
- Payment Method;
- Payment Gateway;
- Receipt;
- Refund;
- Chargeback;
- Credit Note;
- Debit Note;
- Reconciliation;
- Tax Rule;
- Currency;
- Exchange Rate;
- Discount;
- Coupon;
- Adjustment;
- Billing Period.

---

# 6. Perfil de facturación

Cada Tenant tendrá un perfil de facturación.

Podrá contener:

- nombre o razón social;
- RUC o identificación fiscal;
- tipo de contribuyente;
- dirección fiscal;
- país;
- departamento o región;
- provincia;
- distrito;
- correo de facturación;
- celular;
- moneda preferida;
- condición tributaria;
- datos adicionales.

El Administrador Propietario será responsable de mantener
actualizada esta información.

---

# 7. Cuenta de facturación

Cada Tenant tendrá una Billing Account.

La cuenta registrará:

- tenant_id;
- billing_profile_id;
- moneda principal;
- estado;
- saldo a favor;
- saldo pendiente;
- créditos;
- débitos;
- límites;
- historial;
- métodos de pago autorizados.

---

# 8. Orden de cobro

Toda operación económica comenzará con una Orden de Cobro.

Ejemplos:

- renovación mensual;
- compra de almacenamiento;
- compra de documentos adicionales;
- activación de integración;
- upgrade de Plan;
- servicio personalizado.

La Orden deberá contener:

- order_id;
- tenant_id;
- subscription_id;
- periodo;
- conceptos;
- moneda;
- subtotal;
- descuentos;
- impuestos;
- total;
- fecha de emisión;
- fecha de vencimiento;
- estado;
- referencia externa;
- canal de pago.

---

# 9. Estados de la Orden

Los estados oficiales serán:

DRAFT

ISSUED

PENDING_PAYMENT

PARTIALLY_PAID

PAID

OVERDUE

CANCELLED

EXPIRED

REFUNDED

PARTIALLY_REFUNDED

UNDER_REVIEW

---

# 10. Conceptos facturables

Una Orden podrá incluir uno o varios conceptos.

Ejemplos:

- Plan Empresa mensual;
- 100 GB adicionales;
- 10,000 documentos adicionales;
- integración Gmail;
- integración WhatsApp;
- OCR adicional;
- IA adicional;
- soporte premium;
- servicio de implementación;
- configuración personalizada;
- migración de datos;
- capacitación;
- recuperación de backup;
- consultoría.

Cada concepto deberá registrar:

- código;
- descripción;
- cantidad;
- unidad;
- precio unitario;
- descuento;
- impuesto;
- total.

---

# 11. Precios

Los precios podrán ser:

- fijos;
- escalonados;
- por consumo;
- por volumen;
- personalizados;
- promocionales;
- prorrateados.

Ejemplo:

Hasta 10,000 documentos:
precio base.

De 10,001 a 50,000:
precio por bloque.

Más de 50,000:
precio corporativo.

---

# 12. Versionado de precios

Todo precio deberá estar versionado.

Ejemplo:

PLAN EMPRESA

Versión 1
Vigencia:
01/01/2026 al 30/06/2026

Versión 2
Vigencia:
desde 01/07/2026

Las órdenes históricas conservarán el precio vigente al momento
de su emisión.

---

# 13. Monedas

El Billing Engine deberá soportar múltiples monedas.

Ejemplos:

- PEN;
- USD;
- EUR.

Cada Orden tendrá una moneda de emisión.

No se deberá cambiar la moneda después de confirmarse el pago,
salvo proceso autorizado.

---

# 14. Tipo de cambio

Cuando se requiera conversión, se registrará:

- moneda origen;
- moneda destino;
- tipo de cambio;
- fecha;
- proveedor de tasa;
- referencia;
- importe original;
- importe convertido;
- redondeo.

El tipo de cambio utilizado deberá conservarse históricamente.

---

# 15. Impuestos

Los impuestos dependerán de:

- país;
- tipo de servicio;
- condición fiscal;
- moneda;
- perfil del Tenant;
- normativa vigente.

El Billing Engine deberá permitir configurar:

- impuesto;
- porcentaje;
- base;
- vigencia;
- jurisdicción;
- exoneración;
- inafectación;
- retención aplicable;
- observaciones.

No se deberán codificar permanentemente tasas dentro del código.

---

# 16. Regla tributaria configurable

Toda regla fiscal deberá tener:

- nombre;
- país;
- jurisdicción;
- tipo;
- tasa;
- vigencia desde;
- vigencia hasta;
- condiciones;
- prioridad;
- estado;
- fuente normativa;
- responsable de actualización.

---

# 17. Descuentos

Podrán aplicarse descuentos:

- porcentuales;
- fijos;
- promocionales;
- por volumen;
- por pago anual;
- por campaña;
- por alianza;
- por antigüedad;
- manuales autorizados.

Cada descuento tendrá:

- discount_id;
- tipo;
- valor;
- vigencia;
- límites;
- Plan aplicable;
- Tenant aplicable;
- cantidad máxima de usos;
- acumulabilidad;
- estado.

---

# 18. Cupones

Un cupón podrá:

- aplicar porcentaje;
- aplicar monto fijo;
- otorgar días gratuitos;
- añadir capacidad;
- reducir un complemento;
- permitir un upgrade temporal.

Estados:

ACTIVE

USED

EXPIRED

REVOKED

LIMIT_REACHED

---

# 19. Ajustes

El Billing Engine permitirá ajustes positivos o negativos.

Ejemplos:

- corrección comercial;
- diferencia de prorrateo;
- saldo a favor;
- penalidad;
- descuento excepcional;
- ajuste por soporte;
- compensación.

Todo ajuste requerirá:

- motivo;
- responsable;
- fecha;
- importe;
- aprobación;
- auditoría.

---

# 20. Prorrateo

Cuando un Tenant cambie de Plan a mitad de periodo,
el sistema podrá calcular:

- días utilizados;
- saldo no consumido;
- valor del nuevo Plan;
- diferencia;
- crédito;
- importe a pagar.

El método de prorrateo será configurable.

---

# 21. Métodos de pago

El Billing Engine podrá admitir:

- tarjeta de crédito;
- tarjeta de débito;
- transferencia bancaria;
- depósito;
- Yape;
- Plin;
- PayPal;
- Skrill;
- billeteras autorizadas;
- pasarelas locales;
- pasarelas internacionales;
- criptomonedas autorizadas;
- saldo a favor;
- crédito interno.

---

# 22. Pasarela de pago

Cada pasarela será un adaptador independiente.

Ejemplo:

PAYMENT_GATEWAY

├── CARD_GATEWAY
├── PAYPAL_GATEWAY
├── BANK_TRANSFER_GATEWAY
├── WALLET_GATEWAY
└── CRYPTO_GATEWAY

El Billing Engine no dependerá de un único proveedor.

---

# 23. Contrato de pasarela

Toda pasarela deberá exponer operaciones normalizadas:

- create_payment;
- get_payment_status;
- cancel_payment;
- refund_payment;
- validate_webhook;
- tokenize_method;
- get_transaction;
- reconcile_payment.

La implementación concreta podrá cambiar sin alterar
la lógica general.

---

# 24. Payment Intent

Antes de realizar un pago se generará un Payment Intent.

Contendrá:

- payment_intent_id;
- tenant_id;
- billing_order_id;
- importe;
- moneda;
- método;
- pasarela;
- fecha;
- expiración;
- estado;
- idempotency_key;
- referencia externa.

---

# 25. Estados del Payment Intent

CREATED

REQUIRES_ACTION

PENDING

PROCESSING

SUCCEEDED

FAILED

CANCELLED

EXPIRED

REFUNDED

PARTIALLY_REFUNDED

UNDER_REVIEW

---

# 26. Idempotencia

Toda creación o confirmación de pago deberá ser idempotente.

Un mismo Payment Intent procesado varias veces deberá producir
un solo pago válido.

Ejemplo:

1 Payment Intent confirmado
=
1 transacción
=
1 renovación

No deberá duplicar:

- periodos;
- saldos;
- comprobantes;
- facturación;
- créditos.

---

# 27. Pago manual

Para métodos manuales:

ADMINISTRADOR
↓
GENERA ORDEN
↓
SELECCIONA MÉTODO
↓
REALIZA TRANSFERENCIA O DEPÓSITO
↓
SUBE COMPROBANTE
↓
PAGO EN REVISIÓN
↓
VALIDACIÓN
↓
CONFIRMACIÓN

El comprobante de pago será una evidencia digital.

---

# 28. Pago automático

Para métodos automáticos:

ADMINISTRADOR
↓
SELECCIONA MÉTODO
↓
PASARELA
↓
AUTORIZA
↓
WEBHOOK
↓
VALIDACIÓN
↓
CONFIRMACIÓN
↓
RENOVACIÓN

---

# 29. Pago parcial

Una Orden podrá admitir pago parcial cuando la política lo permita.

Estados:

PARTIALLY_PAID

La Orden registrará:

- total;
- pagado;
- saldo pendiente;
- transacciones;
- vencimiento.

No se activará completamente la Suscripción si la política exige
pago total.

---

# 30. Saldo a favor

El Tenant podrá tener saldo a favor.

Origen posible:

- pago duplicado;
- devolución;
- crédito comercial;
- prorrateo;
- ajuste;
- promoción.

El saldo a favor podrá aplicarse a nuevas Órdenes.

---

# 31. Crédito interno

FACT CENTRAL podrá otorgar crédito autorizado.

El crédito tendrá:

- monto;
- moneda;
- vigencia;
- motivo;
- límite;
- responsable;
- estado.

No deberá confundirse con saldo a favor.

---

# 32. Confirmación de pago

Un pago será confirmado solamente cuando exista:

- respuesta válida de pasarela;
- webhook verificado;
- conciliación bancaria;
- validación manual autorizada;
- evidencia suficiente.

No bastará con que el navegador muestre “pago realizado”.

---

# 33. Webhooks

Los Webhooks deberán:

- validar firma;
- validar secreto;
- validar origen;
- verificar fecha;
- impedir replay;
- usar idempotencia;
- registrar evento;
- tolerar reintentos;
- actualizar estados de forma segura.

---

# 34. Eventos de pago

Ejemplos:

payment.created

payment.pending

payment.succeeded

payment.failed

payment.refunded

payment.chargeback

payment.cancelled

invoice.issued

invoice.paid

subscription.renewed

subscription.suspended

---

# 35. Conciliación

La conciliación comparará:

- Orden;
- Payment Intent;
- transacción de pasarela;
- depósito;
- referencia bancaria;
- importe;
- moneda;
- fecha;
- Tenant;
- comprobante.

Estados:

MATCHED

PARTIAL_MATCH

UNMATCHED

DUPLICATE

AMOUNT_MISMATCH

CURRENCY_MISMATCH

UNDER_REVIEW

---

# 36. Conciliación automática

Cuando exista información suficiente:

TRANSACTION
↓
ORDER
↓
TENANT
↓
AMOUNT
↓
CURRENCY
↓
REFERENCE
↓
MATCH

Resultado:

MATCHED

---

# 37. Conciliación manual

Cuando no exista coincidencia automática,
Superadmin o personal autorizado podrá:

- relacionar pago;
- corregir referencia;
- observar operación;
- rechazar evidencia;
- solicitar información;
- registrar motivo.

---

# 38. Comprobante SaaS

Cuando corresponda, FACT CENTRAL podrá emitir o registrar
un comprobante por el servicio SaaS.

Podrá ser:

- factura;
- boleta;
- recibo;
- documento equivalente;
- comprobante internacional;
- nota de crédito;
- nota de débito.

La emisión dependerá de la configuración tributaria.

---

# 39. Datos del comprobante

El comprobante podrá incluir:

- emisor;
- receptor;
- identificación fiscal;
- dirección;
- fecha;
- moneda;
- conceptos;
- subtotal;
- impuestos;
- descuentos;
- total;
- forma de pago;
- referencia;
- periodo;
- orden relacionada;
- estado.

---

# 40. Comprobante electrónico

Cuando se utilice facturación electrónica,
el Billing Engine podrá integrarse con:

- SUNAT;
- PSE;
- OSE;
- proveedor autorizado;
- sistema externo.

La integración no deberá mezclarse con el procesamiento
de CPE de los Tenants.

---

# 41. Separación documental

Los comprobantes emitidos por FACT CENTRAL SaaS pertenecerán
al módulo comercial de la plataforma.

Los comprobantes que los Tenants suben al ERP pertenecen
al módulo documental del Tenant.

No se deberán mezclar.

---

# 42. Notas de crédito

Podrán emitirse por:

- anulación;
- descuento posterior;
- devolución;
- error;
- reducción de servicio;
- reembolso;
- ajuste.

Toda Nota de Crédito deberá relacionarse con el comprobante original.

---

# 43. Notas de débito

Podrán emitirse por:

- intereses;
- penalidad;
- diferencia;
- cargo adicional;
- corrección de importe.

Toda Nota de Débito deberá quedar relacionada con el comprobante base.

---

# 44. Devoluciones

Estados:

REFUND_REQUESTED

REFUND_UNDER_REVIEW

REFUND_APPROVED

REFUND_REJECTED

REFUND_PROCESSING

REFUNDED

PARTIALLY_REFUNDED

FAILED

---

# 45. Reembolso parcial

Un pago podrá devolver solo parte del importe.

El sistema deberá registrar:

- monto original;
- monto devuelto;
- saldo;
- motivo;
- fecha;
- pasarela;
- referencia;
- comprobante de devolución.

---

# 46. Contracargos

Un contracargo deberá:

- marcar la transacción;
- bloquear crédito asociado;
- notificar;
- poner la Cuenta en revisión;
- registrar evidencia;
- suspender renovación automática;
- permitir respuesta administrativa.

---

# 47. Disputas

Estados:

OPEN

EVIDENCE_REQUIRED

EVIDENCE_SUBMITTED

WON

LOST

CLOSED

Toda disputa deberá conservar:

- pasarela;
- referencia;
- fechas;
- importe;
- evidencia;
- resultado.

---

# 48. Fraude

El Billing Engine podrá detectar:

- múltiples pagos fallidos;
- tarjetas repetidas;
- comportamiento anómalo;
- creación masiva de Tenants;
- uso abusivo de pruebas;
- identidad inconsistente;
- chargebacks recurrentes;
- referencias duplicadas;
- comprobantes alterados.

---

# 49. Riesgo de pago

Cada operación podrá tener:

LOW

MEDIUM

HIGH

CRITICAL

Una operación de alto riesgo podrá pasar a:

UNDER_REVIEW

antes de activar la Suscripción.

---

# 50. Seguridad de tarjetas

FACT CENTRAL no deberá almacenar datos completos de tarjeta
cuando la pasarela pueda tokenizarlos.

No se almacenarán:

- CVV;
- número completo;
- credenciales sensibles.

Se conservará únicamente:

- token;
- marca;
- últimos cuatro dígitos;
- fecha de expiración parcial;
- referencia segura.

---

# 51. Datos bancarios

Las cuentas bancarias del SaaS deberán estar separadas
de las cuentas de pago de Usuarios del ERP.

Solo personal autorizado podrá administrarlas.

---

# 52. Pagos por transferencia

El sistema podrá mostrar:

- banco;
- titular;
- cuenta;
- CCI;
- moneda;
- referencia;
- instrucciones.

El Administrador adjuntará:

- voucher;
- captura;
- PDF;
- referencia bancaria.

---

# 53. Pagos por billetera

Cuando corresponda, se podrá mostrar:

- número;
- QR;
- titular;
- referencia;
- límite;
- vigencia.

La confirmación podrá ser:

- automática;
- manual;
- por integración.

---

# 54. Pagos con criptomonedas

Cuando se habiliten:

- se usará proveedor especializado;
- se registrará activo;
- red;
- dirección;
- importe;
- tasa;
- expiración;
- hash de transacción;
- confirmaciones;
- estado.

No se implementará custodia directa sin controles específicos.

---

# 55. Pagos en revisión

Una operación pasará a revisión cuando:

- importe no coincide;
- moneda no coincide;
- referencia repetida;
- comprobante ilegible;
- riesgo alto;
- pago parcial no permitido;
- fraude probable;
- webhook inconsistente.

---

# 56. Vencimiento de Orden

Una Orden podrá expirar.

Al expirar:

- no se aceptará confirmación automática sin nueva validación;
- podrá generarse una nueva Orden;
- se conservará el historial;
- se notificará al Administrador.

---

# 57. Recordatorios

El sistema podrá enviar recordatorios:

- al emitir Orden;
- antes del vencimiento;
- el día del vencimiento;
- durante gracia;
- antes de suspensión;
- después de suspensión.

---

# 58. Panel del Administrador

El Administrador verá:

FACTURACIÓN

- Plan;
- periodo;
- Orden actual;
- importe;
- moneda;
- impuestos;
- descuentos;
- vencimiento;
- estado;
- método de pago;
- comprobante;
- historial;
- saldo;
- créditos;
- devoluciones.

Acciones:

- pagar;
- descargar Orden;
- descargar comprobante;
- cambiar método;
- subir voucher;
- solicitar revisión;
- solicitar reembolso;
- actualizar datos fiscales.

---

# 59. Panel del Superadmin

Superadmin podrá ver:

- facturación total;
- ingresos por periodo;
- pagos pendientes;
- pagos fallidos;
- conciliaciones;
- devoluciones;
- contracargos;
- monedas;
- impuestos;
- descuentos;
- cupones;
- riesgo;
- pasarelas;
- errores;
- ingresos por Plan;
- ingresos por país;
- ingresos por canal.

---

# 60. Reportes

El Billing Engine podrá generar:

- ingresos mensuales;
- ingresos recurrentes;
- MRR;
- ARR;
- churn;
- renovaciones;
- morosidad;
- pagos fallidos;
- conversión de prueba;
- upgrade;
- downgrade;
- reembolsos;
- contracargos;
- ticket promedio;
- consumo facturable;
- ingresos por complemento.

---

# 61. MRR

MRR representará el ingreso mensual recurrente normalizado.

No deberá incluir automáticamente:

- pagos únicos;
- migraciones;
- servicios extraordinarios;
- capacitación;
- consultoría.

Estos podrán reportarse por separado.

---

# 62. ARR

ARR podrá calcularse a partir de ingresos recurrentes anualizados.

Deberá distinguir:

- recurrente;
- no recurrente;
- proyectado;
- confirmado.

---

# 63. Auditoría

Toda operación deberá registrar:

- tenant_id;
- billing_account_id;
- order_id;
- invoice_id;
- payment_id;
- persona;
- acción;
- importe;
- moneda;
- fecha;
- estado anterior;
- estado nuevo;
- pasarela;
- referencia;
- IP;
- resultado.

---

# 64. Historial inmutable

No se deberán sobrescribir silenciosamente:

- importes;
- comprobantes;
- referencias;
- estados;
- descuentos;
- impuestos;
- devoluciones;
- conciliaciones.

Los cambios deberán producir nuevas versiones o eventos.

---

# 65. Permisos

Permisos posibles:

billing.profile.view

billing.profile.edit

billing.order.view

billing.order.create

billing.payment.create

billing.payment.confirm

billing.payment.review

billing.refund.request

billing.refund.approve

billing.reconciliation.view

billing.reconciliation.manage

billing.invoice.view

billing.invoice.download

billing.tax.configure

billing.gateway.configure

billing.report.view

---

# 66. Acceso del Administrador

El Administrador podrá:

- ver su facturación;
- pagar;
- descargar comprobantes;
- actualizar perfil;
- solicitar revisión;
- solicitar reembolso;
- consultar historial.

No podrá:

- confirmar manualmente su propio pago;
- alterar importes;
- alterar impuestos;
- aprobar reembolsos;
- cambiar estados internos.

---

# 67. Acceso del Superadmin

Superadmin podrá:

- configurar precios;
- configurar impuestos;
- administrar pasarelas;
- conciliar;
- confirmar pagos manuales;
- gestionar devoluciones;
- gestionar contracargos;
- revisar fraude;
- emitir ajustes;
- ver reportes.

---

# 68. Otros roles

Gerente, Secretaría, Usuario y Gestor del ERP no tendrán
acceso al Billing SaaS, salvo permiso específico.

La facturación SaaS corresponde al Administrador Propietario.

---

# 69. Workers

Workers de Billing podrán:

- generar Órdenes;
- emitir comprobantes;
- procesar Webhooks;
- conciliar;
- enviar recordatorios;
- ejecutar renovaciones;
- actualizar estados.

Cada Worker tendrá identidad técnica limitada.

---

# 70. Colas

Las operaciones económicas deberán utilizar colas cuando corresponda.

Ejemplos:

- emisión de comprobante;
- conciliación;
- webhook;
- reembolso;
- notificación;
- renovación masiva.

---

# 71. Tolerancia a fallos

Si una pasarela no responde:

- no duplicar;
- no asumir éxito;
- mantener PENDING;
- reintentar con límites;
- consultar estado;
- alertar;
- conservar trazabilidad.

---

# 72. Recuperación

El Billing Engine deberá poder reconstruir el estado económico desde:

- eventos;
- Órdenes;
- pagos;
- Webhooks;
- comprobantes;
- conciliaciones;
- auditoría.

---

# 73. Backups

La información económica deberá incluirse en backups protegidos.

Los comprobantes y evidencias deberán mantenerse
según políticas de retención.

---

# 74. Privacidad

Los datos económicos y fiscales deberán tratarse como sensibles.

El acceso será limitado y auditado.

---

# 75. API

La API deberá permitir:

- consultar perfil;
- consultar Órdenes;
- crear Payment Intent;
- consultar pago;
- subir voucher;
- descargar comprobante;
- solicitar devolución;
- consultar historial.

Todas las acciones deberán validar Tenant y permisos.

---

# 76. Integración con Subscription Engine

Cuando un pago sea confirmado:

BILLING ENGINE
↓
EMITE EVENTO
↓
SUBSCRIPTION ENGINE
↓
ACTIVA O RENUEVA
↓
TENANT ACTIVE

Billing no modificará directamente todos los permisos del Tenant.

Emitirá eventos confiables al Subscription Engine.

---

# 77. Integración con Tenant Lifecycle

Los eventos económicos podrán provocar:

PAYMENT_CONFIRMED
→ ACTIVE

PAYMENT_FAILED
→ PAYMENT_PENDING

PAST_DUE
→ GRACE_PERIOD

GRACE_EXPIRED
→ SUSPENDED

REFUND
→ REVIEW

CHARGEBACK
→ UNDER_REVIEW

---

# 78. Integración con NEXUS

NEXUS podrá:

- detectar anomalías;
- proyectar ingresos;
- alertar morosidad;
- detectar fraude;
- recomendar Plan;
- analizar churn;
- prever consumo.

NEXUS no podrá confirmar pagos ni aprobar devoluciones
sin autorización.

---

# 79. Flujo general

PLAN
↓
PERIODO
↓
ORDEN DE COBRO
↓
PAYMENT INTENT
↓
PASARELA O PAGO MANUAL
↓
CONFIRMACIÓN
↓
CONCILIACIÓN
↓
COMPROBANTE
↓
RENOVACIÓN
↓
AUDITORÍA

---

# 80. Reglas supremas

## Regla Suprema 1

EL BILLING SaaS ES INDEPENDIENTE DEL MÓDULO DE PAGOS DEL ERP.

## Regla Suprema 2

TODA OPERACIÓN ECONÓMICA PERTENECE A UN TENANT.

## Regla Suprema 3

NINGÚN PAGO SE CONFIRMARÁ SOLO POR UNA RESPUESTA DEL NAVEGADOR.

## Regla Suprema 4

LOS WEBHOOKS DEBERÁN SER VERIFICADOS E IDEMPOTENTES.

## Regla Suprema 5

UNA TRANSACCIÓN CONFIRMADA SOLO PODRÁ GENERAR UNA RENOVACIÓN.

## Regla Suprema 6

TODO IMPORTE, IMPUESTO, DESCUENTO Y TIPO DE CAMBIO
DEBERÁ CONSERVAR SU VERSIÓN HISTÓRICA.

## Regla Suprema 7

LOS DATOS DE TARJETA NO SE ALMACENARÁN DIRECTAMENTE
CUANDO EXISTA TOKENIZACIÓN.

## Regla Suprema 8

LAS DEVOLUCIONES Y CONTRACARGOS DEBERÁN SER AUDITABLES.

## Regla Suprema 9

LOS PAGOS MANUALES REQUERIRÁN EVIDENCIA Y VALIDACIÓN.

## Regla Suprema 10

BILLING EMITIRÁ EVENTOS AL SUBSCRIPTION ENGINE;
NO REESCRIBIRÁ DIRECTAMENTE EL CICLO DE VIDA DEL TENANT.

## Regla Suprema 11

LOS COMPROBANTES DEL SaaS NO SE MEZCLARÁN CON LOS CPE
PROCESADOS DENTRO DE LOS TENANTS.

## Regla Suprema 12

TODA OPERACIÓN DE FACTURACIÓN PODRÁ RECONSTRUIRSE
DESDE SU HISTORIAL Y AUDITORÍA.
