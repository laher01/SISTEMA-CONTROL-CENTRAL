# OCR Core v1 — extracción documental verificable

## Propósito

OCR Core obtiene texto utilizable desde documentos ya recibidos y almacenados. Su resultado
aporta contexto al Expediente Inteligente, pero no reemplaza el archivo original ni convierte
automáticamente una inferencia en un hecho aprobado.

## Responsabilidad

- Extraer la capa de texto de PDF mediante `pypdf`.
- Rasterizar con PDFium los PDF sin capa de texto y ejecutar OCR página por página.
- Ejecutar Tesseract en imágenes JPEG, PNG, TIFF y WEBP cuando esté instalado.
- Conservar método, motor, páginas, idioma y confianza junto con el texto extraído.
- Proponer un tipo documental mediante indicadores explícitos.
- Sugerir campos estructurados: serie, correlativo, RUC de emisor/receptor, fecha de emisión,
  moneda, importe total y número de operación.
- Conservar para cada campo el valor, fuente, evidencia textual y confianza.
- Exigir confirmación humana antes de aplicar la clasificación sugerida.
- Registrar auditoría de procesamiento completado o fallido.

## Límites

- No modifica el original.
- No vincula automáticamente el documento a un expediente.
- No clasifica silenciosamente.
- Limita el OCR de PDF a 50 páginas por defecto para controlar tiempo y memoria.
- No depende de NEXUS.

## Contrato actual

```http
POST /api/v1/documentos/{documento_id}/procesar
```

El resultado se guarda en:

```text
documentos.datos_extraidos.procesamiento_documental
```

Todo resultado incluye procedencia suficiente para diferenciar texto nativo de PDF y texto OCR.
Los campos sugeridos se guardan en
`procesamiento_documental.extraccion_estructurada`; nunca modifican por sí solos un expediente y
se muestran en la bandeja de pendientes para revisión humana.

La confirmación explícita se registra mediante:

```http
PUT /api/v1/documentos/{documento_id}/extraccion-confirmada
```

El dato validado queda separado en `datos_extraidos.extraccion_confirmada` y genera el evento de
auditoría `EXTRACCION_DOCUMENTAL_CONFIRMADA`.
