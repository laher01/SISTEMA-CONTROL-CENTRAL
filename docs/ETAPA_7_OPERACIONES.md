# Etapa 7 — Operaciones, instalación y estado

Fecha: 2026-10-09. Base: main 392e67d. Rama: feature/etapa-7-infraestructura.
Diseño inicial: [infraestructura](ETAPA_7_INFRAESTRUCTURA.md).

## Implementación

La migración 0017 incorpora operaciones, backups y revisión instalada.
Las versiones incluyen backend y frontend por digest. Su aprobación exige ambas
imágenes y un enlace CI que SUPERADMIN declara haber revisado. Esa declaración
queda identificada en auditoría; el enlace no prueba automáticamente que CI pasó.

Las operaciones guardan UUID de idempotencia, versión/revisión anterior, imágenes,
actor, estado y resultado. El agente reclama bajo bloqueo PostgreSQL por nodo y
recibe lease aleatoria almacenada como hash. Repetir el mismo resultado es seguro;
una ejecución vencida nunca se vuelve a ejecutar automáticamente. Un proceso muerto
con estado local pendiente requiere revisión humana de Docker.
No se puede editar/desactivar el nodo mientras ejecuta; desactivarlo cancela su cola.
Un lote de hasta 20 nodos avanza secuencialmente después de cada éxito; fallo,
cancelación o incertidumbre detienen los siguientes nodos.

Operaciones permitidas: DESPLIEGUE, BACKUP y ROLLBACK_IMAGEN. No existe shell libre.
El despliegue exige versión aprobada, entorno compatible, reporte reciente y
revisión conocida. Si cambia el esquema, exige backup reciente de ese nodo/revisión
y declaración auditada de restauración aislada. El éxito exige salud, imagen
instalada por digest y revisión real. El rollback de imágenes exige igual revisión
final; no revierte PostgreSQL ni restaura datos automáticamente.

El backup contiene pg_dump y documentos originales en un bundle con hashes internos,
cifrado age y hash del objeto cifrado. Detiene temporalmente backend/frontend solo
del Compose aislado para obtener snapshot consistente y los inicia en finally.
pg_restore --list verifica estructura, no restauración completa. La retención queda
registrada en días; limpieza automática permanece pendiente hasta validar recuperación.
El montaje externo se configura por el operador; no se afirma que exista.
Los archivos de entorno y claves privadas no se incluyen en el bundle.

La recuperación aislada valida hashes, rechaza rutas documentales inseguras,
extrae documentos a directorio temporal y restaura PostgreSQL en un contenedor
temporal sin red ni puertos. Solo elimina ese contenedor de nombre único.
La recuperación productiva de configuración/datos después de migraciones requiere
procedimiento humano pendiente. No existe rollback automático con pérdida de datos.

Los eventos se protegen con triggers contra UPDATE/DELETE en PostgreSQL y SQLite.
No hay API de edición/borrado. Un administrador con permisos DDL puede eliminar
triggers; esos privilegios de la VPS todavía deben revisarse.

## Modelos y estados

- infra_nodos: inventario global, capacidades, token hash, último contacto y revisión.
- infra_reportes: UUID por nodo, hash de contenido, métricas y servicios autenticados.
- infra_versiones: SemVer, commit, imágenes/digests, construcción, entorno,
  validación/aprobación y compatibilidad de esquema.
- infra_tenant_nodo: ubicación única por tenant, sin traslado de registros de negocio.
- infra_eventos: actor, correlación, acción, recurso, resultado y datos estructurados.
- infra_operaciones: solicitud, lease hash/caducidad, grupo/orden, parámetros y resultado.
- infra_backups: objeto cifrado, hash, tamaño, nodo/versión/revisión y política de retención.

Estados de operación: PENDIENTE → EJECUTANDO → EXITO/FALLO; CANCELADA para colas
de nodos desactivados. Una lease vencida o cambio inesperado de nodo bloquea nuevas
ejecuciones; resolver la incertidumbre exige revisar el estado real, no reintentar comandos.

## Instalación de staging y agente (no ejecutada aquí)

1. Ejecutar workflow infrastructure-images con versión y revisión Alembic instalada.
   Reutiliza CI backend/frontend y auditorías, valida PostgreSQL, publica imágenes
   GHCR de staging con etiqueta SHA, digest, metadata OCI, SBOM y provenance.
   Registrar artifact version-staging.json desde SUPERADMIN y revisar CI antes de aprobar.
   No introduce credenciales administrativas de VPS en GitHub ni despliega esta rama.
2. Preparar Linux de pruebas con Docker Compose y age. Copiar
   deploy/.env.agent-staging.example a .env.agent-staging, introducir credenciales
   nuevas y dos imágenes por digest; proteger con chmod 600.
3. Iniciar exclusivamente deploy/docker-compose.agent-staging.yml con proyecto
   fact-central-agent-staging: puerto loopback 18081 y volúmenes independientes.
   No usar deploy/deploy.sh: sigue actualizando main y no debe ejecutar esta rama.
4. Registrar nodo y generar credencial. Copiar deploy/infra-agent.env.example a
   /etc/factcentral/infra-agent.env con UUID, token, API HTTPS central, rutas absolutas
   y montaje externo. Mantener operaciones deshabilitadas al verificar métricas.
5. Desde backend ejecutar python -m app.infra_agent --once, o instalar servicio
   deploy/systemd/factcentral-infra-agent.service con usuario dedicado y permisos
   sobre directorio de estado y montaje de backups. El socket Docker concede
   capacidad elevada: usar una VPS de staging dedicada y revisar permisos.
   Este agente de ejecución no se instala en producción.
