# Regla individual de distribución de Jonatan y Javier (sin Alex)

Estado: calculadora de simulación, sin emisión ni autorización de pagos. Aplica únicamente al plan individual de JAVIER01 / Jonatan, previa asignación del Usuario/Responsable y activación formal de su plan versionado.

**Ajuste solicitado 08/10/2026:** retirar a Alex del cálculo y redistribuir los 3.000 puntos porcentuales de comisión únicamente entre:
- Gente y Lima: 2.250 % de B.
- Javier: 0.125 % de B.
- Jonatan: 0.625 % de B.
- Suma 3.000 %.

**Variables:**
- `total_emitido`: producción emitida para ese periodo y moneda.
- `base_autorizada`: importe de facturas autorizado manualmente, positivo y no superior al total emitido.
- `usar_total_emitido`: modo alternativo, requiere confirmación expresa y no admite `base_autorizada` simultánea.
- `tasas`: valores configurables; la suma debe seguir igual a 3.000 % hasta que se apruebe una nueva tasa total.
- `B`: base manual o total emitido confirmado.
- `bruto`: B × 3 % redondeado a céntimos.
- `gente_lima`: B × 2.250 %.
- `javier`: B × 0.125 %.
- `jonatan`: bruto − gente_lima − javier, para atribuir el eventual céntimo residual y conciliar.

**Ejemplos basados en capturas y redistribución nueva:**
1. B = S/ 378,000.00: bruto 11,340.00; Gente y Lima 8,505.00; Javier 472.50; Jonatan 2,362.50.
2. B = S/ 1,114,897.76: bruto 33,446.93; Gente y Lima 25,085.20; Javier 1,393.62; Jonatan 6,968.11.

**Diferencia importante**: esta distribución del 3 % se aplica a una base seleccionada para el Usuario y su Gestor; no sustituye la comisión del 3.5 % a nivel Responsable. No sumar dos veces la producción. El flujo de pagos existente `/api/v1/pagos` **no se ha conectado aún** a la calculadora: primero deben modelarse los beneficiarios, validarse sus identidades y la nueva jerarquía, definir vigencias, estados de aprobación, soportes de pago y controles de acceso. La función en `app/services/distribucion_jonatan.py` es pura y ejecutable mediante pruebas, no un comando de giro de fondos.

**Cuestión a confirmar:** el texto «Gente y Lima» figura como una sola bolsa del 2.25 % en la hoja; no se definió reparto interno entre esas dos personas o entidades. Mantenerla como un solo beneficiario lógico hasta contar con porcentajes individuales aprobados.
