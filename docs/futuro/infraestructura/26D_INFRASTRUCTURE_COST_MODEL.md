# 26D — INFRASTRUCTURE COST MODEL

# FACT CENTRAL

## Modelo Oficial de Costos de Infraestructura de NEXUS

**Versión:** 2.0
**Estado:** Arquitectura económica definida
**Modelo:** Costos dinámicos vinculados a capacidad y crecimiento

---

# 1. Objetivo

Definir cómo FACT CENTRAL y NEXUS deberán calcular, proyectar, comparar y controlar los costos asociados con la infraestructura tecnológica.

El modelo deberá transformar necesidades técnicas en impacto económico comprensible para Administración.

Debe responder permanentemente:

> ¿CUÁNTO CUESTA OPERAR FACT CENTRAL HOY?

> ¿CUÁNTO COSTARÁ MANTENERLO MAÑANA?

> ¿CUÁNTO COSTARÁ ESCALAR?

> ¿QUÉ OPCIÓN DE INFRAESTRUCTURA ES MÁS CONVENIENTE?

---

# 2. Principio fundamental

> TODA DECISIÓN DE ESCALAMIENTO DEBERÁ CONOCER SU IMPACTO ECONÓMICO ANTES DE EJECUTARSE, SALVO EMERGENCIAS OPERATIVAS PREVIAMENTE AUTORIZADAS.

Capacity Planning determina la necesidad.

Infrastructure Cost Model determina el costo.

Administración decide dentro de las políticas autorizadas.

---

# 3. Relación principal

```text
DEMANDA
↓
CAPACIDAD REQUERIDA
↓
RECURSOS
↓
COSTO
↓
RECOMENDACIÓN
↓
AUTORIZACIÓN
```

---

# 4. Categorías de costos

FACT CENTRAL deberá separar como mínimo:

## Infraestructura computacional

* VPS;
* servidores;
* PCs;
* CPU;
* RAM;
* GPU.

## Almacenamiento

* SSD;
* NAS;
* Object Storage;
* almacenamiento remoto;
* crecimiento de capacidad.

## Bases de datos

* PostgreSQL;
* réplicas;
* backups;
* almacenamiento de base de datos.

## Red

* Internet;
* ancho de banda;
* transferencia;
* tráfico cloud;
* VPN.

## Edge

* Cloudflare;
* CDN;
* WAF;
* servicios de protección.

## Inteligencia Artificial

* APIs IA;
* modelos;
* tokens;
* inferencias;
* GPU.

## OCR

* procesamiento local;
* servicios externos;
* capacidad de workers.

## Observabilidad

* logs;
* métricas;
* trazas;
* almacenamiento de logs.

## Backup y Disaster Recovery

* réplicas;
* almacenamiento histórico;
* ubicación remota;
* restauraciones.

---

# 5. Costos fijos y variables

El sistema distinguirá:

## Costos fijos

Ejemplo:

```text
VPS mensual
Internet
Servidor contratado
Licencias
Servicios base
```

## Costos variables

Ejemplo:

```text
GB almacenado
GB transferido
tokens IA
OCR procesado
requests
nodos temporales
workers adicionales
```

---

# 6. Costos locales y cloud

Se deberán diferenciar:

### Infraestructura propia

Costos:

* compra;
* mantenimiento;
* energía;
* depreciación;
* Internet;
* reemplazo;
* discos;
* UPS.

### Cloud / VPS

Costos:

* mensualidad;
* CPU;
* RAM;
* almacenamiento;
* transferencia;
* backups;
* servicios gestionados.

---

# 7. Modelo híbrido

FACT CENTRAL podrá utilizar:

```text
VPS
+
PC LOCAL
+
STORAGE LOCAL
+
BACKUP REMOTO
```

El Cost Model deberá calcular el costo combinado.

---

# 8. Costo por nodo

Cada nodo deberá tener un perfil económico.

Ejemplo:

```text
NODE_ID: VPS-01

Costo mensual:
XXX

CPU:
X

RAM:
X

Storage:
X

Transferencia:
X

Rol:
API / Processing
```

---

# 9. PCs propias

Las PCs internas no deberán tratarse como costo cero.

Se podrá considerar:

```text
Costo de adquisición
÷
vida útil esperada
```

más:

* energía;
* mantenimiento;
* discos;
* reemplazos;
* Internet.

---

