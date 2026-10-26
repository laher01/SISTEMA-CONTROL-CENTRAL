# Operaciones de pesca: backend inicial

El módulo `/api/v1/pesca` acompaña al flujo documental actual de FACT CENTRAL y registra la
descarga desde muelle hasta la recepción por vehículo en planta. Sus tablas usan el tenant ya
configurado por el backend.

## Flujo implementado

1. Crear operación diaria. La fecha se completa con la fecha local de `FC_ZONA_HORARIA` si no se
   envía en la solicitud.
2. Vincular embarcaciones por matrícula y registrar patrón/armador e intermediario.
3. Registrar vehículos, asignarles las cargas de una o más embarcaciones y conservar peso de
   muelle y cajas por asignación.
4. Registrar el turno y el inicio de atención en planta. Las fechas y horas de inicio y fin se
   pueden informar manualmente para casos sin señal o batería. La fecha/hora final toma el
   momento actual si se omite; se puede indicar expresamente que no se registrará.
5. Registrar por vehículo el resultado de planta (`completo`, `parcial` o `rechazado`), solo el
   peso aceptado, la unidad y, cuando aplique, las cajas rechazadas y el motivo. Las unidades se
   normalizan a kg para las comparaciones y sumas.
6. Subir la evidencia del peso de planta y cerrar el registro del vehículo. La operación solo
   cierra cuando todos sus vehículos tienen peso y evidencia.

Los archivos aceptados son PDF, JPG, PNG y WEBP. Un documento puede quedar vinculado a varios
vehículos para usar una sola acta general o certificado. Cada cambio operativo importante crea
una entrada de historial con actor, fecha y detalle.

## Rutas principales

- `POST/GET /api/v1/pesca/operaciones`
- `POST /api/v1/pesca/operaciones/{id}/embarcaciones`
- `POST /api/v1/pesca/operaciones/{id}/vehiculos`
- `POST /api/v1/pesca/vehiculos/{id}/cargas`
- `POST /api/v1/pesca/vehiculos/{id}/planta/iniciar`
- `POST /api/v1/pesca/vehiculos/{id}/planta`
- `POST /api/v1/pesca/operaciones/{id}/documentos` (multipart: `archivo`, `tipo`, y opcionalmente
  `vehiculo_ids` repetido por cada vehículo)
- `GET /api/v1/pesca/operaciones/{id}/documentacion` y `/resumen`
- `GET /api/v1/pesca/operaciones/{id}/historial`
- `POST /api/v1/pesca/vehiculos/{id}/planta/cerrar`
- `POST /api/v1/pesca/operaciones/{id}/cerrar`

Tipos de documento conocidos: `guia_remitente`, `guia_transportista`, `acta_fiscalizacion`,
`formato_descarga`, `certificado_procedencia`, `certificado_captura`, `peso_planta`, `otro`.
La verificación de documentación enumera faltantes por vehículo para preparar su expediente
operativo.

## Límite actual

Este primer corte no implementa todavía inicio de sesión propio ni permisos por rol dentro de la
API. El backend existente usa Cloudflare Access como barrera de entrada al entorno de prueba; el
El módulo toma el actor del encabezado de identidad inyectado por Cloudflare Access; `X-Actor` es
solo una alternativa para desarrollo local y no autentica ni autoriza al usuario. Antes de habilitar
el módulo a usuarios finales se deben aplicar permisos por rol para jefe de bahía, encargado y
apuntadores. No se deben publicar estas rutas sin esa protección.

La emisión, presentación y cobro de facturas queda fuera del módulo operativo.
