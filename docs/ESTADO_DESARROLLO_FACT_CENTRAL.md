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

## Avance: asignación formal de empresas (14/10/2026)

- Modelo `AsignacionEmpresaGestor` en `backend/app/models.py`, unicidad empresa/tenant.
- Migración `0036` en `backend/alembic/versions/20261014_0036_asignacion_empresa_gestor.py`; **no aplicada aún**.
- API `backend/app/api/routes/asignaciones_emisores.py`: GET listado y PUT asignación solo ADMINISTRADOR con validación del grupo y auditoría; registrada en `app/main.py`.
- Servicio `ambito_emisor.py` consulta antes la titularidad formal; asignaciones de pedido quedan como referencia provisional cuando no hay formal.
- Prueba HTTP de privilegios, asignación y reconocimiento grupo añadida a `backend/tests/test_ambito_emisor.py`.
- Commits: `48e19173`, `07a1c6f5`, `87ad9fb4`, `adce126d`, `87a6bccc`, `046c1279`.
- CI: **sin ejecuciones asociadas al último commit al consultar**; validación pendiente.
- **Próximo trabajo inmediato**: crear almacenamiento seguro de cuarentena por tenant, solicitudes automáticas y estados; implementar aprobación/rechazo y notificaciones; proteger rutas de paquetes, OCR e ingesta de correo; posteriormente frontend. Mantener PR borrador y no desplegar.

## Avance 14/10/2026: solicitudes y rechazo (solo XML UBL)

- `documentos.py`: si emisor UBL está asignado a otro grupo o es ambiguo, crea `SolicitudCargaEmisor` PENDIENTE, escribe temporal separado de documentos registrados y emite `AlertaManual` para Administración/gestor/responsable (en la alerta el responsable se representa mediante destinatario_usuario_id).
- `solicitudes_carga_emisor.py`: GET solicitudes y POST rechazo por Administrador o Responsable propietario, valida tenant y autoaprobación, elimina archivo temporal y registra auditoría. Ruta registrada en `main.py`.
- Prueba HTTP ampliada para comprobar documento y expediente sin alteración, solicitud pendiente y rechazo con eliminación de temporal.
- Commits `2dbcf7bf`, `56682b1f`, `49763564`, `7d51b6e5`.
- **PENDIENTE CRÍTICO**: aprobación efectiva, revalidación del archivo, estados de autorización de la operación, sincronización DB/disco ante falla, aislamiento del almacenamiento temporal, clasificación sin RUC, OCR/PDF, paquetes y correo; frontend, permisos Responsable, notificaciones exactas y reintentos de archivo.
- Pruebas **no ejecutadas** y VPS **no modificada**. No fusionar ni desplegar.

## Caso GRE SUNAT MARY GREIS / MAREUF (14/10/2026)

Observación de las capturas (NO archivo PDF binario): GRE remitente E001-00000910, emisor MARY GREIS E.I.R.L. RUC 20550466385, destinatario MAREUF RUC 20538821374, referencia impresa "Factura N° 0002 8 - RUC N° 20550466385". La referencia fiscal está incompleta/ambigua: falta serie válida E###/F###. No asumir que la guía es la factura ni deducir serie de E001-00000910.

Causa verificada: `extraer_referencias_factura_gre` solo acepta serie F###/E###; `automatizacion_documental.py` deriva a revisión cuando faltan referencia/RUC. Cuando sí existe referencia inequívoca, guarda `ReferenciaGRE` y se ve en `GET /documentos/provisionales-gre`, NO necesariamente en expedientes regulares; conciliación al llegar factura ya existe.

Cambios: `automatizacion_documental.py` conserva `gre_factura_pendiente` para referencia ambigua y "importe_contabilizable": "0.00"; prueba añadida en `test_gre_primero_factura_despues.py` con impresión SUNAT de referencia incompleta. Commits `03598436`, `5378dabd`. **Pruebas no ejecutadas**.

Siguiente trabajo: revisar contrato UI de expedientes para mostrar GRE provisionales (incluidas las ambiguas), con estado PENDIENTE_FACTURA y monto contable 0 sin falsificar fecha/serie; añadir extracción OCR robusta con PDF real aportado, validación de emisor/receptor/propiedad por gestor para PDF y conciliación sin contaminación entre grupos. Verificar seguridad y pruebas antes de deploy.


## Validación con 13 PDF originales adjuntos (14/10/2026)

Análisis local mediante `pdftotext -layout`, sin subir archivos privados a GitHub:
- 13 archivos recibidos; 9 SHA-256 únicos y 4 copias exactas.
- Las 5 GRE son PDF con texto seleccionable. El patrón vigente de `extraer_referencias_factura_gre` recupera correctamente serie/correlativo/RUC factura y RUC destinatario de las 5:
  - EG07-330 => E001-468, emisor factura 20614885085, receptor 20524011353 (factura adjunta S/ 6,990.32).
  - EG07-335 => E001-474, emisor 20614885085, receptor 20613213008 (factura S/ 660.56).
  - EG07-339 => E001-481, emisor 20614885085, receptor 20615137422 (factura S/ 492.06).
  - EG07-526 => E001-435, emisor 20612638935, receptor 20538821374 (factura no adjunta).
  - EG07-136 => E001-246, emisor 10708800207, receptor 20524011353 (factura no adjunta).
- E001-495 del emisor 20614885085, destinatario 20523209176, importe S/ 492.06 no equivale a E001-481 aunque compartan importe; deduplicación fiscal debe basarse en identidad.
- La GRE no documenta un importe fiscal: pendientes no deben sumar ventas, IGV o importes.

**Cambios de rama (no desplegados):** pruebas de formato para 5 GRE en `backend/tests/test_referencias_gre.py` (commit `a01d1de8`); API `GET /api/v1/documentos/provisionales-gre` ahora expone `estado=PENDIENTE_FACTURA` y `monto_contabilizable=0.00` (commit `3dcb87b6`); regresión en `backend/tests/test_gre_primero_factura_despues.py` (commit `11c3c176`).

**Pendiente:** comprobar pipeline real `procesar -> aplicar_automaticamente` en FastAPI con PDF binario original; exponer GRE provisionales en pantalla principal de expedientes o vista unificada, no solo Pendientes; creación de expediente provisional formal requiere diseñar datos faltantes sin inventar fecha/moneda/valor de factura. Aislar PDF por titularidad del emisor antes de contabilizar (PR #185). CI aún no verificado. VPS sin cambios.

## Visualización inicial de GRE en Expedientes (14/10/2026)

- Commit `1a793b6a`: `frontend/src/paginas/Expedientes.tsx` presenta sección independiente de GRE provisionales obtenidas de `/api/v1/documentos/provisionales-gre`, con referencia factura, RUC emisor/receptor, `PENDIENTE_FACTURA` y monto 0.00 sin mezclarlas con expedientes completos ni la selección de impresiones.
- La API ya devuelve `monto_contabilizable=0.00` (commit `3dcb87b6`). Los filtros de receptor, emisor y búsqueda se aplican en frontend a la sección provisional, pero falta homogeneizar todos los filtros de fechas/jerarquía con los de expedientes activos y paginar más de 2000 registros.
- Se verificó que GitHub Actions inició `backend`, `frontend`, `recepcion-documental-ci` y roles; al revisar estaban **en progreso**. No afirmar aprobación hasta consultar resultados.
- Persisten pendientes: correr y arreglar suite, prueba E2E UI, autovinculación a factura, expediente provisional formal con identidad parcial, autorización de cargas PDF ajenas, operación segura de cuarentena y seguridad por tenant.