# 10. Costos de almacenamiento

El modelo deberá calcular:

```text
CAPACIDAD ACTUAL
+
CRECIMIENTO
+
RÉPLICAS
+
BACKUPS
```

Ejemplo conceptual:

```text
Datos útiles:
2 TB

Replica:
2 TB

Backup:
4 TB

Capacidad real requerida:
8 TB
```

El costo no deberá calcularse únicamente sobre los datos originales.

---

# 11. Storage Overhead

Cada TB de información productiva puede requerir más de 1 TB físico debido a:

* réplicas;
* backups;
* versiones;
* OCR;
* miniaturas;
* metadatos;
* logs.

Se utilizará un:

**Storage Multiplication Factor**

Ejemplo conceptual:

```text
Datos productivos = 1 TB

Factor = 2.5

Capacidad necesaria:
2.5 TB
```

El factor será configurable.

---

# 12. Costos de crecimiento de SSD

Cuando NEXUS proyecte expansión:

```text
Storage actual:
1 TB

Utilización:
78 %

Recomendación:
Agregar 2 TB
```

Cost Model deberá mostrar:

```text
Costo adquisición
Costo instalación
Costo replicación
Costo backup adicional
Costo operativo
```

---

# 13. Capacity Tier Cost

Cada Capacity Tier tendrá un costo estimado.

Ejemplo conceptual:

| Tier   | Capacidad       | Costo estimado |
| ------ | --------------- | -------------- |
| Tier 1 | 2,000 usuarios  | Configurable   |
| Tier 2 | 5,000 usuarios  | Configurable   |
| Tier 3 | 10,000 usuarios | Configurable   |
| Tier 4 | 25,000 usuarios | Configurable   |

Los valores reales dependerán de infraestructura y proveedor.

---

# 14. No vincular costo únicamente a usuarios

El costo real dependerá principalmente de:

* concurrencia;
* documentos;
* OCR;
* IA;
* almacenamiento;
* transferencia;
* eventos;
* procesamiento.

Por eso:

```text
5,000 usuarios ligeros
```

pueden costar menos que:

```text
1,000 usuarios
con cargas documentales masivas
```

---

# 15. Cost per Document

NEXUS podrá calcular:

```text
COSTO TOTAL DOCUMENTAL
÷
DOCUMENTOS PROCESADOS
```

para obtener:

**Costo promedio por documento**

---

# 16. Cost per Expedient

También podrá calcular:

```text
Infraestructura asociada
÷
Expedientes procesados
```

---

# 17. Cost per Tenant

Cuando sea útil:

```text
Costo generado por Tenant
```

considerando:

* storage;
* documentos;
* OCR;
* IA;
* API;
* transferencia;
* procesamiento.

Esto será útil para decisiones comerciales futuras.

---

# 18. Cost per User

También podrá calcularse un costo promedio por usuario.

Pero deberá utilizarse como indicador ejecutivo y no como única métrica técnica.

---

# 19. Costos API IA

Toda integración de IA deberá registrar, cuando sea posible:

```text
Proveedor
Modelo
Solicitudes
Tokens entrada
Tokens salida
Costo
Fecha
Tenant
Proceso
Agente
```

---

# 20. Presupuesto IA

Administración podrá definir:

```text
Presupuesto diario
Presupuesto mensual
Presupuesto por tenant
Presupuesto por agente
```

---

# 21. Límites de IA

Ante aproximación al presupuesto:

```text
80 % → aviso
90 % → advertencia
100 % → política definida
```

La política podrá:

* solicitar aprobación;
* utilizar modelo alternativo;
* reducir procesos secundarios;
* suspender tareas no críticas.

---

# 22. Costos OCR

OCR deberá calcular:

```text
Documentos
Páginas
Tiempo
Workers
GPU/CPU
Servicio externo
```

permitiendo comparar:

```text
OCR LOCAL
vs
OCR CLOUD
```

---

# 23. Costos de red

El modelo deberá registrar:

* ancho de banda;
* datos entrantes;
* datos salientes;
* transferencia interregional;
* transferencia cloud;
* uso mensual.

---

# 24. Costos de Cloudflare

Cloudflare deberá modelarse como servicio independiente.

El Cost Model registrará:

```text
Plan
Servicios habilitados
Consumo
Costo mensual
```

Los precios específicos deberán obtenerse del proveedor durante implementación.

---

