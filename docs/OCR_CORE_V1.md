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
- Aplicar automáticamente la clasificación y crear/reutilizar el expediente cuando el tipo y
  todos los campos fiscales superen los umbrales configurados.
- Exigir confirmación humana cuando falten datos, exista una contradicción o la confianza sea
  inferior al umbral.
- Registrar auditoría de procesamiento completado o fallido.

## Límites

- No modifica el original.
- No vincula inferencias ambiguas: registra el motivo y las envía a revisión.
- No clasifica silenciosamente: toda decisión automática conserva evidencia, confianza y
  auditoría.
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
`procesamiento_documental.extraccion_estructurada`. Para Factura o RHE, si están completos y
superan el umbral, se validan con origen `AUTOMATICA`, se crea o reutiliza el expediente fiscal y
se vincula el original en una sola transacción. Los demás casos se muestran en la bandeja de
pendientes con el motivo de revisión.

La confirmación explícita se registra mediante:

```http
PUT /api/v1/documentos/{documento_id}/extraccion-confirmada
```

El dato validado queda separado en `datos_extraidos.extraccion_confirmada`. La validación humana
genera `EXTRACCION_DOCUMENTAL_CONFIRMADA`; la automática genera
`EXTRACCION_DOCUMENTAL_VALIDADA_AUTOMATICAMENTE` y conserva su confianza mínima.

## Creación asistida del expediente

```http
POST /api/v1/documentos/{documento_id}/crear-expediente
```

Este contrato manual acepta una extracción previamente confirmada. El flujo automático aplica la
misma regla de identidad. Busca primero la identidad fiscal
`tenant + receptor + tipo + serie + correlativo + emisor`; si ya existe, reutiliza el expediente y
vincula la nueva evidencia. Si no existe, crea uno y vincula el documento en la misma transacción.
Repetir la operación no crea otro expediente ni duplica su efecto económico.

## Procesamiento de documentos existentes

```http
POST /api/v1/documentos/procesar-pendientes?limit=50
```

Procesa secuencialmente para limitar el consumo de memoria en VPS pequeñas. Reutiliza resultados
de extracción existentes y devuelve cuántos documentos fueron relacionados, quedaron en revisión
o fallaron.
