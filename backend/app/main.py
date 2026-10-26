from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import alertas, dashboard, documentos, empresas, expedientes, gestores
from app.pesca import routes as pesca
from app.core.config import get_settings

app = FastAPI(
    title="FACT CENTRAL",
    description=(
        "Gestión documental, expedientes y operaciones de descarga de pesca con recepción por vehículo."
    ),
    version="0.1.0",
)

cors_origins = get_settings().cors_origins
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type", "X-Actor", "Cf-Access-Authenticated-User-Email"],
    )

api = APIRouter(prefix="/api/v1")
for modulo in (documentos, expedientes, empresas, gestores, alertas, dashboard, pesca):
    api.include_router(modulo.router)
app.include_router(api)


@app.get("/health", tags=["sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}
