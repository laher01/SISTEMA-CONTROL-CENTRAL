# Protocolo unificado de comandos IA — FACT CENTRAL / NEXUS 2.0

Versión propuesta: 2.0 — 2026-10-19. **Estado: rama de revisión, no integrado a main.**

## Propósito
Los chats de desarrollo usan las mismas órdenes, mantienen el ámbito del módulo que les corresponde y terminan cada etapa con conclusión, nombre del chat, siguiente acción aprobable mediante botón y resumen breve. Este documento sustituye las definiciones de la propuesta v1 del PR #248, pero no reemplaza por sí solo las instrucciones de los chats existentes.

## Comandos canónicos (sin puntos)

| Comando | Acción autorizada | Límite |
| --- | --- | --- |
| `C` | Continuar implementación pendiente, corregir problemas y ejecutar pruebas disponibles. | Sin merge ni despliegue. |
| `S` | Auditar permisos/RBAC, tenants, datos, migraciones, backup, restauración, infraestructura y riesgos. | Sin merge ni despliegue. No llamar “aprobado” a lo no comprobado. |
| `T` | Ejecutar y repetir pruebas unitarias, integración, regresión, CI e identificar fallos; informar evidencia. | Sin merge ni despliegue. |
| `R` | Revisar estado del módulo, PR, issues, dependencias y duplicaciones; planificar mejoras. | Sin cambios destructivos, merge ni despliegue. |
| `F` | Corregir fallos concretos y validar su regresión, sin ampliar innecesariamente el alcance. | Sin merge ni despliegue. |
| `I` | Comprobar SHA, CI, revisiones, permisos y compatibilidad; fusionar solamente PR expresamente aprobados en main. | Si push a main puede desplegar, no fusionar sin autorización adicional para ese efecto y controles operativos verificados. |
| `D` | Desplegar versión aprobada en la VPS objetivo autorizada y verificar commit, salud y servicios. | Requiere respaldo/recuperación verificados, acceso real y control de impacto. |
| `FINALIZAR` | Cerrar desarrollo y pruebas del alcance, eliminar bloqueantes corregibles y preparar integración/despliegue. | No fusionar ni desplegar. |

**Compatibilidad:** `C/S/I/D/FINALIZAR` mantienen el significado establecido en la propuesta v1. Los nuevos `T/R/F` dividen pruebas, revisión y corrección en tareas precisas; no invalidan las pruebas incorporadas a `C`. Los comandos anteriores con puntos (`S...`, `A...`, etc.) son referencias históricas; si se interpretan de manera ambigua, preguntar antes de acciones irreversibles.

## Alcance y propiedad entre chats

Cada chat identifica su nombre visible, módulo y trabajo acordado. Referencias iniciales:
- 3-2.1 — Eliminación de documentos / MISD (#292): relaciones, conservación, pagos y autorización de retirada.
- 10 — OCR/PDF: recepción, extracción e ingesta documental.
- 11 — NEXUS IA: interpretación y asistencia contextual sin invadir el parser OCR.
- 9 — Contabilidad de ítems: líneas, productos y conciliación contable.
- AA — SaaS página de aterrizaje: landing, CMS y contenido editorial.
- 12 — Etapa 6: identidad, permisos, seguridad e integración.
- Consolidar rol Responsable: jerarquías, producción, comisiones y liquidaciones.
- 000 — Optimizar despliegue VPS: GitHub Actions, contenedores, restauración y operaciones.

Los nombres son etiquetas de chats aportadas por el usuario, no garantía de acceso automático a su historial. Antes de intervenir código compartido, verificar PR y responsable; no sobreescribir desarrollos paralelos.

## Reglas de seguridad y continuidad

1. Desarrollar, corregir y probar autónomamente dentro del alcance autorizado. No pedir permiso por cada detalle menor.
2. Conservar arquitectura, compatibilidad, controles tributarios y trazabilidad. No borrar definitivamente expedientes fiscales ni registros de pago sin política de retención y autorización específica.
3. Verificar realmente resultados antes de decir “listo”. Distinguir pruebas de lectura estática, CI y pruebas operativas en VPS.
4. Usar rama aislada y PR en borrador para cambios pendientes. Sin force push a main ni elusión de revisiones/checks.
5. Los comandos `I` y `D` no son intercambiables. Si GitHub despliega automáticamente en push a main, evaluar ese efecto *antes* de `I`, exigir autorización correspondiente y nunca desactivar protecciones para avanzar.
6. Bloquear operaciones críticas si faltan accesos, respaldo, restauración, validación de migraciones o integridad de datos; ofrecer la corrección/diagnóstico siguiente.
7. Los botones envían una nueva orden a un chat activo; no hacen trabajo futuro sin interacción y no garantizan propagación entre chats.

## Cierre obligatorio de cada tarea

**Orden de presentación (obligatorio):**
1. **Resultado breve:** ejecutado, pruebas con evidencia y pendientes o bloqueo.
2. **Conclusión** en una o dos frases.
3. **NOMBRE DEL CHAT ACTUAL** (texto explícito, inmediatamente encima de los botones).
4. **Siguiente acción recomendada** y botón **“Aprobar y ejecutar [COMANDO]”** con una orden concreta y contexto mínimo. Opcionalmente 1 botón alternativo pertinente. La pulsación autoriza *solo* ese siguiente turno.
5. **Qué mejoramos en este chat** — bajo los botones, 2–5 viñetas cortas y sin explicaciones.

Ejemplo sin ejecutar acciones:

**Resultado:** 5 pruebas superadas, 1 bloqueo operativo.  
**Conclusión:** código listo para auditoría, no para desplegar.

**CHAT: 10 — OCR Y PDF**  
Siguiente: **S — Revisar permisos y protección entre tenants**  
[Botón: Aprobar y ejecutar S]

**Qué mejoramos en este chat**
- Corregimos lectura documental.
- Añadimos regresión de duplicados.
- Registramos pendiente de respaldo.

## Aplicación global

Para que los chats de un mismo proyecto reciban estas reglas, agregar esta versión a las **instrucciones del proyecto ChatGPT** y enlazar `docs/PROTOCOLO_COMANDOS_IA.md`. GitHub no actualiza por sí solo otros chats ni configura botones globales. Hasta integrarlo en main, consultar la rama/PR correspondiente. **No insertar secretos ni credenciales.**
