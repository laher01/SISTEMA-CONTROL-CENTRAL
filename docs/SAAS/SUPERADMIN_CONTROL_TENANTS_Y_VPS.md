# FACT CENTRAL — SUPERADMIN, tenants y almacenamiento secuencial

**Estado:** especificación técnica aprobable e implementación incremental. No equivale a infraestructura desplegada.

## 1. Separación de ámbitos
- **SUPERADMIN de plataforma:** administra tenants, estado de capacidad, nodos de almacenamiento, salud de la VPS central, políticas de altas/suspensiones y cuentas auxiliares expresamente delegadas. Inspección documental de tenants: **solo lectura y auditada**, sin suplantación de sesiones.
- **ADMIN01 de cada tenant:** único administrador propietario de su espacio operativo. Gerentes, Secretarías, Responsables, Usuarios y Gestores se crean dentro de ese tenant. SUPERADMIN no genera registros comerciales por ellos.
- **VPS central antigua:** ejecuta frontend, API, PostgreSQL y servicios de FACT CENTRAL. No instalar otras copias independientes del SaaS en las VPS almacén.
- **VPS de almacenamiento:** nodos de objetos/documentos cifrados, con autenticación servicio-a-servicio, límites por tenant y trazabilidad. No acceden a la base de datos productiva como usuarios privilegiados.

## 2. Creación de tenant desde SUPERADMIN
Se reutiliza el flujo vigente `POST /api/v1/configuracion/administraciones`, protegido por el rol SUPERADMIN: crea registro de Tenant, ADMIN01, cuenta y contraseña temporal con cambio obligatorio. El menú «Creación de tenant» lleva al flujo existente, no crea un segundo camino.

**Plantilla:** cada tenant hereda automáticamente la estructura **versionada de la aplicación y migraciones comunes**: mismas tablas compartidas con `tenant_id`, permisos y menús de su plan. No se clonan filas, archivos, expedientes, credenciales, historiales ni IDs del tenant original; este continúa intacto. La actualización del código y migraciones del SaaS central alcanza a todos los tenants compatibles, sin usar un tenant con datos como origen de copia.

Provisionamiento idempotente con clave de solicitud, transacción, auditoría y rechazo de nombres/subdominios duplicados. **Nueva regla solicitada:** únicamente SUPERADMIN (o auxiliares de plataforma con delegación expresamente aprobada) autoriza la creación efectiva del tenant. El registro público debe producir una **solicitud pendiente de aprobación**, no una base ni un tenant activo. Existe actualmente la ruta de demos con secreto (`POST /configuracion/administraciones/demo`), y el documento de ciclo de vida histórico prevé autoalta: resolver esa incompatibilidad con el equipo de Etapa 7 y autenticación antes de cambiar el onboarding compartido. No afirmar exclusividad total de SUPERADMIN mientras la ruta demo siga disponible.

## 3. Administración y seguridad
| Operación | Responsable |
| --- | --- |
| Ver inventario y estado de todos los tenants | SUPERADMIN |
| Crear tenant, suspender/reactivar | SUPERADMIN; auxiliares solo con permisos explícitos |
| Consultar indicadores de tenants | SUPERADMIN, solo lectura y con auditoría |
| Restablecer acceso del propietario ADMIN01 | SUPERADMIN con verificación reforzada, revocación de sesiones y auditoría |
| Eliminar tenant | No permitir borrado físico inmediato; suspensión → periodo de retención → autorización doble → backup/restauración verificados → purga controlada |
| Administrar módulos comerciales, documentos y usuarios operativos | ADMIN01 y jerarquía de su tenant, no SUPERADMIN |
| Gestionar operadores auxiliares de plataforma | SUPERADMIN mediante RBAC separado, sin compartir su contraseña |

Toda operación sensible requiere autenticación robusta, protección CSRF cuando aplique, confirmación y auditoría; acceso por `tenant_id` incluso ante UUID conocidos.

## 4. VPS central y nodos secuenciales de almacenamiento
Inventario de cada nodo: ID interno, nombre, clase (CENTRAL/ALMACEN), etiqueta, estado (REGISTRADO/VERIFICADO/ACTIVO/LECTURA/RETIRADO), capacidad total y libre, utilización, CPU vCPU, RAM total/usada, swap total/usada, IO, latencia, timestamp y salud del agente. Nunca guardar claves privadas ni tokens en registros de negocio.

