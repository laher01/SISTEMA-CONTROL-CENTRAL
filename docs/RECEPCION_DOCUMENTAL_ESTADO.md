# FACT CENTRAL — Estado de recepción documental Gmail/Outlook

Actualizado: 2026-10-10. Estado: **AUDITORÍA INICIAL / NO DESPLEGABLE**.

## Objetivo y alcance
Integrar lectura autorizada de buzones Gmail API y Microsoft Graph, remitentes registrados por gestores, deduplicación y vinculación segura con expedientes. Mantener intactos los módulos productivos y las relaciones de gerencia, responsable, usuario y gestor.

## Fuentes verificadas
- `main`: consultados `README.md`, `backend/app/main.py`, `backend/app/models.py`, `backend/app/api/deps.py`, `backend/app/services/ingesta.py`, `backend/app/services/relaciones_documentales.py`, `backend/pyproject.toml`, `backend/alembic/env.py` y `.github/workflows/deploy-staging.yml`.
- El checkout remoto está sujeto a cambios posteriores; **SHA HEAD de main aún no comprobado mediante referencia Git**. El SHA `95e1aacff45c2667d9e29f82c16fa47c43b19888` fue aportado como referencia, no confirmado como HEAD.
- PR #101 y #102 localizados, pero el estado abierto/cerrado no ha sido verificado de forma concluyente por la búsqueda disponible. No fusionar ni modificar sus funciones.
- La aplicación ya dispone de `Documento`, `Expediente`, `Empresa`, `Miembro`, `Gestor`, servicios de ingesta y relaciones, y ruta central FastAPI.
- `get_contexto_operativo` restringe especialmente el rol RESPONSABLE; la integración deberá incluir permisos específicos y pruebas, sin ampliar globalmente ese rol.

## Recuperación V10
Se recuperó de adjunto previo el paquete `FACT_CENTRAL_CORREO_V10_LOCAL.zip` (46 elementos); contiene `factcentral_mail/`, `sql/`, `tests/` y un componente React preliminar. Son pruebas y código **de laboratorio**; no se verificó su incorporación al repositorio ni su compatibilidad con el esquema actual. La cifra histórica «76 pruebas» proviene de ese trabajo, NO de CI o staging actual.

## Arquitectura y autorización
- RESPONSABLE: conecta y administra buzones receptores OAuth, dentro de su tenant y ámbito.
- GESTOR: registra solo correos remitentes de proveedores, sin facultad para crear empresas receptoras.
- ADMINISTRADOR / GERENTE / RESPONSABLE: aprueban, clasifican y dan de baja empresas según su ámbito, con doble confirmación y auditoría.
- No procesar adjuntos de remitentes no autorizados. Correo conocido pero gestor ambiguo: pendiente; RUC receptor no habilitado: cuarentena sin devengo.
- Canal único de ingesta: reutilizar `app.services.ingesta` / `procesamiento_documental` / `relaciones_documentales`; duplicados de comprobante y de archivo deben ser idempotentes.
- Secretos y refresh tokens cifrados fuera del repositorio y logs; permisos mínimos; revocación de OAuth.
- Baja de empresa: operación lógica auditada, confirmaciones separadas, protección de datos compartidos y obligaciones de conservación; nunca purga automática de datos productivos.

## Componentes implementados en esta rama
- Este documento de continuidad, sin activación de funcionalidad ni cambios en el esquema.

## Archivos modificados
- `docs/RECEPCION_DOCUMENTAL_ESTADO.md`

## Migraciones incorporadas
Ninguna. No ejecutar el SQL del prototipo V10 contra producción.

## Rama, PR y commit
- Rama: `feature/recepcion-documental-gmail-outlook`.
- PR: #105 (borrador), https://github.com/laher01/SISTEMA-CONTROL-CENTRAL/pull/105.
- Commit de rama: consultar a GitHub, no inferir de este documento.
- Último HEAD verificado de main: **pendiente de comprobar**.

## Pruebas
- No se han ejecutado pruebas del repositorio integrado en esta rama.
- V10: paquete local recuperado con tests históricos; requiere instalación y prueba aislada.
- Pendientes: ruff, mypy, pytest, migraciones upgrade/downgrade staging, React build y E2E, aislamiento tenants/gerencias, regresión de expedientes, pagos y liquidaciones.

## Bloqueadores
1. Adaptar SQLAlchemy/Alembic al esquema de `main` y preservar historial.
2. Conectar OAuth Google y Microsoft con IDs y secretos autorizados; no compartir secretos en PR.
3. Implementar workers con locking, reintentos e idempotencia real PostgreSQL.
4. Adaptar ZIP/RAR/OCR al almacenamiento existente y proteger contra archivos maliciosos.
5. Implementar frontend y permisos especiales RESPONSABLE sin romper rutas actuales.
6. Validar snapshot de datos, respaldos restaurables y pipeline CI antes de merge.
7. Confirmar estados actuales de PR #94, #97, #98, #99, #100, #101, #102, #103, #104.

## Estado de main y VPS
- No integrado en `main`. VPS no modificada desde este trabajo.
- `deploy-staging.yml` usa `push: main` y `workflow_dispatch`; fusionar a main puede iniciar despliegue, así que se prohíbe merge antes de la aprobación técnica y respaldo comprobado.

## Siguiente tarea exacta
1. Leer y comparar migraciones actuales, servicios de gestión de empresas y modelos de seguridad completos.
2. Portar primero la ingesta idempotente y tablas de buzones/sincronización a SQLAlchemy/Alembic.
3. Añadir pruebas PostgreSQL y permisos multi-tenant.
4. Integrar conectores OAuth, workers y pantallas en la rama.
5. Ejecutar CI y E2E staging; únicamente después evaluar merge/despliegue productivo.
