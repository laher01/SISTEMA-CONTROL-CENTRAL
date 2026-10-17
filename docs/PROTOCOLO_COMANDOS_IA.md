# Protocolo maestro de comandos IA — FACT CENTRAL / NEXUS 2.0

Versión: 1.0 — 2026-10-17  
Estado: propuesta versionada, pendiente de revisión e integración a `main`.

## Propósito y alcance

Unificar el significado de órdenes breves en los chats de desarrollo de FACT CENTRAL, NEXUS 2.0 y módulos relacionados. Esta referencia no concede acceso a un servidor ni permite a los chats leer automáticamente conversaciones ajenas. Para aplicarla de manera consistente, incorporar el resumen a las instrucciones compartidas del proyecto y enlazar este documento.

## Tabla de comandos vigentes

| Comando exacto | Objetivo | Límite de autorización |
| --- | --- | --- |
| `C` | Continuar el desarrollo ya acordado, corregir errores y ejecutar pruebas automáticas disponibles. | No fusionar ni desplegar. |
| `S` | Verificar seguridad, permisos, aislamiento por tenant, base de datos, migraciones, respaldos y restauración. | No fusionar ni desplegar. |
| `I` | Revisar PR aprobados y aptos para integración, comprobar conflictos y checks, y fusionar únicamente los PR pertinentes en `main`. | Antes de fusionar, verificar si un push a `main` dispara despliegue automático. Si lo dispara y no existe autorización expresa vigente para ese despliegue, NO fusionar; documentar el bloqueo y solicitar autorización `D` o usar una separación segura previamente validada. Nunca dar por hecho que `I` autoriza publicar en producción. |
| `D` | Desplegar la versión aprobada en la VPS antigua mediante el procedimiento seguro establecido y verificar su operación. | Bloquear ante ausencia de respaldos/restauración comprobados, falta de acceso o fallas críticas. |
| `FINALIZAR` | Ejecutar el ciclo de desarrollo, pruebas, corrección y validación del trabajo en curso, hasta dejarlo preparado para integrar y desplegar. | No fusionar ni desplegar; emitir conclusión y recomendar el paso siguiente. |

Los comandos anteriores con tres puntos (`C...`, `S...`, `A...`, `D...`) se consideran **legado**. No inferir aprobación de despliegue desde un comando ambiguo. La nueva forma canónica es sin puntos.

## Máquina de estados y autorización

1. `C` y `FINALIZAR`: desarrollo/pruebas en rama aislada. El trabajo puede regresar a `C` si queda algo por corregir.
2. `S`: auditar criterios de seguridad y recuperación. Si falla, recomendar `C` para corregir y repetir `S`.
3. `I`: integrar solo PR expresamente aprobados y que hayan pasado controles. Verificar las reglas de protección y el efecto real de los workflows sobre `main`; si fusionar dispara producción sin autorización `D`, bloquear la fusión. La fusión no demuestra despliegue.
4. `D`: antes de actuar, verificar acceso a la VPS, identidad de versión/commit, preflight, respaldo fresco y restauración aislada; después desplegar y comprobar el SHA instalado y salud de servicios.
5. Si cualquier acción resulta inaccesible por herramientas, permisos o infraestructura, describirla como pendiente; nunca declararla ejecutada.

No es obligatorio pasar siempre por todos los comandos: el siguiente depende del estado verificado. `FINALIZAR` cierra la etapa preparatoria, **no** significa pasar a producción.

## Conclusión obligatoria en cada chat

Al cerrar una respuesta de ejecución, informar:
- Alcance y cambios efectivamente realizados, con rama y commit cuando existan.
- Pruebas ejecutadas y evidencias, distinguiéndolas de pruebas no realizadas.
- Riesgos, errores y bloqueantes abiertos.
- Estado de PR, seguridad, integración y despliegue; evitar la palabra «listo» sin verificación.
- **Un único siguiente comando recomendado** y explicación de por qué corresponde.

Si la interfaz admite controles interactivos, incluir un botón que envíe **solo el siguiente comando** (o el comando con contexto mínimo que elimine ambigüedad). El botón solicita una nueva interacción: no ejecuta anticipadamente ni concede autorización para etapas sucesivas.

## Reglas para colaboración y producción

- Respetar trabajo paralelo y límites entre módulos; no mezclar cambios de PR no relacionados ni sobrescribir ramas de terceros.
- Prohibido forzar `main`, saltarse CI, omitir revisión de seguridad, desactivar preflight o simular verificaciones.
- Auditoría documental de un PR NO certifica permisos reales de repositorio, branch protection, secretos de Actions, base de datos, respaldos ni acceso SSH. Esas comprobaciones requieren evidencia y herramientas apropiadas; marcar claramente «no verificado».
- Antes de cualquier fusión, cotejar el SHA revisado con el SHA actual, los checks obligatorios, revisiones, conflictos y reglas de protección. Una actualización posterior invalida una aprobación anterior hasta repetir la comprobación.
- Proteger secretos, PII, comprobantes y datos tributarios. No copiar credenciales ni ejemplos sensibles al repositorio.
- Cualquier cambio de fórmula monetaria, aprobación contable, fiscal o permisos requiere criterio de negocio explícito y pruebas de regresión.
- El rol documental del protocolo **no** equivale a un servicio que ejecute automáticamente comandos entre chats.
- La ejecución se realiza únicamente durante una interacción activa y con herramientas/credenciales efectivamente disponibles.

## Pendientes conocidos al redactar esta versión

Los siguientes issues requieren atención por separado y no se resuelven creando este protocolo:
- #235: certificación del autodespliegue en VPS antigua.
- #240: exclusión de expedientes pendientes/observados en liquidaciones de Responsable.
- #229: aprendizaje asistido de facturas en NEXUS.
- #224: Contabilidad de Ítems.
- #221: ZIP/RAR y vouchers.
- #202: reescaneo histórico NEXUS.
- #242: Gerencia SaaS / pedido único.

Estos ítems son un inventario puntual, no una afirmación de que el estado futuro siga siendo idéntico.

## Aplicación multichat

Copiar la tabla de comandos, las reglas de aprobación y el formato de conclusión a las **instrucciones del proyecto ChatGPT**. Registrar esta ruta como fuente: `docs/PROTOCOLO_COMANDOS_IA.md`. Los chats existentes no reciben cambios retroactivos de mensajes ni pueden garantizar lectura de este archivo sin acceso a GitHub/proyecto.
