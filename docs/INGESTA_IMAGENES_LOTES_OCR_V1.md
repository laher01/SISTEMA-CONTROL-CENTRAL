# Ingesta documental por imágenes y paquetes — contrato de integración v1

Fecha: 2026-10-15. Estado: **especificación para implementación**, no despliegue.

## Objetivo

Incorporar imágenes JPG/JPEG/PNG/WEBP/TIFF obtenidas por cámara o compartidas desde el celular, PDF nativos y escaneados, y archivos ZIP/RAR, manteniendo la arquitectura existente de FACT CENTRAL. Tipos: factura, recibo por honorarios (RHE), GRE remitente, GRE transportista, voucher/constancia bancaria, cotización y orden de compra. **Una foto no equivale necesariamente a un documento:** agrupar anverso/reverso, páginas y capturas fragmentadas antes de comparar identidades fiscales.

## Componentes existentes que deben reutilizarse

- `docs/CORE/03_UPLOAD_STATE_MACHINE.md`: sesión, hash SHA-256, cuarentena, seguridad, deduplicación física y lógica.
- `docs/CORE/08_CORE_INTEGRATION_CONTRACTS.md`: OCR solo después de `storage.file.available`; idempotencia y eventos.
- `docs/OCR_CORE_V1.md`: PDF texto, PDF escaneado con PDFium, Tesseract en imágenes, datos con evidencia/confianza y revisión humana.
- `POST /api/v1/documentos/{id}/procesar`, `PUT /api/v1/documentos/{id}/extraccion-confirmada` y `POST /api/v1/documentos/{id}/crear-expediente`.
- Revisar PR #178 (duplicados de factura), PR #180 (identidad OCR en revisión), PR #183 (paquetes/cotizaciones), PR #207 (cotizaciones sin vinculación fiscal) antes de tocar rutas compartidas. No sobrescribir otros desarrollos.

## Pipeline

1. **Captura:** cámara posterior mediante selector de archivos del navegador y selección múltiple. Vista previa; reordenar y agrupar páginas, corregir rotación, detectar desenfoque y permitir recorte/perspectiva sin alterar el original.
2. **Recepción:** un lote lógico con N archivos; el servidor procesa un máximo de **10 imágenes por sublote** (no implica límite de 10 archivos total); cada carga conserva `ingestion_id`, `tenant_id`, `actor_id`, `source_channel`, `batch_id`, hash e idempotency_key. El cliente recibe progreso individual y resumido.
3. **Archivo comprimido:** ZIP y RAR solo si está instalado un extractor seguro y aislado, con límites en número de miembros, bytes expandidos, ratio de compresión, anidamiento, tiempo/CPU/memoria, rutas y tipos internos. Prohibidos rutas absolutas, `../`, enlaces, ejecutables y extracción fuera de zona de cuarentena. RAR no se habilita por defecto si no se valida el extractor.
4. **Antivirus e integridad:** validar firma real/MIME, tamaño, hash, malware, seguridad de PDF y límites de páginas; originales inmutables. Promover a storage definitivo y esperar `storage.file.available`.
5. **Separación/agrupación:** detectar múltiples documentos dentro de un PDF o una secuencia de fotos; conservar relación contenedor → página → documento lógico. Nunca confiar en el orden de llegada de imágenes para inferir número de factura.
6. **OCR y clasificación:** extraer texto nativo primero; OCR Tesseract `spa+eng` si corresponde. Guardar texto por página, bounding boxes cuando estén disponibles, motor/versión, confianza y evidencia por campo. Clasificar documento antes de aplicar su clave de deduplicación.
7. **Extracción:** factura/RHE: tipo, serie, número, fecha, moneda, RUC/razón social emisor y receptor, IGV, subtotal, total, ítems, unidades, cantidad y precio. GRE: emisor/remitente, transportista, destinatario, número, fecha, punto partida/llegada, placas, conductor, bienes. Voucher: banco, fecha/hora, número de operación, importe, cuentas enmascaradas, ordenante/beneficiario. Cotización/OC: número, partes, fecha, ítems, importes. No atribuir roles por RUC aislado o texto ambiguo.
8. **Normalización y validación:** normalizar RUC/serie/correlativo/moneda/fechas/decimales sin alterar la evidencia; validar RUC y consistencia de totales, subtotal + IGV, ítems, fechas y contradicciones entre páginas. Si incompleto, ambiguo o conflictivo: `REVIEW_REQUIRED`, nunca crear expediente de forma automática.
9. **Deduplicación:** primero `tenant + SHA-256` (archivo idéntico); luego identidad lógica:
   - Factura/RHE: `tenant + RUC emisor + tipo + serie + correlativo`; verificar además receptor, importe y fecha, y detectar conflicto si discrepan.
   - GRE: `tenant + tipo GRE + RUC emisor + serie + correlativo`.
   - Voucher: `tenant + banco + número operación + fecha + importe`, revisando posibles colisiones; sin identidad suficiente, revisión.
   - Cotización/OC: `tenant + emisor + tipo + número` cuando sea confiable; de otro modo revisión.
   - Fotografía visualmente idéntica con bytes distintos: huella perceptual solo como **indicio**, no rechazo automático.
