# FACT CENTRAL — Backend MVP

API FastAPI que implementa el alcance de `docs/MVP.md` sobre el esquema de `docs/ESQUEMA_MVP.md`.

## Requisitos

- Python 3.13 y [uv](https://docs.astral.sh/uv/)
- PostgreSQL 17 (incluido en `docker-compose.yml`)

## Puesta en marcha

```bash
cd backend
uv sync
cp .env.example .env
docker compose up -d postgres
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Documentación interactiva: http://localhost:8000/docs

## Flujo

1. `POST /api/v1/documentos` (multipart `archivo`, opcional `tipo_documento`, `expediente_id`, `gestor_id`).
   - SHA-256 del contenido; si ya existe en el tenant responde `409`.
   - El original se guarda sin modificar en `FC_STORAGE_DIR/<tenant>/<sha[:2]>/<sha>`.
   - XML UBL 2.1: factura (`01`) crea o encuentra el expediente; guía (`09`/`31`) se asocia
     a la factura referenciada. Otros archivos quedan `PENDIENTE_CLASIFICACION`.
2. `POST /api/v1/documentos/{id}/vincular` asocia un PDF/imagen (Voucher, RET, ...) a un expediente.
3. `PATCH /api/v1/empresas/{id}` marca receptores como autorizados o agentes de retención.
4. `POST /api/v1/expedientes/recalcular` reevalúa estados (p. ej. tarea diaria para vencimientos).
5. `GET /api/v1/dashboard/resumen`, `/expedientes`, `/alertas` para consulta.
6. `POST /api/v1/documentos/{id}/procesar` extrae texto de PDF o ejecuta OCR sobre
   imágenes. Guarda método, motor, confianza e idioma, y puede sugerir un tipo documental
   que siempre requiere confirmación humana.
7. `GET /api/v1/documentos/{id}/relaciones-sugeridas` compara serie-correlativo, RUC e
   importe con expedientes del mismo tenant. Retorna candidatos con puntaje y evidencias;
   nunca vincula automáticamente.

## Estados del expediente

| Estado   | Condición                                                          |
|----------|--------------------------------------------------------------------|
| VERDE    | Documentos principales completos y sin retención pendiente         |
| AMARILLO | Principales completos; falta constancia de retención               |
| NARANJA  | Falta algún documento principal y aún no vence el plazo            |
| ROJO     | Falta algún documento principal y pasó el día límite del mes siguiente |

Principales: comprobante (FACT/RHE) + GRR (si `requiere_guia`, nunca para RHE) + VCHR.

## Calidad

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy app
uv run pytest                                   # SQLite en memoria
FC_TEST_DATABASE_URL=postgresql+psycopg://fact:fact@localhost:5432/fact_central uv run pytest
```

Con PostgreSQL se verifica además que la migración Alembic coincide con los modelos.

## Limitaciones conocidas del MVP

- Un solo tenant (`FC_TENANT_DEFAULT`); sin autenticación.
- La clasificación sugerida por OCR no se aplica automáticamente; PDF e imágenes se vinculan
  manualmente al expediente.
- Los PDF con texto se leen mediante `pypdf`; las imágenes usan Tesseract si está instalado.
  Los PDF escaneados se detectan y quedan marcados como `requiere_ocr`.
- Almacenamiento local; S3-compatible queda para una fase posterior.
