"""Control global de publicación comercial. Sin acceso cruzado a tenants."""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import AuthDep, SessionDep
from app.models import AuditoriaLandingGlobal, ConfiguracionLandingGlobal

router = APIRouter(prefix="/plataforma/landing", tags=["plataforma"])


class EstadoLanding(BaseModel):
    activa: bool
    version: int


class CambiarLanding(BaseModel):
    activa: bool
    version: int = Field(ge=1)


@router.get("/publico", response_model=EstadoLanding)
def estado_publico(session: SessionDep) -> EstadoLanding:
    estado = session.get(ConfiguracionLandingGlobal, 1)
    return EstadoLanding(activa=estado.activa, version=estado.version) if estado else EstadoLanding(activa=True, version=1)


@router.get("", response_model=EstadoLanding)
def estado_admin(session: SessionDep, auth: AuthDep) -> EstadoLanding:
    _exigir_superadmin(auth)
    return estado_publico(session)


@router.put("", response_model=EstadoLanding)
def actualizar_estado(
    datos: CambiarLanding, session: SessionDep, auth: AuthDep
) -> EstadoLanding:
    _exigir_superadmin(auth)
    estado = session.scalar(
        select(ConfiguracionLandingGlobal)
        .where(ConfiguracionLandingGlobal.id == 1)
        .with_for_update()
    )
    if estado is None:
        if datos.version != 1:
            raise HTTPException(status.HTTP_409_CONFLICT, "La configuración cambió; recargue")
        estado = ConfiguracionLandingGlobal(id=1, activa=True, version=1)
        session.add(estado)
        session.flush()
    if estado.version != datos.version:
        raise HTTPException(status.HTTP_409_CONFLICT, "La configuración cambió; recargue")
    if estado.activa != datos.activa:
        session.add(
            AuditoriaLandingGlobal(
                cuenta_id=auth.cuenta_id,
                anterior=estado.activa,
                nuevo=datos.activa,
                version=estado.version + 1,
            )
        )
        estado.activa = datos.activa
        estado.version += 1
        estado.actualizado_por = auth.cuenta_id
    session.commit()
    return EstadoLanding(activa=estado.activa, version=estado.version)


def _exigir_superadmin(auth: object) -> None:
    if (
        getattr(auth, "rol", None) != "SUPERADMIN"
        or getattr(auth, "cambio_clave_obligatorio", True)
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo SUPERADMIN puede administrar la página web")
