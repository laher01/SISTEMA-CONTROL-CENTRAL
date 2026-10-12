# Captura documental y cache OCR — plan incremental (2026-10-11)

## Auditoría verificada
- `frontend/src/paginas/Subir.tsx`: carga de varios archivos, cola de concurrencia 1 para VPS 1 GB y paquetes PDF; ahora también accesos explícitos para cámara y múltiples escaneos.
- `backend/app/services/procesamiento_documental.py`: pypdf; PDFium para PDF escaneado; Tesseract TSV para JPEG/PNG/TIFF/WEBP.
- `docs/OCR_CORE_V1.md`: extracción verificable, confirmación humana para ambigüedad, expedientes idempotentes.
- `deploy/ORACLE_AUTOUPDATE.md`: timer de sondeo previsto; su instalación y ejecución en VPS no son verificables por inspección de GitHub.
- `deploy/docker-compose.production.yml`: no declara servicio Redis actualmente. No asumir cache operativo.

## Entregado en esta rama
- Entrada explícita de foto usando `input[type=file][capture=environment]` en navegadores compatibles.
- Entrada masiva de imágenes escaneadas o PDF reutilizando la cola y API actuales.
- Sin modificar originales, entidades fiscales, endpoints ni inferencias tributarias.
- **No constituye todavía un escáner de recorte de perspectiva**, ni combina páginas en un único PDF.

## Siguiente desarrollo (criterios de aceptación)
1. Previsualizador de páginas de cámara/escaner, rotación, reordenar y borrar una captura antes de subir.
2. Detectar cuatro esquinas y corregir perspectiva localmente (OpenCV.js bajo carga diferida, o motor equivalente mantenido). Si falla, ofrecer recorte manual. No alterar el original almacenado; conservar derivado y transformaciones auditables.
3. Multi-página: agrupar varias tomas en un documento lógico, sin confundir varias facturas distintas con una factura multipágina. Vista previa y separación antes de confirmar.
4. Cache OCR persistente: clave `tenant_id + sha256(original) + ocr_engine_version + idioma + pipeline_version + parametros_normalizados`. El cache guarda resultado técnico y metadatos de tiempo/confianza, **no decisiones fiscales aprobadas**. No reutilizar entre tenants salvo autorización y control formal.
5. Redis opcional para estado breve de jobs/TTL y deduplicación de trabajo en curso; PostgreSQL para metadatos durables si se requiere recuperar extracción tras reinicio. Evitar almacenar imágenes originales en Redis.
6. Idempotencia financiera por identidad fiscal comprobada, independientemente de SHA del archivo (fotos diferentes tienen hashes diferentes).
7. Cola por tenant con límite de concurrencia, reintentos acotados, cancelación, límites de archivo/páginas/píxeles, validación del MIME por contenido, antivirus si disponible y detección de imágenes maliciosas.
8. El frontend muestra estados `en_cola/subiendo/procesando/revisión/relacionado/error`, tiempos y mensajes recuperables.
9. Medición de rendimiento p50/p95: subida, preprocesamiento, OCR, deduplicación y cache-hit; comparación con y sin cache en 1 GB de RAM.
10. Pruebas E2E con PDF nativo, PDF escaneado, imagen borrosa, documento rotado, duplicado de bytes, fotos diferentes de misma factura, múltiples documentos en una foto y lote de 50 archivos.
11. CI exige lint, typecheck, tests y build. Solo fusionar a `main` tras checks y revisión; validar `/health` y despliegue VPS con evidencia (logs de timer y commit desplegado).

## Consideraciones
- Captura por HTML no implica tener acceso a un escáner USB/TWAIN desde navegador: para escáneres físicos, usar PDF/imagen generados por el dispositivo o una integración de escritorio separada.
- No recomprimir originales para obtener velocidad ficticia. Optimizar miniaturas y derivados de OCR, con calidad suficiente para lectura.
- El escáner, cache persistente, servicio Redis y rendimiento mejorado son **pendientes**, no declarar implementados.
