"""Administración de buzones y remitentes; sin credenciales OAuth en base de datos."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import AuthDep, SessionDep, TenantDep
from app.models import CorreoBuzon, CorreoRemitente, Gestor, Miembro

router = APIRouter(prefix="/recepcion-correo", tags=["recepcion-correo"])


class BuzonIn(BaseModel):
    direccion: str = Field(min_length=5, max_length=320)
    proveedor: str = Field(pattern="^(GMAIL|OUTLOOK)$")


class RemitenteIn(BaseModel):
    direccion: str = Field(min_length=5, max_length=320)


def _correo(valor: str) -> str:
    direccion = valor.strip().lower()
    if direccion.count("@") != 1 or " " in direccion:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Dirección de correo inválida")
    return direccion


@router.get("/buzones")
def listar_buzones(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: AuthDep
) -> list[dict[str, str | bool]]:
    if auth.rol != "RESPONSABLE" or auth.miembro_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el Responsable administra sus buzones")
    buzon = session.scalars(
        select(CorreoBuzon).where(
            CorreoBuzon.tenant_id == tenant_id, CorreoBuzon.responsable_id == auth.miembro_id
        ).order_by(CorreoBuzon.direccion)
    )
    return [
        {"id": str(b.id), "direccion": b.direccion, "proveedor": b.proveedor, "activo": b.activo}
        for b in buzon
    ]


@router.post("/buzones", status_code=status.HTTP_201_CREATED)
def registrar_buzon(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: AuthDep,
    datos: BuzonIn
) -> dict[str, str]:
    if auth.rol != "RESPONSABLE" or auth.miembro_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el Responsable administra buzones")
    miembro = session.scalar(
        select(Miembro.id).where(
            Miembro.id == auth.miembro_id, Miembro.tenant_id == tenant_id,
            Miembro.rol == "RESPONSABLE", Miembro.activo.is_(True), Miembro.deleted_at.is_(None)
        )
    )
    if miembro is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Responsable no válido")
    buzon = CorreoBuzon(
        tenant_id=tenant_id, responsable_id=auth.miembro_id, direccion=_correo(datos.direccion),
        proveedor=datos.proveedor, activo=False,
    )
    session.add(buzon)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Buzón ya registrado") from exc
    return {"id": str(buzon.id), "estado": "PENDIENTE_OAUTH"}


@router.get("/remitentes")
def listar_remitentes(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: AuthDep
) -> list[dict[str, str | bool]]:
    if auth.rol != "GESTOR" or auth.gestor_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Gestor consulta sus remitentes")
    rows = session.scalars(select(CorreoRemitente).where(
        CorreoRemitente.tenant_id == tenant_id, CorreoRemitente.gestor_id == auth.gestor_id
    ).order_by(CorreoRemitente.direccion))
    return [{"id": str(r.id), "direccion": r.direccion, "activo": r.activo} for r in rows]


@router.post("/remitentes", status_code=status.HTTP_201_CREATED)
def registrar_remitente(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: AuthDep,
    datos: RemitenteIn
) -> dict[str, str]:
    if auth.rol != "GESTOR" or auth.gestor_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Gestor registra remitentes")
    gestor = session.scalar(select(Gestor.id).where(
        Gestor.id == auth.gestor_id, Gestor.tenant_id == tenant_id, Gestor.deleted_at.is_(None)
    ))
    if gestor is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Gestor inválido")
    direccion = _correo(datos.direccion)
    existe = session.scalar(select(CorreoRemitente.id).where(
        CorreoRemitente.tenant_id == tenant_id,
        CorreoRemitente.direccion == direccion,
        CorreoRemitente.activo.is_(True),
    ))
    if existe is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Remitente ya asignado")
    registro = CorreoRemitente(
        tenant_id=tenant_id, gestor_id=auth.gestor_id, direccion=direccion, activo=True
    )
    session.add(registro)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Remitente ya registrado") from exc
    return {"id": str(registro.id), "estado": "ACTIVO"}
