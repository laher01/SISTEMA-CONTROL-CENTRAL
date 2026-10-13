# Regla individual de distribución de Jonatan y Javier (sin Alex)

Estado: calculadora de simulación, sin emisión ni autorización de pagos. Aplica únicamente al plan individual de JAVIER01 / Jonatan, previa asignación del Usuario/Responsable y activación formal de su plan versionado.

**Ajuste solicitado 08/10/2026:** retirar a Alex sin redistribuir su porcentaje. La comisión bruta sigue siendo el 3 %, pero la parte neta pagable es 2.6875 %, repartida entre:
- Gente y Lima: 2.250 % de B.
- Javier: 0.125 % de B.
- Jonatan: 0.3125 % de B.
- Suma neta 2.6875 %. La cuota 0.3125 % de Alex no se paga.

**Variables:**
- `total_emitido`: producción emitida para ese periodo y moneda.
- `base_autorizada`: importe de facturas autorizado manualmente, positivo y no superior al total emitido.
- `usar_total_emitido`: modo alternativo, requiere confirmación expresa y no admite `base_autorizada` simultánea.
- `tasas`: valores configurables; la suma de los beneficiarios debe ser 2.6875 % hasta que se apruebe una nueva tasa total.
- `B`: base manual o total emitido confirmado.
- `bruto`: B × 3 % redondeado a céntimos.
- `gente_lima`: B × 2.250 %.
- `javier`: B × 0.125 %.
- `neto`: B × 2.6875 %. `jonatan`: neto − gente_lima − javier, para conciliar los céntimos. `excluido_alex`: bruto − neto; no es un pago.

**Ejemplos basados en capturas y redistribución nueva:**
1. B = S/ 378,000.00: bruto 11,340.00; Gente y Lima 8,505.00; Javier 472.50; Jonatan 1,181.25; neto 10,158.75.
2. B = S/ 1,114,897.76: bruto 33,446.93; Gente y Lima 25,085.20; Javier 1,393.62; Jonatan 3,484.06; neto 29,962.88.

**Diferencia importante**: esta distribución del 3 % se aplica a una base seleccionada para el Usuario y su Gestor; no sustituye la comisión del 3.5 % a nivel Responsable. No sumar dos veces la producción. El flujo de pagos existente `/api/v1/pagos` **no se ha conectado aún** a la calculadora: primero deben modelarse los beneficiarios, validarse sus identidades y la nueva jerarquía, definir vigencias, estados de aprobación, soportes de pago y controles de acceso. La función en `app/services/distribucion_jonatan.py` es pura y ejecutable mediante pruebas, no un comando de giro de fondos.

**Cuestión a confirmar:** el texto «Gente y Lima» figura como una sola bolsa del 2.25 % en la hoja; no se definió reparto interno entre esas dos personas o entidades. Mantenerla como un solo beneficiario lógico hasta contar con porcentajes individuales aprobados.


## Especificación aprobada 12/10/2026: NEXUS y pagos por Responsable

**Alcance:** la fórmula especial de distribución corresponde exclusivamente al miembro identificado internamente como JONA01 (Jonatan Lama), dentro del equipo del Responsable autorizado. Validar tenant_id, responsable_id y usuario_id; no depender de comparaciones de nombre ni permitir aplicación transversal.

**Regla JONA01:** el Responsable elige entre (a) base manual autorizada, positiva y no mayor a la producción emitida elegible, y (b) total emitido del período confirmado expresamente. Calcular sobre la base B: Gente y Lima 2.250 %, Javier 0.125 %, Jonatan Lama 0.3125 %. Total distribuido 2.6875 %. Redondear a céntimos y conciliar la diferencia de redondeo en la participación de Jonatan. No incluir otros beneficiarios en la vista de pago. Separar cálculo de autorización, programación, registro de abonos y confirmación de pago; no ejecutar giros automáticamente.

**Resto de usuarios:** mantener el pago estándar = producción de clientes sin agente de retención × porcentaje_sin_retencion / 100 + producción de clientes con agente de retención × porcentaje_con_retencion / 100. Tomar tasas de la ficha del usuario gestionada por su Responsable, con snapshot de tasas y desglose de empresas/facturas en cada liquidación. No aplicar la fórmula de JONA01 a otros usuarios.

**Motor NEXUS por Responsable:** agregar apartado Fórmulas de pago con descripción en lenguaje natural, propuesta estructurada de expresión segura (sin ejecutar código arbitrario), variables autorizadas, simulación con casos de prueba, aprobación explícita del Responsable, versión inmutable, fecha de vigencia, activación/desactivación, historial y auditoría. La IA únicamente propone; backend valida límites, permisos, porcentajes, moneda, fechas, no duplicidad y alcance. Nunca activar una fórmula directamente desde texto libre. Las liquidaciones emitidas conservan su fórmula y valores originales. Un usuario solo puede tener una fórmula especial activa por ámbito/fecha; si no existe, se aplica la estándar.

**Seguridad y despliegue:** cambios en rama de desarrollo; tests de permisos, límites de tenant, precisión decimal, modos incompatibles, pagos parciales, solapamientos y regresión del cálculo estándar; migración reversible y CI verde antes de fusionar. El despliegue productivo se hará únicamente después de la autorización final solicitada por el usuario al concluir la implementación.
