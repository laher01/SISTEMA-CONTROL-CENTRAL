# FACT CENTRAL

# DOMAIN MODEL

Versión: 1.0

Estado: Modelo Conceptual

Última actualización: Agosto 2026

---

# PROPÓSITO

Definir todas las entidades principales del dominio de negocio de FACT CENTRAL y las relaciones existentes entre ellas.

Todo desarrollo del sistema deberá respetar este modelo.

---

# FILOSOFÍA

FACT CENTRAL no administra documentos.

FACT CENTRAL administra operaciones empresariales.

Los documentos son únicamente evidencias que forman parte de una operación.

---

# ENTIDADES PRINCIPALES

## Empresa SaaS (Tenant)

Representa la empresa cliente que utiliza FACT CENTRAL.

Cada empresa posee:

• Usuarios

• Clientes (Receptores)

• Proveedores

• Productos

• Pedidos

• Expedientes

---

## Usuario

Persona que interactúa con el sistema.

Tipos:

• Administrador

• Gerente

• Secretario(a)

• Gestor

---

## Cliente (Receptor)

Empresa para la cual se administran las compras.

El cliente es el destinatario final de las facturas de compra.

Puede tener:

• múltiples pedidos

• múltiples expedientes

• múltiples productos

---

## Proveedor

Empresa emisora de las facturas.

Puede abastecer a uno o varios clientes.

Puede participar en múltiples expedientes.

---

## Pedido

Solicitud de compras realizada por Gerencia.

Todo pedido origina una distribución hacia gestores.

Puede dividirse automáticamente.

---

## Expediente Inteligente

Representa una operación empresarial completa.

Contiene toda la documentación relacionada.

---

## Documento

Elemento documental perteneciente a un expediente.

Nunca existe aislado.

Tipos:

Factura

Guía

Voucher

Correo

WhatsApp

Imagen

PDF

XML

CDR

---

## Producto

Elemento adquirido mediante la compra.

Todo producto pertenece a una factura.

Todo producto pertenece a un proveedor.

Todo producto pertenece a un cliente.

---

## Pago

Representa la evidencia financiera de una compra.

Puede estar compuesto por:

Voucher

Transferencia

Constancia

Correo

WhatsApp

---

## Evidencia

Todo archivo utilizado para demostrar una operación.

Puede ser:

Documento

Imagen

Correo

WhatsApp

Transferencia

---

# REGLAS DEL DOMINIO

Un proveedor puede atender a muchos clientes.

Un cliente posee muchos expedientes.

Un expediente posee muchos documentos.

Todo documento pertenece a un único expediente.

Todo producto pertenece a una factura.

Toda factura pertenece a un proveedor.

Toda factura pertenece a un cliente.

Toda compra genera conocimiento.

Todo conocimiento alimenta la Inteligencia Artificial.

---

# JERARQUÍA DEL NEGOCIO

Empresa SaaS

↓

Cliente

↓

Pedido

↓

Proveedor

↓

Factura

↓

Producto

↓

Evidencias

↓

Expediente Inteligente

↓

Conocimiento

↓

Inteligencia

↓

Decisiones