from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    alertas,
    auth,
    configuracion,
    configuracion_acceso,
    dashboard,
    documentos,
    empresas,
    expedientes,
    gestores,
    mensajes_alerta,
    miembros,
    nexus,
    pagos,
    produccion,
    registros,
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
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )

api = APIRouter(prefix="/api/v1")
api.include_router(auth.router)
for modulo in (
    documentos,
    expedientes,
    registros,
    empresas,
    miembros,
    gestores,
    alertas,
    mensajes_alerta,
    nexus,
    dashboard,
    produccion,
    pagos,
    configuracion,
    configuracion_acceso,
):
    api.include_router(modulo.router)
app.include_router(api)


@app.get("/health", tags=["sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}
