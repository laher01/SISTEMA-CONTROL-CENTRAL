"""Administración global del CMS, exclusivamente SUPERADMIN.

La publicación editorial no activa automáticamente la página pública.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import AuthDep, SessionDep
from app.api.routes.pagina_web import _exigir_superadmin
from app.services.cms_landing_core import EstadoEditorial
from app.services.cms_landing_store import (
    cambiar_estado,
    guardar_borrador,
    revision_table,
    publicacion_table,
)
from app.services.cms_landing_validation import ContenidoCms

router = APIRouter(prefix="/plataforma/cms", tags=["plataforma-cms"])


class BorradorCms(BaseModel):
    version: int = Field(ge=0)
    contenido: ContenidoCms


class TransicionCms(BaseModel):
    version: int = Field(ge=1)
    destino: EstadoEditorial


@router.get("")
def consultar_cms(session: SessionDep, auth: AuthDep) -> dict[str, object]:
    _exigir_superadmin(auth)
    fila = (
        session.execute(select(revision_table).where(revision_table.c.id == 1))
        .mappings()
        .one_or_none()
    )
    if fila is None:
        return {"existe": False, "version": 0, "estado": "borrador", "contenido": None}
    return {
        "existe": True,
        "version": fila["version"],
        "estado": fila["estado"],
        "contenido": fila["contenido"],
    }


@router.put("/borrador")
def guardar_cms(datos: BorradorCms, session: SessionDep, auth: AuthDep) -> dict[str, object]:
    _exigir_superadmin(auth)
    try:
        nueva = guardar_borrador(
            session,
            contenido=datos.contenido.model_dump(),
            version_esperada=datos.version,
            rol=auth.rol,
            actor_id=auth.cuenta_id,
        )
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"version": nueva.version, "estado": nueva.estado, "existe": True}


@router.post("/transicion")
def transicionar_cms(datos: TransicionCms, session: SessionDep, auth: AuthDep) -> dict[str, object]:
    _exigir_superadmin(auth)
    try:
        nueva = cambiar_estado(
            session,
            destino=datos.destino,
            version_esperada=datos.version,
            rol=auth.rol,
            actor_id=auth.cuenta_id,
        )
    except (ValueError, LookupError) as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"version": nueva.version, "estado": nueva.estado, "existe": True}


@router.get("/publico")
def contenido_cms_publico(session: SessionDep) -> dict[str, object]:
    """Solo contenido aprobado y publicado; no expone borradores ni identidades."""
    from app.models import ConfiguracionLandingGlobal

    configuracion = session.get(ConfiguracionLandingGlobal, 1)
    if configuracion is None or configuracion.activa is not True:
        return {"disponible": False, "contenido": None}
    fila = (
        session.execute(
            select(publicacion_table).where(publicacion_table.c.id == 1)
        )
        .mappings()
        .one_or_none()
    )
    if fila is None:
        return {"disponible": False, "contenido": None}
    # Validar de nuevo en salida, incluso ante datos antiguos de base de datos.
    try:
        contenido = ContenidoCms.model_validate(fila["contenido"])
    except ValueError:
        return {"disponible": False, "contenido": None}
    return {"disponible": True, "contenido": contenido.model_dump()}
