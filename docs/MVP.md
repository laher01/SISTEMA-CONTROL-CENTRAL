# FACT CENTRAL — MVP

Versión 1.0 · Este documento tiene prioridad sobre el resto de la documentación
mientras el MVP no esté terminado.

## Objetivo

Demostrar con documentos reales de 1–2 empresas que FACT CENTRAL convierte
comprobantes de compra dispersos en **expedientes auditables** y ahorra trabajo
manual de revisión.

## Alcance (sí entra)

1. **Ingesta**: subir archivos (XML UBL 2.1 de SUNAT, PDF, imágenes) por API.
   El original se guarda sin modificar.
2. **Duplicados**: SHA-256 del contenido (nunca el nombre del archivo). Un
   archivo repetido se rechaza indicando el documento existente.
3. **Extracción automática desde XML**: Factura (`Invoice`, tipo 01) y Guía de
   Remisión (`DespatchAdvice`, tipos 09/31). Se obtiene emisor, receptor,
   serie-correlativo, fecha, moneda e importe.
4. **Empresas**: emisores y receptores se crean automáticamente por RUC. Si el
   receptor no está autorizado ("trabaja con nosotros"), el expediente queda
   pendiente de aprobación.
5. **Expedientes**: uno por `RUC receptor + tipo + serie + correlativo + RUC
   emisor`. XML y PDF con extracción completa se vinculan automáticamente; imágenes y documentos
   ambiguos quedan para revisión.
6. **Estado del expediente** (semáforo de BUSINESS_RULES):
   - Principales: `FACT + GRR + VCHR` (o `RHE + VCHR`; la GRR puede marcarse
     como no requerida para servicios).
   - **VERDE**: principales completos.
   - **AMARILLO**: principales completos, pero falta un documento importante
     (RET cuando el receptor es agente de retención).
   - **NARANJA**: falta un principal y aún no vence el plazo.
   - **ROJO**: falta un principal después del día 7 del mes siguiente a la
     emisión (día configurable).
7. **Alertas**: bancarización sin voucher (importe ≥ S/ 2,000 o ≥ US$ 500,
   configurable), retención pendiente, receptor no autorizado, expediente
   vencido.
8. **Dashboard básico** (API): expedientes por estado, monto bancarizado / no
   bancarizado, alertas abiertas, documentos pendientes de relación.
9. **Auditoría**: toda acción relevante queda registrada.

## Fuera de alcance (después del MVP)

- NEXUS, agentes, motores cognitivos → `docs/futuro/nexus/`.
- Infraestructura multi-nodo/multi-región → `docs/futuro/infraestructura/`.
- Multi-tenant real, suscripciones y facturación SaaS (el esquema ya incluye
  `tenant_id`, pero el MVP opera con un solo tenant).
- Interpretación semántica avanzada de documentos con formatos no reconocidos; el OCR y la
  extracción determinista de PDF/imágenes ya forman parte del flujo ejecutable.
- Comisiones, adelantos, liquidaciones y pagos a gestores.
- Clasificación de productos y validación del giro comercial.
- Autenticación JWT/RBAC (siguiente paso inmediato tras validar el flujo).
- Frontend (el MVP expone API REST + documentación OpenAPI en `/docs`).

## Stack

Python 3.13 · FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL 17 · Docker.
Esquema de datos: [`ESQUEMA_MVP.md`](ESQUEMA_MVP.md).

## Criterios de éxito

- Cargar ≥ 500 documentos reales sin duplicados ni pérdida de originales.
- ≥ 90 % de las facturas XML generan su expediente sin intervención manual.
- La secretaría puede ver qué expedientes están incompletos y qué falta.
- Tiempo de revisión por expediente menor que el proceso manual actual.

## Siguientes pasos tras el MVP

1. Autenticación y roles (Administrador, Secretaría, Usuario, Gestor).
2. Frontend React con el semáforo de expedientes.
3. OCR de PDF/imágenes.
4. Comisiones y pagos a gestores.
5. Multi-tenant real.