10. **Decisión de factura nueva:** si la identidad fiscal es completa, confiable y no existe, crear expediente y vincular original de manera atómica con restricción única de BD. Si existe, **rechazar la creación de otro expediente**, marcar el intento `REJECTED_DUPLICATE`, informar referencia al expediente existente y no generar efecto contable/comercial. Registrar únicamente auditoría del intento y preservar evidencia conforme a la política de conservación. Si la identidad coincide pero contenidos divergen, `CONFLICT_REVIEW`.
11. **Documentos auxiliares:** GRE/voucher/OC/cotización no crean automáticamente expediente fiscal; relacionarlos a expediente existente solo por evidencia consistente y permisos, o enviarlos a bandeja de pendientes.
12. **Resultado lote:** por imagen/documento mostrar `CREATED`, `LINKED`, `REJECTED_DUPLICATE`, `CONFLICT_REVIEW`, `REVIEW_REQUIRED`, `FAILED_RETRYABLE` o `REJECTED_SECURITY`. Nunca presentar éxito global si quedan elementos fallidos.

## Contrato propuesto (no confundir con endpoints existentes)

- `POST /api/v1/ingestas/lotes`: crear lote y devolver `batch_id`, límites, sesiones de carga y estado.
- `POST /api/v1/ingestas/lotes/{batch_id}/procesar`: encolar lotes; **202 Accepted**, nunca OCR sincrónico en petición web.
- `GET /api/v1/ingestas/lotes/{batch_id}`: progreso y estados por archivo/documento.
- `POST /api/v1/ingestas/documentos/{id}/revisar`: aceptar/corregir agrupación y campos, según RBAC.
- `POST /api/v1/ingestas/lotes/{batch_id}/reintentar`: reintentar fallos transitorios de forma idempotente.

Ejemplo de respuesta conceptual:

```json
{
  "batch_id": "uuid",
  "status": "PARTIALLY_COMPLETED",
  "max_images_per_subbatch": 10,
  "results": [
    {"ingestion_id":"uuid-1","status":"CREATED","expediente_id":"uuid-e"},
    {"ingestion_id":"uuid-2","status":"REJECTED_DUPLICATE","existing_expediente_id":"uuid-e"},
    {"ingestion_id":"uuid-3","status":"REVIEW_REQUIRED","reason":"UNCERTAIN_ISSUER"}
  ]
}
```

## Capacidad y fiabilidad de VPS antigua

- Cola persistente y trabajadores independientes del API; un trabajador OCR simultáneo inicialmente, configurable por RAM/CPU. Sub-lotes de diez por turno con procesamiento secuencial o concurrencia pequeña supervisada.
- Aislar tiempo máximo, megapíxeles, DPI de rasterizado, páginas por PDF, tamaño archivo, tamaño y expansión comprimidos. No cargar todos los bytes/imágenes descomprimidos a RAM.
- Procesamiento reanudable tras reinicio: checkpoints por documento y paso; reintentos con backoff y DLQ; índice único en BD evita condiciones de carrera entre cargas simultáneas.
- Métricas: tiempo por página, consumo CPU/RAM, pendiente en cola, porcentaje extracción válida, duplicados, revisiones, errores de motor y tasa de falsos positivos.
- Auditoría: origen, actor, tenant, hashes, decisiones, campos usados, confidencias, versiones del parser y OCR, timestamps, expediente existente, errores. Aplicar RBAC y no filtrar datos entre tenants.

## Pruebas de aceptación obligatorias

1. 1, 10, 11, 25 imágenes: procesar como 1, 1, 2 y 3 sublotes; progreso consistente.
2. Una factura enviada por PDF, foto y foto rotada: **un expediente**; segundo/tercer intento `REJECTED_DUPLICATE`, sin impacto financiero.
3. Emisor/serie/correlativo iguales y receptor/importe diferente: `CONFLICT_REVIEW`, no auto-confirmar.
4. Dos uploads concurrentes de la misma factura: una sola creación gracias a restricción única y transacción.
5. Foto borrosa o sin RUC: `REVIEW_REQUIRED`, sin expediente inventado.
6. GRE, voucher, cotización y OC: clasificación correcta, asociación segura; ninguna genera factura automática.
7. PDF multipágina, PDF mixto y paquete con múltiples documentos: separar/agrupación verificable y originales intactos.
8. ZIP/RAR con traversal, symlinks, bomba de compresión, contraseña o malware: rechazo seguro; ningún archivo se ejecuta.
9. Falla de OCR/worker/red a mitad de lote: reintento seguro, sin documentos ni expedientes dobles.
10. Tenants distintos con mismo RUC/archivo: aislamiento de metadata y permisos.
11. Validar CI, migraciones Alembic, restauración aislada, pruebas frontend móvil y pruebas reales de OCR (no solo texto sintético).

## Puerta de despliegue

**Entorno autorizado: solamente VPS antigua `132.145.233.172`. No actualizar ni desplegar Oracle.** No fusionar a `main` ni ejecutar `check-updates.sh` sin confirmar qué servidor toca. Antes de cualquier producción: CI verde, pruebas reales, backup y restauración comprobada, revisión de PR concurrentes, migración compatible, despliegue aislado y healthcheck. Esta especificación no acredita implementación ni pruebas aprobadas.
