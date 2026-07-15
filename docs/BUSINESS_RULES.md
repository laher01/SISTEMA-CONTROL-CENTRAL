# BUSINESS_RULES.md
# FACT CENTRAL
## Reglas de Negocio del ERP

---

# Objetivo

Este documento define las reglas funcionales del ERP FACT CENTRAL.

Las reglas aquí establecidas tienen prioridad sobre cualquier implementación técnica.

Todo módulo del sistema deberá respetarlas.

---

# CAPÍTULO 1
## Expedientes

### Regla 1

Todo documento pertenece obligatoriamente a un expediente.

Nunca existirán documentos huérfanos.

---

### Regla 2

Cada expediente será único.

Su identificación lógica estará formada por

RUC Receptor
+
Tipo Documento
+
Serie
+
Correlativo
+
RUC Emisor

Internamente utilizará UUID.

---

### Regla 3

Un expediente nunca podrá contener dos Facturas principales.

---

### Regla 4

Un expediente puede contener múltiples documentos secundarios.

Ejemplo

Correos

WhatsApp

Cotizaciones

Voucher

Retenciones

Fotografías

---

# CAPÍTULO 2
## Documentos

### Regla 5

Los documentos aceptados serán

FACT

GUIA

TRANSPORTISTA

RHE

VCHR

RET

WHATSAPP

CORREO

COTIZACION

REQUERIMIENTO

FOTO

---

### Regla 6

Todo archivo conservará el original.

Nunca será modificado.

---

### Regla 7

Las copias procesadas serán independientes del archivo original.

---

### Regla 8

Todo archivo tendrá HASH.

El HASH será utilizado para detectar duplicados.

---

### Regla 9

El nombre del archivo nunca será utilizado para detectar duplicados.

Siempre se utilizará el contenido.

---

# CAPÍTULO 3
## Procesamiento

### Regla 10

Todo documento subido primero ingresará al Área General.

---

### Regla 11

El Motor IA clasificará automáticamente.

---

### Regla 12

Si existe duda,

el documento quedará pendiente de validación.

---

### Regla 13

La IA nunca eliminará documentos.

Solo propondrá acciones.

---

### Regla 14

Todo procesamiento quedará registrado.

---

# CAPÍTULO 4
## Empresas

### Regla 15

Toda Empresa Emisora nueva será creada automáticamente.

---

### Regla 16

Toda Empresa Receptora nueva será creada automáticamente.

---

### Regla 17

Si una empresa no pertenece a la base autorizada,

el expediente quedará pendiente.

---

### Regla 18

El Administrador decidirá si incorpora dicha empresa.

---

# CAPÍTULO 5
## Dashboard

### Regla 19

Todo expediente mostrará su estado.

---

### Regla 20

VERDE

Factura

Guía

Voucher

Completos.

---

### Regla 21

NARANJA

Falta uno de los documentos principales.

---

### Regla 22

ROJO

Después del día 7 del mes siguiente,

continúa faltando documentación principal.

---

### Regla 23

AMARILLO

Solo faltan documentos opcionales.

Correo

WhatsApp

Cotización

---

# CAPÍTULO 6
## Tributario

### Regla 24

Toda factura mayor a S/ 1,999.99 será considerada bancarizada.

---

### Regla 25

Toda factura menor o igual a S/ 1,999.99 será considerada no bancarizada.

---

### Regla 26

El sistema calculará automáticamente

Monto Bancarizado

Monto No Bancarizado

---

### Regla 27

El sistema verificará

Detracción

Retención

Agente de Retención

---

### Regla 28

Cuando la empresa receptora sea Agente de Retención,

la IA sugerirá validar el porcentaje correspondiente antes de cerrar el expediente.

---

# CAPÍTULO 7
## IA

### Regla 29

La IA aprenderá continuamente.

---

### Regla 30

Todo documento corregido manualmente alimentará el entrenamiento futuro.

---

### Regla 31

La IA asignará un porcentaje de confianza.

---

### Regla 32

Cuando la confianza sea menor al límite definido,

se solicitará confirmación del usuario.

---

# CAPÍTULO 8
## Pagos

### Regla 33

Las comisiones serán calculadas automáticamente.

---

### Regla 34

Cada Usuario podrá tener porcentajes distintos.

---

### Regla 35

Los cálculos nunca modificarán la información original.

---

### Regla 36

Todo cálculo podrá recalcularse.

---

# CAPÍTULO 9
## Auditoría

### Regla 37

Toda acción quedará registrada.

---

### Regla 38

Toda eliminación será lógica.

Nunca física.

---

### Regla 39

Todo acceso será registrado.

---

### Regla 40

Todo cambio de permisos quedará registrado.

---

# CAPÍTULO 10
## Seguridad

### Regla 41

Los Gestores solo visualizarán su información.

---

### Regla 42

Los Usuarios visualizarán únicamente sus Gestores.

---

### Regla 43

Secretaría visualizará toda la información.

No podrá eliminar registros.

---

### Regla 44

Administrador tendrá acceso total.

---

# CAPÍTULO 11
## Escalabilidad

### Regla 45

Cada módulo deberá funcionar independientemente.

---

### Regla 46

Si un módulo falla,

el ERP continuará funcionando.

---

### Regla 47

Todo módulo podrá ser actualizado sin afectar a los demás.

---

### Regla 48

Toda comunicación entre módulos será mediante API.

---

# REGLA SUPREMA

El Expediente es el activo principal del ERP.

Todo gira alrededor del Expediente.

Nunca alrededor de un documento individual.
