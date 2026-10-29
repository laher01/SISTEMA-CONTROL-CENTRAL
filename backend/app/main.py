from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    administraciones,
    alertas,
    asignaciones_emisores,
    auth,
    chat,
    comisiones,
    configuracion,
    configuracion_acceso,
    contabilidad_items,
    correo,
    dashboard,
    documentos,
    empresas,
    expedientes,
    gerencias,
    gestores,
    mantenimiento,
    mensajes_alerta,
    miembros,
    nexus,
    pagina_web,
    pagos,
    pagos_gestores,
    pagos_responsables,
    produccion,
    registros,
    responsable,
    solicitudes_carga_emisor,
    solicitudes_retiro_misd,
)
from app.pesca import routes as pesca
from app.core.config import get_settings

app = FastAPI(
    title="S.P.T. · Sistema Pesquero de Trazabilidad",
    description=(
        "Plataforma para la trazabilidad pesquera, la gestión documental y la recepción de descargas."
    ),
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
    administraciones,
    asignaciones_emisores,
    solicitudes_carga_emisor,
    solicitudes_retiro_misd,
    correo,
    documentos,
    chat,
    comisiones,
    contabilidad_items,
    expedientes,
    registros,
    empresas,
    miembros,
    gestores,
    gerencias,
    alertas,
    mensajes_alerta,
    nexus,
    dashboard,
    produccion,
    pagos,
    pagos_gestores,
    pagos_responsables,
    responsable,
    configuracion,
    configuracion_acceso,
    pagina_web,
    mantenimiento,
    pesca,
):
    api.include_router(modulo.router)
app.include_router(api)


@app.get("/health", tags=["sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}
