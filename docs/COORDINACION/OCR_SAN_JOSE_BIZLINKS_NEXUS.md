# Contrato de evidencia OCR San José/Bizlinks → NEXUS IA

**Propietario de lectura:** módulo 10 OCR/PDF. **Consumidor:** módulo 11 NEXUS IA.
Esta propuesta no entrena un modelo ni duplica el motor OCR.

## Salida estructurada prevista

```json
{
  "documento_id": "UUID-del-sistema",
  "tenant_id": "UUID-del-tenant",
  "formato_documental": "factura_estacion_bizlinks",
  "lector": "OCR/PDF",
  "version_parser": "san-jose-bizlinks-v1",
  "estado_lectura": "EXTRAIDO_PENDIENTE_VALIDACION",
  "campos": {
    "serie": {"valor": "F091", "evidencia": "F091-...", "confianza": 0.94},
    "correlativo": {"valor": "00007211", "evidencia": "F091-...", "confianza": 0.94},
    "ruc_emisor": {"valor": "20175642341", "evidencia": "encabezado", "confianza": 0.94},
    "ruc_receptor": {"valor": "RUC-validado-por-OCR", "evidencia": "bloque Cliente", "confianza": 0.94},
    "fecha_emision": {"valor": "2026-09-29", "evidencia": "etiqueta de fecha", "confianza": 0.94},
    "importe_total": {"valor": "28800.00", "evidencia": "Importe Total", "confianza": 0.94},
    "moneda": {"valor": "PEN", "evidencia": "S/ del total", "confianza": 0.94}
  },
  "alertas": [],
  "requiere_confirmacion": true
}
```

Este JSON es **ejemplo de contrato**, no salida comprobada en producción ni un payload nuevo implementado.

- OCR produce campos con evidencia y confianza; NEXUS analiza las anomalías e informa acciones sugeridas sin reinterpretar el archivo crudo.
- La confirmación SUNAT, aprobación del cliente, materialización de expediente, suma contable y permisos dependen de módulos especializados.
- Para rechazos no se sustituye ni borra el original: se emiten motivos verificables, se preservan tenant y UUID y se remite a revisión.
- El caso de regresión incluye F091-00007211 y F091-00007270 frente a F091-00007229 y F091-00007271; el lector debe resistir valores anteriores a etiquetas en texto `pypdf`.
- Los 17 PDF originales proporcionados se usaron para diagnosticar **localmente**, no se almacenan en GitHub como fixtures ni se publican en CI por contener datos fiscales.
- **Brecha no resuelta:** que ambos documentos figuren sin expediente en producción también puede deberse a caché, errores de automatización o controles fiscales. Sin estado JSON/alertas de VPS no se puede adjudicar causa exclusiva al parser.
- Prohibido reprocesamiento masivo, eliminación y despliegue sin aprobación específica; MISD #292 permanece propietario exclusivo de retiradas.