# 25. Costos PostgreSQL

Incluirán:

* nodo Primary;
* réplica;
* almacenamiento;
* backup;
* transferencia;
* mantenimiento;
* servicios gestionados cuando existan.

---

# 26. Costos de Redis / Queue

Deberán incluir:

* memoria;
* nodo;
* réplica;
* persistencia;
* transferencia.

---

# 27. Costos de observabilidad

Logs y métricas también consumen almacenamiento.

Se deberá calcular:

```text
Logs diarios
Retención
Compresión
Storage
Transferencia
```

---

# 28. Retención de logs

No todos los logs deberán mantenerse indefinidamente en almacenamiento rápido.

Podrán utilizarse niveles:

```text
HOT
WARM
ARCHIVE
```

---

# 29. Storage Tiers

El almacenamiento podrá clasificarse económicamente.

## HOT STORAGE

Documentos de acceso frecuente.

Mayor rendimiento.

## WARM STORAGE

Acceso ocasional.

## COLD STORAGE

Archivo histórico.

Menor costo.

---

# 30. Movimiento entre Tiers

NEXUS podrá recomendar:

```text
Documento sin acceso durante X tiempo
↓
WARM
↓
COLD
```

sin perder identidad documental.

---

# 31. Reglas legales y operativas

La reducción de costo por archivado nunca deberá violar:

* requisitos legales;
* retención documental;
* disponibilidad necesaria;
* auditoría;
* seguridad.

---

# 32. Disaster Recovery Cost

El modelo deberá calcular el costo de:

```text
Primary
+
Replica
+
Backup
+
Remote Backup
```

La alta disponibilidad tendrá un costo visible.

---

# 33. Costo de no tener redundancia

NEXUS también podrá mostrar riesgos.

Ejemplo:

```text
Ahorro por eliminar réplica:
S/ X

Riesgo:
Pérdida de disponibilidad crítica
```

Esto evitará tomar decisiones únicamente por precio.

---

# 34. Cost vs Risk

Toda recomendación importante podrá mostrar:

```text
COSTO
↓
BENEFICIO
↓
RIESGO
```

---

# 35. Escalamiento económico

Cuando Capacity Manager recomiende:

```text
Tier 1
→
Tier 2
```

Cost Model deberá calcular:

```text
Costo actual
Costo futuro
Diferencia
Variación %
```

---

# 36. Ejemplo administrativo

```text
CAPACIDAD ACTUAL:
Tier 1

Costo mensual:
S/ XXX

CAPACIDAD RECOMENDADA:
Tier 2

Costo mensual estimado:
S/ XXX

Incremento:
S/ XXX

Motivo:
Crecimiento proyectado
```

---

# 37. Aprobación

El Administrador podrá recibir:

```text
[ APROBAR ]
[ POSPONER ]
[ CAMBIAR OPCIÓN ]
```

---

# 38. Autoescalamiento con presupuesto

Administración podrá definir:

```text
Presupuesto máximo automático:
S/ X / mes
```

Dentro de ese límite NEXUS podrá ejecutar escalamiento previamente autorizado.

---

# 39. Escalamiento fuera de presupuesto

Si una acción supera el límite:

```text
APPROVAL_REQUIRED
```

No deberá ejecutarse automáticamente salvo política de emergencia.

---

# 40. Emergency Budget

Administración podrá definir un:

**Emergency Infrastructure Budget**

para situaciones críticas.

Ejemplo:

```text
Capacidad crítica
↓
Escalamiento necesario
↓
Costo dentro de Emergency Budget
↓
Autoaprobar
```

---

# 41. Forecasting de costos

NEXUS deberá proyectar:

```text
Costo próximo mes
Costo 3 meses
Costo 6 meses
Costo 12 meses
```

basándose en crecimiento real.

---

# 42. Cost Growth Rate

Se calculará:

```text
Variación mensual
Variación trimestral
Variación anual
```

---

# 43. Anomalías de costo

Si un servicio aumenta inesperadamente:

```text
Costo promedio:
S/ 500

Costo actual:
S/ 1,200
```

NEXUS deberá generar:

```text
COST_ANOMALY
```

---

# 44. Causas de anomalía

Podrán incluir:

* incremento documental;
* ataque;
* error;
* loop;
* exceso de IA;
* transferencia anormal;
* crecimiento de logs;
* almacenamiento inesperado.

---

