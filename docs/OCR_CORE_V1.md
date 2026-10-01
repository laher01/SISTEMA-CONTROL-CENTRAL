# OCR Core v1 — extracción documental verificable

## Propósito

OCR Core obtiene texto utilizable desde documentos ya recibidos y almacenados. Su resultado
aporta contexto al Expediente Inteligente, pero no reemplaza el archivo original ni convierte
automáticamente una inferencia en un hecho aprobado.

## Responsabilidad

- Extraer la capa de texto de PDF mediante `pypdf`.
- Marcar como `requiere_ocr` los PDF sin capa de texto.
- Ejecutar Tesseract en imágenes JPEG, PNG, TIFF y WEBP cuando esté instalado.
- Conservar método, motor, páginas, idioma y confianza junto con el texto extraído.
- Proponer un tipo documental mediante indicadores explícitos.
- Exigir confirmación humana antes de aplicar la clasificación sugerida.
- Registrar auditoría de procesamiento completado o fallido.

## Límites

- No modifica el original.
- No vincula automáticamente el documento a un expediente.
- No clasifica silenciosamente.
- No interpreta todavía PDF escaneado; lo marca para una fase OCR posterior.
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
