# 26B_DISASTER_RECOVERY_PLAN.md

# FACT CENTRAL

## DISASTER RECOVERY PLAN

### Plan Oficial de Recuperación ante Desastres (DRP)

Versión 1.0

---

# Objetivo

Definir los procedimientos, responsabilidades y mecanismos necesarios para recuperar la operación de FACT CENTRAL ante cualquier incidente que afecte la disponibilidad, integridad o continuidad del servicio.

Este documento forma parte de la estrategia de Continuidad del Negocio (BCP).

---

# Filosofía

Los errores son inevitables.

La pérdida de información no.

FACT CENTRAL deberá estar preparado para continuar operando incluso ante fallas críticas.

---

# Objetivos

Garantizar:

- continuidad operativa;
- protección de la información;
- recuperación rápida;
- mínima pérdida de datos;
- trazabilidad completa;
- recuperación automática cuando sea posible.

---

# Principios

Toda estrategia de recuperación deberá ser:

- documentada;
- probada;
- automatizada;
- auditable;
- segura;
- repetible.

---

# Riesgos Considerados

• Falla del servidor.

• Corrupción de Base de Datos.

• Eliminación accidental.

• Error humano.

• Ataque ransomware.

• Ataque DDoS.

• Incendio.

• Corte eléctrico.

• Caída de Internet.

• Falla del Storage.

• Falla de Redis.

• Falla del Event Bus.

• Falla de APIs externas.

• Corrupción documental.

• Error de despliegue.

---

# Activos Críticos

Usuarios.

Empresas.

Expedientes.

Documentos.

Productos.

Pagos.

Eventos.

Auditoría.

Configuraciones.

Modelos IA.

Knowledge Graph.

Memory System.

---

# Niveles de Incidente

## Nivel 1

Incidente menor.

Sin pérdida de datos.

Recuperación inmediata.

---

## Nivel 2

Incidente moderado.

Interrupción parcial.

Recuperación en minutos.

---

## Nivel 3

Incidente crítico.

Servicios principales afectados.

Recuperación prioritaria.

---

## Nivel 4

Desastre total.

Pérdida del servidor principal.

Activación completa del DRP.

---

# RTO

Recovery Time Objective

Tiempo máximo para restaurar el servicio.

Objetivos recomendados:

Autenticación

15 minutos

Backend

30 minutos

Frontend

30 minutos

PostgreSQL

60 minutos

Storage

90 minutos

Dashboard

60 minutos

IA

120 minutos

---

# RPO

Recovery Point Objective

Pérdida máxima aceptable de información.

Objetivo recomendado

≤ 15 minutos.

---

# Estrategia de Backups

Base de Datos

Incrementales cada hora.

Diarios.

Semanales.

Mensuales.

---

Storage

Incremental diario.

Completo semanal.

---

Configuraciones

Cada modificación importante.

---

Documentos

Replicación automática.

---

# Política 3-2-1

Mantener:

3 copias.

2 medios distintos.

1 copia fuera del sitio principal.

---

# Replicación

PostgreSQL

Replica de lectura.

Replica caliente.

Failover automático.

---

Storage

Replica local.

Replica remota.

---

Redis

Sentinel.

Replica.

---

# Recuperación PostgreSQL

Procedimiento

1.

Detener escritura.

2.

Verificar integridad.

3.

Restaurar respaldo.

4.

Aplicar WAL.

5.

Validar datos.

6.

Reabrir servicio.

---

# Recuperación Storage

Verificar HASH.

Restaurar archivos.

Reconstruir índices.

Validar documentos.

Actualizar metadatos.

---

# Recuperación de NEXUS

Reiniciar motores.

Recuperar estados.

Recuperar Scheduler.

Recuperar Event Bus.

Recuperar Agentes.

Verificar consistencia.

---

# Recuperación de Agentes

Cada agente deberá poder:

detenerse;

reiniciarse;

reanudar tareas;

recuperar contexto;

publicar eventos pendientes.

---

# Recuperación del Event Bus

Restaurar cola.

Reprocesar eventos.

Evitar duplicados.

Registrar auditoría.

---

# Recuperación de Redis

Reconstruir cache.

Restaurar locks.

Reprogramar Scheduler.

---

# APIs Externas

Si SUNAT falla

↓

Entrar en modo degradado.

Reintentar automáticamente.

Registrar incidente.

Notificar.

Lo mismo aplica para:

APIPERU.

OpenAI.

Correo.

WhatsApp.

---

# Recuperación Manual

El administrador podrá ejecutar:

Restaurar Base.

Restaurar Storage.

Reprocesar OCR.

Reprocesar Eventos.

Reprocesar Misiones.

Reindexar Base.

Reconstruir Dashboard.

---

# Simulacros

Realizar simulacros:

Mensuales.

Trimestrales.

Anuales.

Registrar resultados.

---

# Monitoreo

Detectar:

Caídas.

Latencia.

Errores.

Uso de CPU.

Uso de RAM.

Disco.

Colas.

Backups.

---

# Alertas

Notificar automáticamente:

Administrador.

Gerencia.

Equipo Técnico.

Según el nivel del incidente.

---

# Auditoría

Registrar:

Incidente.

Fecha.

Hora.

Impacto.

Responsable.

Acciones.

Resultado.

Tiempo de recuperación.

---

# Checklist de Recuperación

✓ Detectar incidente.

✓ Clasificar nivel.

✓ Notificar.

✓ Aislar problema.

✓ Restaurar servicio.

✓ Validar integridad.

✓ Reanudar operaciones.

✓ Registrar auditoría.

✓ Analizar causa raíz.

✓ Proponer mejoras.

---

# Integración

Este documento se integra con:

26_DEPLOYMENT_ARCHITECTURE.md

26A_INFRASTRUCTURE_TOPOLOGY.md

27_SECURITY_ARCHITECTURE.md

24_EVENT_CATALOG.md

25_AGENT_CATALOG.md

20_BACKEND_IMPLEMENTATION_PLAN.md

---

# Roadmap

Nivel 1

Backups automáticos.

Nivel 2

Replicación.

Nivel 3

Failover automático.

Nivel 4

Cluster activo-activo.

Nivel 5

Recuperación geográfica.

---

# Regla Suprema

FACT CENTRAL deberá estar preparado para recuperarse de cualquier incidente sin comprometer la integridad de la información, la continuidad del negocio ni la trazabilidad del sistema.

Todo componente crítico deberá contar con un procedimiento documentado de recuperación, validado mediante pruebas periódicas y respaldado por mecanismos automáticos siempre que sea posible.