# 45. Cost Attribution

Los costos deberán poder atribuirse a:

```text
Tenant
Usuario
Gestor
Motor
Agente
Servicio
Nodo
Proceso
```

cuando la telemetría lo permita.

---

# 46. Cost Center

Podrán existir centros de costo:

```text
INFRASTRUCTURE
AI
OCR
STORAGE
DATABASE
NETWORK
OBSERVABILITY
BACKUP
```

---

# 47. Cost Efficiency Score

NEXUS podrá calcular:

```text
Costo
vs
Capacidad utilizada
```

y producir un:

**Cost Efficiency Score**

Ejemplo:

```text
100 = excelente
80 = saludable
60 = revisar
40 = ineficiente
20 = crítico
```

---

# 48. Recursos infrautilizados

Si:

```text
NODE-05
CPU promedio: 4 %
durante 30 días
```

NEXUS podrá recomendar:

```text
reducir nodo
apagar
reasignar
consolidar
```

---

# 49. Recursos saturados

Si un recurso está continuamente al límite:

```text
NODE-02
CPU 90 %
```

NEXUS podrá comparar:

```text
aumentar servidor
vs
agregar nodo
```

y recomendar la opción más conveniente.

---

# 50. Optimización automática

Dentro de políticas autorizadas NEXUS podrá:

* apagar workers innecesarios;
* reducir capacidad temporal;
* mover archivos a storage más económico;
* reorganizar procesos;
* consolidar nodos.

---

# 51. No sacrificar integridad por costo

> NINGUNA OPTIMIZACIÓN ECONÓMICA PODRÁ ELIMINAR LOS NIVELES MÍNIMOS DE SEGURIDAD, BACKUP O INTEGRIDAD DEFINIDOS POR FACT CENTRAL.

---

# 52. Comprar vs alquilar

El sistema podrá comparar:

```text
PC / SERVER PROPIO
vs
VPS
vs
CLOUD
```

considerando:

* inversión inicial;
* costo mensual;
* electricidad;
* mantenimiento;
* disponibilidad;
* escalabilidad;
* redundancia.

---

# 53. Amortización

Los equipos propios podrán manejar:

```text
Costo adquisición
Vida útil
Costo mensual equivalente
```

---

# 54. Energía

Para nodos locales podrán registrarse:

```text
Watts promedio
Horas
Costo kWh
```

para estimar costo operativo.

---

# 55. UPS y protección

Infraestructura local crítica podrá incluir costos de:

* UPS;
* estabilización;
* baterías;
* reemplazos.

---

# 56. Costos de reemplazo

El modelo podrá reservar una proyección para:

* SSD;
* discos;
* UPS;
* servidores;
* PCs.

---

# 57. Depreciación tecnológica

NEXUS podrá considerar que determinados equipos pierden eficiencia económica con el tiempo.

---

# 58. Comparación de escenarios

Ejemplo:

```text
ESCENARIO A
2 VPS + Storage Cloud

ESCENARIO B
1 VPS + 3 PCs + Storage Local

ESCENARIO C
Cloud completo
```

Para cada uno:

```text
Costo
Capacidad
Disponibilidad
Riesgo
Complejidad
```

---

# 59. TCO

El modelo deberá calcular:

**Total Cost of Ownership**

incluyendo:

```text
Compra
Operación
Mantenimiento
Energía
Servicios
Storage
Backups
Red
IA
```

---

# 60. Dashboard económico

Ruta propuesta:

**Administración → Infraestructura → Costos**

Deberá mostrar:

```text
Costo mensual actual
Costo proyectado
Costo por categoría
Costo por nodo
Costo por tenant
Costo por documento
Variación
Presupuesto
Anomalías
Recomendaciones
```

---

# 61. Alertas

Ejemplo:

```text
INFRASTRUCTURE COST ALERT

Presupuesto:
S/ X

Proyección:
S/ Y

Diferencia:
+Z %
```

---

# 62. Integración con Capacity Planning

`26C_CAPACITY_PLANNING.md` determina:

> CUÁNTO NECESITAMOS.

Este documento determina:

> CUÁNTO CUESTA.

---

# 63. Integración con Infrastructure Topology

`26A_INFRASTRUCTURE_TOPOLOGY.md` indica:

> QUÉ RECURSOS EXISTEN Y DÓNDE ESTÁN.

Cost Model asigna costo a esos recursos.