6. Después de verificar configuración, habilitar FC_INFRA_OPERACIONES_HABILITADAS
   en el plano administrativo y FC_INFRA_AGENT_OPERACIONES en el agente.
   FC_INFRA_PRODUCCION_HABILITADA queda false; el agente además rechaza production.
7. Solicitar backup y comprobar la restauración:

   ```sh
   python -m app.infra_agent --restore-isolated /mnt/backups/archivo.backup.tar.age \
     --identity /ruta/privada/age-key.txt --sha256 HASH_DEL_INVENTARIO
   ```

   Conservar evidencia antes de declarar restauración verificada. La clave age privada
   debe permanecer separada del nodo que realiza los respaldos.
8. Solicitar despliegue, consultar imagen/revisión efectivas, probar rollback compatible
   y verificar que un lote se detiene después de un fallo en su primer nodo.

Variables adicionales: FC_INFRA_LEASE_SEGUNDOS (3600),
FC_INFRA_OPERACIONES_HABILITADAS (false), FC_INFRA_PRODUCCION_HABILITADA (false).
El agente usa FC_INFRA_AGENT_* y FC_INFRA_BACKUP_* documentadas en su ejemplo.
HTTP tiene timeout 10 segundos, una petición por ciclo y outbox privado. Los
comandos tienen timeouts acotados. Un fallo de red no vuelve a ejecutar comandos.
Si hay en-curso.json, no borrarlo ni reprocesar antes de revisar Docker.

## Endpoints adicionales y permisos

Prefijo /api/v1/infraestructura; sesión existente y SUPERADMIN:

- GET operaciones; POST despliegues; POST rollback-imagen; POST lotes.
- GET/POST backups; POST backups/{id}/restauracion-verificada.
- POST versiones/{id}/aprobar.

Agente mediante Bearer individual:

- GET agentes/{id}/identidad; GET agentes/{id}/salud.
- POST agentes/{id}/reclamar; POST agentes/{id}/operaciones/{id}/resultado.

El token no concede acceso al dashboard, versiones, empresas ni otros nodos.
Los destinos privados registrados no se consultan desde backend. El agente consulta
API HTTPS configurada y healthcheck loopback; no sigue redirecciones con Bearer.
El control Origin acepta HTTPS del host público configurado detrás del proxy sin
confiar en X-Forwarded-Host. Se conservan las cookies y el aislamiento host/tenant.

## Validación y seguridad

Backend local: 146 pruebas correctas, una omitida por requerir PostgreSQL,
Ruff/formato y mypy Linux sin errores. Frontend: cuatro pruebas, typecheck y build
correctos; lint sin errores y aviso anterior en Chat.tsx. Las dos nuevas migraciones
se probaron en SQLite aislado preservando datos; SQL PostgreSQL de toda la cadena
se generó correctamente. CI agrega ejecución upgrade/downgrade de estas migraciones
en una base PostgreSQL distinta de la utilizada por las pruebas.

El agente se prueba sustituyendo subprocess: argumentos, hashes, recuperación
documental y aislamiento están comprobados; Docker/age/pg_restore reales NO.
Aquí no están disponibles Docker/PostgreSQL locales ni configuración SSH a la VPS.
No se ha verificado la versión efectiva de Oracle/Cloudflare.

Se corrigió vulnerabilidad alta anterior en source-map-js; npm audit informó cero.
pip-audit sobre dependencias instaladas informó No known vulnerabilities found.
uv.lock permanece conservado. No se agregaron secretos al repositorio ni se
activaron canales externos, servicios de pago o despliegues productivos.

## Pendientes reales

Validación Docker y restauración completa en staging; CI remoto; revisión visual/E2E
del panel; almacenamiento externo y retención; privilegios del agente; recuperación
productiva de configuración/datos; migración de tenants; comprobación VPS/Cloudflare.
MFA/IdP avanzado no está presente en la autenticación existente y no se declara resuelto.

## Matriz de módulos

PROBADO corresponde a código local, no certifica producción.

| Módulo | Estado | Alcance / pendiente |
|---|---|---|
| 7.1 VPS | PROBADO | CRUD lógico, capacidades y tokens; VPS sin consultar |
| 7.2 Dashboard | IMPLEMENTADO | Build/lint; visual y E2E pendientes |
| 7.3 Monitoreo | PROBADO | Reportes y recolector; Linux real pendiente |
| 7.4 Versiones | PROBADO | SemVer, commit, imágenes y aprobación auditada |
| 7.5 Despliegues | IMPLEMENTADO | Estados/leases/agente; Docker real pendiente |
| 7.6 CI/CD | IMPLEMENTADO | Workflows y GHCR; ejecución remota pendiente |
| 7.7 Progresivo | PROBADO | Lotes con parada ante fallos; flota real pendiente |
| 7.8 Backups | IMPLEMENTADO | Bundle cifrado; almacenamiento/retención real pendientes |
| 7.9 Rollback | IMPLEMENTADO | Imágenes compatibles; datos/config productivos pendientes |
| 7.10 Migraciones | PROBADO | SQLite y SQL; PostgreSQL real pendiente |
| 7.11 Tenants/nodos | PROBADO | Metadata sin acceso cruzado ni traslado de clientes |
| 7.12 Seguridad | PROBADO | Sesión, SUPERADMIN, Origin y tokens; MFA/privilegios pendientes |
| 7.13 Auditoría | PROBADO | Actor/correlación/inmutabilidad; privilegios VPS pendientes |
| 7.14 Alertas | PROBADO | Umbrales, servicios, desconexión, fallos y versión |

La etapa no se declara terminada sin staging, recuperación y CI remoto.