**Solo un nodo de almacenamiento de escritura por vez, para todos los tenants**. Los anteriores permanecen legibles. Antes de activar el siguiente:
1. Medir **uso real persistente del volumen documental**, no RAM, CPU o espacio lógico reservado.
2. Umbral configurable con valor inicial **60 % de uso**: generar alerta y comenzar el procedimiento de transición. No mover escrituras inmediatamente si el nuevo nodo no está validado.
3. SUPERADMIN registra el siguiente nodo; probar conexión TLS/mTLS, espacio, permisos, latencia, escritura, lectura, hash y borrado temporal de prueba.
4. Control transaccional: establecer nuevo nodo ACTIVO como único destino para nuevas escrituras, conservar antiguos nodos LECTURA; nuevos documentos de **todos** los tenants irán al nodo activo.
5. Mantener un **registro inmutable de ubicación por documento**: tenant_id, documento_id, hash, nodo_id, clave, versión, tamaño, fecha y estado. La recuperación no debe depender del nodo que esté activo actualmente.
6. Escritura provisional + comprobación de hash y metadatos + confirmación atómica; reintentos idempotentes. No borrar el origen antes de confirmar destino. Evitar filas huérfanas y documentos sin ubicación.
7. Ante nodo lleno/caído, **detener escrituras de forma segura o realizar failover aprobado y verificado**. No asignar silenciosamente a otro nodo.
8. Los backups de documentos y base deben ser independientes del nodo activo; la replicación no constituye backup.

La VPS central puede alojar temporalmente almacenamiento documental solo mientras no exista nodo verificado, según política explícita; cuando el volumen alcance 60 %, alerta y preparación de nuevo nodo, preservando legibilidad histórica.

## 5. Métricas y panel
- Dashboard SUPERADMIN: total de tenants, activos/suspendidos, documento/uso por tenant y global, salud de central, y secuencia de nodos.
- Tarjetas por VPS: vCPU, RAM, swap, disco total/usado/libre, % disco, última lectura y alertas. Las métricas deben mostrar **SIN TELEMETRÍA** cuando no haya datos, nunca inventar capacidades ni inferir que un nodo está activo.
- Recolector autenticado con privilegios mínimos; sin SSH arbitrario por la interfaz. Lecturas periódicas y detección de datos obsoletos.
- Activación de nodo con check explícito y doble comprobación, no con selección visual simple.

## 6. Orden seguro de implementación
Fase A: menú SUPERADMIN sobre el alta existente + arquitectura y pruebas de autorización.
Fase B: inventario/telemetría de VPS central de solo lectura, backend aislado por rol; no registrar secretos.
Fase C: modelos de nodos y ubicaciones documentales con migración, compatibilidad del `app.storage` existente y pruebas con almacenamiento falso.
Fase D: registro/validación del primer nodo externo, flujo 60 % y conmutación con pruebas, copias verificadas.
Fase E: suspensión/restablecimiento administrativo, auxiliares RBAC de plataforma, auditoría y purga segura; nunca eliminar físicamente tenants sin retención y respaldo.
Fase F: pruebas de recuperación, compatibilidad de migraciones y despliegue controlado a **VPS antigua 132.145.233.172**.

**Frontera de equipos:** este trabajo NO reestructura el tenant original, operaciones, OCR, Etapa 7 ni altera migraciones compartidas sin coordinación. No crear nuevas bases PostgreSQL copiadas por tenant: el aislamiento actual usa tenant_id en esquema multi-tenant. Cualquier cambio de arquitectura de BD requiere diseño, migración y pruebas aparte.

## 7. Pruebas requeridas
- SUPERADMIN ve entrada «Creación de tenant» y usa el endpoint ya existente; ADMINISTRADOR/GERENTE/otros no acceden.
- Alta crea exactamente un tenant con ADMIN01; no hereda datos del primero; reinicio/reintento no duplica tenants.
- Actualizaciones/migraciones comunes mantienen datos de todos los tenants.
- Dos solicitudes simultáneas de alta no generan colisiones o duplicados.
- Un único almacén de escritura por vez; transición al nuevo nodo probada y revertible.
- Al 60 % alerta, sin pérdida de datos; lectura de nodos antiguos; pruebas de integridad de hash.
- Simulación de nodo caído, backup y restauración tanto de DB como de documentos.
- No mostrar telemetría sin fuente autenticada; no revelar secretos en logs/API/UI.
