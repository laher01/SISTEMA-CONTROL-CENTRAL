# FACT CENTRAL — Estado de continuidad verificable

Fecha: 2026-10-14. Repositorio: `laher01/SISTEMA-CONTROL-CENTRAL`.
Rama de trabajo: `feature/eliminacion-integral-roles-y-storage-20261014`.
PR: https://github.com/laher01/SISTEMA-CONTROL-CENTRAL/pull/185
Base funcional: PR #184, aún requiere integración/validación.

## Código incorporado en esta fase

- `backend/app/services/ambito_emisor.py`: revisión provisional de asignaciones de proveedores a gestores desde pedidos activos, sin titularidad permanente.
- `backend/app/models.py`: `SolicitudCargaEmisor` (esquema de solicitudes).
- `backend/alembic/versions/20261014_0035_solicitudes_carga_emisor.py`: migración 0035.
- `backend/tests/test_ambito_emisor.py`: pruebas de clasificación provisional.
- `backend/app/api/routes/documentos.py`: guardia previa al guardado para carga **individual XML UBL**: si el emisor pertenece a otro grupo o asignación ambigua responde 409 `EMISOR_REQUIERE_AUTORIZACION`, sin registrar factura/expediente.

## Límites y advertencias

- **NO se implementó aún cuarentena ni generación de solicitud**. Un 409 indica bloqueo, no que se haya iniciado una aprobación.
- **NO aplica todavía a PDF, imágenes, paquetes PDF, OCR asíncrono ni correo entrante**. No afirmar que el control es seguro o completo. Centralizar la prevalidación en un punto común de entrada al incorporar OCR y separar fases antes/después de extraer identidad.
- Asignaciones `AsignacionPedidoGerencia` no constituyen titularidad permanente. Crear relación formal empresa/grupo y asegurar alcance tenant; validar casos SIN_ASIGNACION y AMBIGUO.
- Falta notificación a Administración, responsable y usuarios del gestor propietario; revisar `mensajes_alerta.py`, `AlertaManual`.
- Falta permiso de aprobación y denegación, reglas de no autoaprobación, almacenamiento temporal privado, borrado seguro y expiración.
- Falta un contrato de respuesta frontend para 409, evitando que aparezca como error genérico.
- **No se ejecutaron pruebas ni migración en VPS**. Nada desplegado.

## Siguiente acción EXACTA

1. Ejecutar suite sobre una copia local de rama y reparar fallos de API/fixtures/migración.
2. Añadir prueba HTTP para XML de otro gestor; comprobar 409, y que documentos, expedientes, montos y archivos NO cambien.
3. Crear titularidad formal de empresa y gestor por tenant; definir migración sin reasignar datos preexistentes implícitamente.
4. Implementar cuarentena aislada, solicitud pendiente y notificaciones, luego endpoints aprobar/rechazar con permisos.
5. Centralizar control en ingesta/Ubl/OCR/paquetes/Google antes de registrar cualquier documento.
6. Completar eliminación integral (PR #184/#185), colas físicas, totales y RBAC.
7. Verificar CI; jamás desplegar sin autorización, ni tocar Oracle.

## Infraestructura

VPS autorizada `132.145.233.172`, `/home/ubuntu/fact-central`, Docker Compose `deploy/docker-compose.production.yml` con `deploy/.env.production`. No borrar empresas, usuarios, credenciales, OAuth o volúmenes PostgreSQL. Reset manual anterior completado para datos documentales de prueba, NO demostraría eliminación automática.

## Plan completo de 18 módulos

Consultar el prompt maestro compartido el 14-10-2026; ejecución por prioridad: (1) integridad/eliminación y reseteo, (2) titularidad y RBAC, (3) ingesta/duplicados/OCR/expedientes, (4) notificaciones/dashboard/ERP, (5) SaaS/frontend/pruebas/despliegue.

## Avance posterior (14-10-2026)

- Commit `3247fe9f`: prueba HTTP en `backend/tests/test_ambito_emisor.py` para rechazo 409 XML de grupo ajeno, sin crear registros ni archivos. **No ejecutada**; verificar en CI/entorno local.
- Pendiente inmediato: ejecutar la prueba y completar el esquema formal de titularidad, cola de cuarentena y decisión segura.
