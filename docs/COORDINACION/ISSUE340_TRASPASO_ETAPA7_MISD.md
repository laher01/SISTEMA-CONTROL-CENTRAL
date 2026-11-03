# Traspaso Etapa 7 y secuencia de integración MISD — Issue #340

**Estado:** coordinación preparada; NO autoriza merge ni despliegue.
**Fecha:** 2026-10-23.
**Responsables:** Etapa 7 (Landing/CMS) asignada al chat de Etapa 7 según AGENTS.md; MISD asignado a chat 3-2.2. Ninguna aprobación humana presumida.

## Entrega al responsable Etapa 7

- Revisar PR draft #341, HEAD `9118c69c32d46ffbf65dd535add31b84f94e671c`.
- Origen del problema: migración 0039 sembraba `activa=TRUE`; 0041 cambiaba solo el default de base de datos.
- Solución propuesta en #341: semilla y default de 0039 pasan a FALSE para instalaciones desde cero. Los endpoints de Landing en main ya devuelven/crean FALSE cuando falta la fila.
- Confirmar expresamente que es aceptable modificar la migración histórica 0039 para nuevas instalaciones; la migración no vuelve a ejecutarse en instalaciones ya actualizadas. Comprobar política de conservación y plan de rollback.
- CI propio #341: cinco checks success; ensayo combinado sobre main vigente en #376 HEAD `c88eef3d91dc95435ca797de02266bb60e6add86`: ocho checks success, 617 pytest aprobadas, 3 integraciones, upgrade/downgrade de Alembic 0041→0042 y conservación de estados TRUE/FALSE en PostgreSQL.
- Solicitar revisión explícita del responsable Etapa 7 y registrar en #340/PR #341 su aprobación o correcciones; **un comentario técnico no sustituye una aprobación de GitHub**.

## Secuencia exacta, condicionada

1. **Congelar hechos y SHA:** consultar HEAD de main y PRs #341, #292, #336 y #376, checks y threads justo antes de cualquier integración. Ante cambio, rehacer comparaciones y pruebas.
2. **Etapa 7 primero:** propietario revisa #341, la política de cambios de 0039 y sus pruebas; reparar hallazgos únicamente en rama propia. Tras aprobación formal y autorización I específica, integrar #341 en main, revisando que el merge no provoque ningún despliegue.
3. **MISD #292:** actualizar una rama de integración independiente desde nuevo main; trasladar cambios MISD sin sobrescribir cambios posteriores de modelos compartidos (especialmente `ConfiguracionLandingGlobal.activa=False`) y respetar `0041` de main.
4. **Dependencia #336:** aplicar correcciones de bloqueo/migración mediante PR #336 hacia la rama MISD; nunca fusionar #336 directamente en main. Revisar coherencia 0040→0041→0042, permisos tenant, retención, pagos, trazabilidad.
5. **Certificar:** verificar PostgreSQL desde cero y escenarios existentes TRUE/FALSE; downgrade y re-upgrade hasta 0042; tests backend, integración, browser, build, common-gate; evaluar conflictos y regresiones.
6. **Hilos P1/P2:** P1 solo resolver después de constatar autoría/orden correcto de 0041 y que la dependencia de MISD pertenece al historial aprobado de Etapa 7; P2 solo después de la corrección de inicialización aprobada y reflejada en rama destino con CI. Dejar abiertos mientras falte cualquiera de esos hechos.
7. **Preintegración I:** obtener revisiones/aprobaciones aplicables, verificar protecciones de main (API de protección devolvió 403; no inferir ausencia de reglas), confirmar SHA exacto, checks obligatorios, workflows y si fusionar activa despliegue. Pedir autorización explícita de fusión y, por separado, de cualquier efecto de despliegue.
8. **D separado:** solo con VPS autorizada, backups, restauración, recuperación y commit aprobados.

## Estado no negociable

#376 es un PR **exclusivamente de ensayo**: **no fusionarlo**. No aprobar por cuenta del responsable de Etapa 7 ni cambiar sus archivos desde MISD. Sin merge ni despliegue.
