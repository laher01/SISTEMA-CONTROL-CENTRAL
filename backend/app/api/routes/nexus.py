from fastapi import APIRouter

from app.api.deps import OperativeAuthDep, SessionDep, SettingsDep
from app.schemas import NexusChatIn, NexusChatOut, NexusEstadoOut
from app.services import auditoria
from app.services.nexus import responder

router = APIRouter(prefix="/nexus", tags=["nexus"])


@router.get("/estado", response_model=NexusEstadoOut)
def estado(settings: SettingsDep, auth: OperativeAuthDep) -> NexusEstadoOut:
    from app.services.nexus_knowledge import knowledge_disponible

    return NexusEstadoOut(
        asistente_activo=True,
        consulta_ruc_externa=bool(settings.nexus_ruc_url_template),
        busqueda_internet=bool(settings.nexus_search_url),
        motor_conversacional=bool(settings.nexus_llm_url),
        knowledge_base=knowledge_disponible(settings),
        fuente_oficial_preferida="SUNAT",
    )


@router.post("/chat", response_model=NexusChatOut)
def chat(
    datos: NexusChatIn,
    session: SessionDep,
    settings: SettingsDep,
    auth: OperativeAuthDep,
) -> NexusChatOut:
    respuesta = responder(
        session,
        settings,
        auth,
        datos.mensaje,
        datos.ruta,
        datos.expediente_id,
        datos.historial,
    )
    auditoria.registrar(
        session,
        auth.tenant_id,
        "NEXUS_CONSULTA",
        "nexus",
        auth.cuenta_id,
        {
            "actor": auth.codigo,
            "rol": auth.rol,
            "ruta": datos.ruta,
            "expediente_id": str(datos.expediente_id) if datos.expediente_id else None,
            "accion": respuesta.accion,
            "motor": respuesta.motor,
            "seccion": respuesta.seccion,
            "internet_usado": respuesta.internet_usado,
            "llm_usado": respuesta.llm_usado,
        },
    )
    session.commit()
    return respuesta