---

# 64. Integración con Disaster Recovery

`26B_DISASTER_RECOVERY_PLAN.md` define redundancia y recuperación.

Cost Model calcula cuánto cuesta mantener esa protección.

---

# 65. Integración con Resource Engine

`15_RESOURCE_ENGINE.md` podrá proporcionar utilización real de infraestructura.

Esto permitirá calcular eficiencia económica.

---

# 66. Integración con Executive Intelligence

`16_EXECUTIVE_INTELLIGENCE_ENGINE.md` podrá transformar datos técnicos en recomendaciones para Administración.

---

# 67. Integración con System Health

`26E_SYSTEM_HEALTH_MODEL.md` aportará:

```text
Health
Utilization
Performance
Capacity
```

para evaluar si el gasto está produciendo capacidad útil.

---

# 68. Integración con Autonomous Operations

`26F_AUTONOMOUS_OPERATIONS_CENTER.md` podrá utilizar costo para decidir entre múltiples alternativas operativas.

---

# 69. Ciclo económico autónomo

```text
SYSTEM HEALTH
↓
CAPACITY PLANNING
↓
RESOURCE ENGINE
↓
COST MODEL
↓
EXECUTIVE INTELLIGENCE
↓
ADMIN APPROVAL
↓
ORCHESTRATION
↓
NEW INFRASTRUCTURE
↓
SYSTEM HEALTH
```

---

# 70. Regla de precio

Los precios de proveedores nunca deberán quedar escritos permanentemente en los algoritmos.

Deberán almacenarse como parámetros actualizables.

Ejemplo:

```text
provider
service
currency
unit
unit_price
effective_date
```

---

# 71. Historial de precios

El sistema deberá mantener historial cuando sea necesario:

```text
Servicio X

Enero: S/ ...
Febrero: S/ ...
Marzo: S/ ...
```

permitiendo analizar variaciones.

---

# 72. Moneda

Los costos podrán almacenarse en:

* PEN;
* USD;
* otras monedas.

Los reportes administrativos podrán convertirlos a una moneda base.

---

# 73. Costos estimados vs reales

Cada gasto podrá clasificarse como:

```text
ESTIMATED
ACTUAL
FORECAST
```

Esto permitirá evaluar la precisión de las proyecciones.

---

# 74. Variance Analysis

Se calculará:

```text
COSTO PROYECTADO
vs
COSTO REAL
```

para mejorar futuras estimaciones.

---

# 75. Presupuesto mensual

Administración podrá definir un presupuesto global de infraestructura.

Ejemplo conceptual:

```text
Presupuesto mensual:
S/ XXXX

Consumido:
XX %

Proyección:
XX %
```

---

# 76. Reserva operativa

Podrá mantenerse capacidad presupuestaria disponible para:

* picos;
* emergencias;
* recuperación;
* crecimiento extraordinario.

---

# 77. Principios obligatorios

## PRINCIPIO 1

El crecimiento técnico deberá tener visibilidad económica.

## PRINCIPIO 2

Los costos no estarán escritos rígidamente en código.

## PRINCIPIO 3

El costo por usuario no será la única métrica.

## PRINCIPIO 4

Almacenamiento deberá calcular originales, réplicas y backups.

## PRINCIPIO 5

La reducción de costo nunca deberá comprometer integridad.

## PRINCIPIO 6

El autoescalamiento respetará presupuestos autorizados.

## PRINCIPIO 7

NEXUS deberá detectar gastos anormales.

## PRINCIPIO 8

Administración conservará el control de decisiones económicas relevantes.

---

# 78. Regla Suprema

> FACT CENTRAL DEBERÁ UTILIZAR LA INFRAESTRUCTURA NECESARIA PARA GARANTIZAR OPERACIÓN, SEGURIDAD Y CRECIMIENTO, PERO NEXUS DEBERÁ EVITAR PAGAR POR CAPACIDAD INNECESARIA.

---

# 79. Estado del documento

**INFRASTRUCTURE COST MODEL — ARQUITECTURA ECONÓMICA DEFINIDA**

Los precios reales de VPS, Cloudflare, almacenamiento, APIs, IA, OCR, energía y otros servicios deberán registrarse durante implementación y mantenerse como datos configurables.

El modelo económico no dependerá de un proveedor específico y podrá evolucionar conforme cambien los costos reales de infraestructura.
