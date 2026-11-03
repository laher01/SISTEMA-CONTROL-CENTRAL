# Protocolo maestro `zz...` — FACT CENTRAL / NEXUS 2.0

## Propósito

Una sola orden `zz...` autoriza una **sesión de continuidad autónoma**: revisar pendientes del alcance, desarrollar, ejecutar pruebas, corregir, repetir y dejar resultados trazables. El asistente no pedirá un nuevo comando `C`, `S` o `FINALIZAR` para cada corrección técnica ordinaria.

La continuidad ocurre **mientras la sesión y las herramientas estén disponibles**. No implica trabajo invisible permanente ni ejecución entre mensajes fuera de una automatización expresamente programada.

## Secuencia de cada ciclo

1. Leer `AGENTS.md`, coordinación, issues, PR abiertos y último SHA de `main`.
2. Elegir el pendiente propio del chat y no sobrescribir cambios de otros responsables.
3. Preparar rama separada; implementar la corrección más pequeña comprobable.
4. Ejecutar lint, tipado, tests, integración, migraciones y verificación de roles según los archivos tocados.
5. Diagnosticar fallos con logs, corregir y repetir. No ocultar errores ni bajar controles para obtener un verde artificial.
6. Abrir o actualizar PR; comprobar SHA exacto y checks del **head vigente**.
7. Integrar únicamente con autorización aplicable y verificaciones requeridas. Después del merge, tratar el despliegue automático como una operación real, no como una acción inocua.
8. Verificar la instalación efectiva y los servicios; si no hay evidencia de VPS, declarar `SIN VERIFICAR` y no repetir el despliegue a ciegas.
9. Terminar con estado, errores pendientes y conclusión. No exigir al usuario pulsar botones para avanzar entre verificaciones no críticas.

## Relación con los comandos

- `C`: implementar/corregir/probar.
- `S`: permisos, copias, integridad, restauración y seguridad.
- `I`: integración controlada de PR aprobados.
- `D`: despliegue controlado y comprobación real.
- `FINALIZAR`: finalizar hasta la preparación, sin integrar ni desplegar.
- `zz...`: ejecutar de forma continua los ciclos **permitidos** anteriores, sin solicitar autorizaciones repetidas para correcciones menores.

La orden `zz...` no permite suplantar aprobaciones humanas exigidas por GitHub, políticas del proveedor, secretos ni comprobaciones técnicas que hayan fallado.

## Puertas de seguridad que nunca se omiten

- No modificar ni revelar secretos, datos de tenants o información productiva ajena al cambio.
- Migraciones PostgreSQL: head lineal, pruebas de upgrade; respaldo comprobado y restauración aislada antes de aplicar.
- No ignorar errores de CI, controles de roles o hallazgos de seguridad.
- No operar sobre `factcentral.online` reservado sin instrucción expresa.
- No borrar, forzar push o hacer un segundo despliegue sin saber el estado del primero.
- Detener cambios críticos si el commit objetivo dejó de ser el último `main` o el SHA instalado no coincide.
- Una operación puede marcarse `PREPARADA`, `INTEGRADA`, `DESPLEGADA` o `VERIFICADA` solamente con la evidencia apropiada.

## Caso conocido: despliegue #420

La ejecución falló con `El destino main cambió, no actualizar`. El bloqueo de `bootstrap-main.sh` es **correcto**: protege de desplegar un SHA obsoleto. Nunca cambiarlo por un checkout forzado.

Si `main` avanza:
1. Consultar el SHA actual y verificar pruebas de ese commit, no las de uno anterior.
2. Consultar los runs automáticos de `push` y si ya existe un despliegue exitoso.
3. Solo plantear una ejecución nueva si no existe una actualización válida en curso o finalizada y los preflights pasan.
4. Tras instalar: verificar `alembic_version`, salud backend, contenedores, login, landing y permisos de SUPERADMIN.


## Certificación de la VPS tras una carrera de commits

Para el caso concreto de `deploy-staging` (VPS antigua autorizada):

- Si el job muestra `El destino main cambió, no actualizar`, marcar **DESPLIEGUE BLOQUEADO POR SHA OBSOLETO**, no `DESPLIEGUE CORRECTO`. Los checks previos y una restauración de prueba no certifican la migración ni los contenedores.
- Comprobar la ejecución `push` o `workflow_dispatch` del SHA vigente de `main`, no reutilizar resultados de PR ni el SHA antiguo.
- En el job remoto, comprobar la salida **`Commit VPS verificado: <SHA>`** y resultado `success`. Si falta, no afirmar instalación.
- Tras comprobar el SHA, obtener evidencias de `docker compose ps`, `/health`, `alembic current` y rutas de login/landing; separar cada estado en la matriz `COMPROBADO / NO COMPROBADO / FALLIDO`.
- No crear otro `workflow_dispatch` mientras un deploy de `main` esté en ejecución. Evitar repetir respaldos/migraciones por desconocimiento del estado.
- El propio merge a `main` dispara `deploy-staging`: comprobar esa consecuencia incluso al fusionar cambios de documentación.

### Escalamiento

Si el conector GitHub solo muestra ejecuciones de `pull_request`, no deducir el estado de `push` a partir de una lista vacía. Pedir el **log o captura del job concreto** o una lectura autorizada de la VPS antes de certificar, conservando los secretos ocultos.

## Informe breve

`Estado`: terminado / pendiente / bloqueado.

`Resultados`: cambios verificables, PR y SHA.

`Errores pendientes`: lo que no pasó o no se pudo comprobar.

`Conclusión`: próximo paso y condición que lo habilita.

No volver a convertir cada sugerencia rutinaria en una solicitud de confirmación. Una nueva autorización específica será necesaria cuando una operación crítica no esté cubierta con suficiente seguridad.
