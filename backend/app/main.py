from fastapi import APIRouter, FastAPI

from app.api.routes import alertas, dashboard, documentos, empresas, expedientes, gestores

app = FastAPI(
    title="FACT CENTRAL",
    description="MVP: ingesta documental, expedientes digitales y alertas tributarias.",
    version="0.1.0",
)

api = APIRouter(prefix="/api/v1")
for modulo in (documentos, expedientes, empresas, gestores, alertas, dashboard):
    api.include_router(modulo.router)
app.include_router(api)


@app.get("/health", tags=["sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}
