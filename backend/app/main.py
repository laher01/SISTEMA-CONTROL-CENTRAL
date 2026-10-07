from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    alertas,
    dashboard,
    documentos,
    empresas,
    expedientes,
    gestores,
    miembros,
    produccion,
)
from app.core.config import get_settings

app = FastAPI(
    title="FACT CENTRAL",
    description="MVP: ingesta documental, expedientes digitales y alertas tributarias.",
    version="0.1.0",
)

cors_origins = get_settings().cors_origins
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type"],
    )

api = APIRouter(prefix="/api/v1")
for modulo in (
    documentos,
    expedientes,
    empresas,
    miembros,
    gestores,
    alertas,
    dashboard,
    produccion,
):
    api.include_router(modulo.router)
app.include_router(api)


@app.get("/health", tags=["sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}
