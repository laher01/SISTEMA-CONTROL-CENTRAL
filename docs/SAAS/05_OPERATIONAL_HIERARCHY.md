# Jerarquía operativa y propiedad de datos

## Jerarquía

FACT CENTRAL separa los roles del Tenant de los recursos que administran.

SUPERADMIN pertenece a la plataforma SaaS.

Dentro de cada Tenant la jerarquía de roles es:

ADMINISTRADOR → GERENTE / SECRETARÍA → USUARIO → GESTOR

Los recursos operativos siguen la propiedad:

TENANT → USUARIO → GESTOR → DOCUMENTO → EXPEDIENTE

## Reglas de propiedad

- Un Usuario es independiente de los demás Usuarios del mismo Tenant.
- Cada Gestor pertenece a un único Usuario operativo.
- Todo documento cargado desde la operación normal conserva gestor_id y usuario_id.
- Todo expediente creado desde ese documento conserva gestor_id y usuario_id.
- Un Gestor no debe descubrir ni consultar documentos de otros Gestores.
- Un Usuario solo debe consultar sus Gestores, documentos, expedientes, proveedores y producción.
- Administrador, Gerente y Secretaría conservan los alcances definidos por el modelo de permisos.

## Creación

- El Administrador crea o invita miembros del Tenant.
- Los miembros pueden tener rol ADMINISTRADOR, GERENTE, SECRETARIA o USUARIO.
- Los Gestores se crean vinculados obligatoriamente a un miembro con rol USUARIO.
- Al seleccionar un Gestor durante la carga, el sistema deriva automáticamente el Usuario propietario.

## Expedientes RHE

Los recibos por honorarios crean expedientes de tipo RHE.

Su identificador visual usa el prefijo:

RHE-<serie>-<correlativo>

Ejemplo:

RHE-E001-15

La identidad fiscal interna continúa almacenando tipo, serie y correlativo por separado.

## Regla interna de documentación por umbral

Para la configuración actual del Tenant:

- las operaciones que alcanzan el umbral de bancarización requieren Voucher;
- las operaciones por debajo del umbral no requieren Voucher;
- la necesidad de Guía se controla con requiere_guia y, para la automatización actual, se desactiva por debajo del umbral configurado.

## Producción

El sistema debe poder acumular por:

- Usuario;
- Gestor;
- Proveedor emisor;
- Empresa receptora;
- periodo;
- moneda;
- número de expedientes;
- importe total.

Este modelo permite rastrear quién originó cada documento, a qué Usuario pertenece la operación y cuánto volumen de compra se gestiona por cada participante.
