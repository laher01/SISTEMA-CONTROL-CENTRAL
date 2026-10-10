# Separación de identidades: SUPADMIN01 / ADMIN01

Estado: diseño aprobado, pendiente de ejecución en base real y CI. No ejecutar cambios de credenciales sin respaldo.

## Regla
- SUPADMIN01 representa SUPERADMIN global SaaS. Credencial independiente, generada con fuente criptográfica segura y entregada fuera de los logs.
- ADMIN01 del tenant NEXOMAR representa ADMINISTRADOR. Mantener su ID de cuenta y password_hash intactos.
- ADMIN01 puede existir en varios tenants con contraseñas diferentes; su identidad es (tenant_id, login).
- Ningún ADMINISTRADOR puede crear un SUPERADMIN.
- Nunca promover todos los ADMIN01 a SUPERADMIN.

## Hallazgo
La migración 0005 promovió miembros ADMIN01 sin filtrar tenant_id. No alterar migraciones ya aplicadas: la corrección debe ser nueva y específica.

## Procedimiento seguro
1. Verificar el tenant exacto de app.nexomarnegocioseirl.online y obtener instantánea del estado actual.
2. Respaldar PostgreSQL y verificar que puede restaurarse en staging.
3. Implementar migración nueva, idempotente y limitada al tenant verificado: restaurar ADMIN01 como ADMINISTRADOR sin cambiar password_hash; crear SUPADMIN01 separado, con rol SUPERADMIN. Evitar colisiones.
4. Iniciar sesión con ambas cuentas y verificar rol, nombre, código, tenant, permisos y contraseña original de ADMIN01.
5. Habilitar contexto global del Superadmin para inventario, selección de tenant y acceso auditado sin suplantar identidad.
6. Probar que un ADMIN01 de tenant A no accede a B; probar sesiones desde cada host y autorización en backend.
7. Solo tras CI, revisión y respaldo, desplegar con reversión documentada.

## Funciones
SUPADMIN01: inventario global, aprovisionamiento/suspensión de tenants, configuración SaaS y acceso auditado a cada espacio.
ADMIN01: altas de gerentes, secretarias, responsables, usuarios y gestores, y administración de recursos propios del tenant.

## Bloqueos actuales
El acceso operativo cruza tenant_id solo si se implementa una ruta autorizada expresamente. El repositorio actual conserva sesiones vinculadas a un tenant; disponer de rol SUPERADMIN no concede automáticamente acceso entre tenants.

## Validación GitHub Actions
No fusionar si Ruff, pytest, mypy, frontend o migraciones fallan. El primer CI del PR #101 detectó errores de formato; se corrigieron en la rama. Ejecutar CI nuevamente antes de despliegue.

## Control previo al despliegue (CI)
La rama de seguridad debe aprobar Ruff, formato, MyPy, Pytest y frontend. El formateo se ejecuta solo en la rama de trabajo y ningún job puede desplegar producción durante esta validación.
