"""Configuración multi-tenant de recepción de correos.

Las direcciones son registros, no conexiones activas: OAuth se autoriza aparte.
"""

import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import OperativeAuthDep, SessionDep, TenantDep
from app.core.config import get_settings
from app.enums import RolMiembro
from app.models import CorreoBuzon, CorreoMensaje, CorreoRemitente, Gestor

router = APIRouter(prefix="/correo", tags=["correo"])


def _solo_administracion(rol: str) -> None:
    if rol != RolMiembro.ADMINISTRADOR:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Administración configura correos")


class BuzonIn(BaseModel):
    direccion: str = Field(min_length=5, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    proveedor: str = "GOOGLE"


class RemitenteIn(BaseModel):
    direccion: str = Field(min_length=5, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    gestor_id: uuid.UUID


@router.get("/buzones")
def listar_buzones(
    session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep
) -> list[dict[str, object]]:
    _solo_administracion(auth.rol)
    return [
        {
            "id": str(b.id),
            "direccion": b.direccion,
            "proveedor": b.proveedor,
            "activo": b.activo,
            "ultimo_error": b.ultimo_error,
        }
        for b in session.scalars(select(CorreoBuzon).where(CorreoBuzon.tenant_id == tenant_id))
    ]


@router.post("/buzones", status_code=status.HTTP_201_CREATED)
def registrar_buzon(
    datos: BuzonIn, session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep
) -> dict[str, str]:
    _solo_administracion(auth.rol)
    proveedor = datos.proveedor.upper().strip()
    if proveedor not in ("GOOGLE", "MICROSOFT", "IMAP"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Proveedor no soportado")
    direccion = str(datos.direccion).strip().lower()
    existente = session.scalar(
        select(CorreoBuzon).where(
            CorreoBuzon.tenant_id == tenant_id, CorreoBuzon.direccion == direccion
        )
    )
    if existente:
        raise HTTPException(status.HTTP_409_CONFLICT, "Buzón ya registrado")
    nuevo = CorreoBuzon(
        tenant_id=tenant_id,
        direccion=direccion,
        proveedor=proveedor,
        responsable_id=auth.miembro_id,
        activo=False,
    )
    session.add(nuevo)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Buzón ya registrado") from exc
    return {"id": str(nuevo.id), "estado": "PENDIENTE_OAUTH"}


@router.get("/remitentes")
def listar_remitentes(
    session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep
) -> list[dict[str, str]]:
    _solo_administracion(auth.rol)
    registros = session.execute(
        select(CorreoRemitente, Gestor)
        .join(Gestor, CorreoRemitente.gestor_id == Gestor.id)
        .where(CorreoRemitente.tenant_id == tenant_id, Gestor.tenant_id == tenant_id)
    )
    return [
        {"id": str(r.id), "direccion": r.direccion, "gestor_id": str(g.id), "gestor": g.nombre}
        for r, g in registros
    ]


@router.post("/remitentes", status_code=status.HTTP_201_CREATED)
def registrar_remitente(
    datos: RemitenteIn, session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep
) -> dict[str, str]:
    _solo_administracion(auth.rol)
    gestor = session.get(Gestor, datos.gestor_id)
    if gestor is None or gestor.tenant_id != tenant_id or gestor.deleted_at is not None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Gestor no autorizado")
    direccion = str(datos.direccion).strip().lower()
    registrado = session.scalar(
        select(CorreoRemitente).where(
            CorreoRemitente.tenant_id == tenant_id,
            CorreoRemitente.direccion == direccion,
            CorreoRemitente.activo.is_(True),
        )
    )
    if registrado is not None:
        if registrado.gestor_id != gestor.id:
            raise HTTPException(status.HTTP_409_CONFLICT, "Remitente asignado a otro Gestor")
        raise HTTPException(status.HTTP_409_CONFLICT, "Remitente ya registrado")
    nuevo = CorreoRemitente(
        tenant_id=tenant_id, direccion=direccion, gestor_id=gestor.id, activo=True
    )
    session.add(nuevo)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Remitente ya registrado") from exc
    return {"id": str(nuevo.id), "gestor_id": str(gestor.id)}


@router.get("/mi-recepcion")
def mi_recepcion(
    session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep
) -> dict[str, object]:
    """Bandeja de solo lectura acotada al Gestor autenticado."""
    if auth.rol != "GESTOR" or auth.gestor_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acceso exclusivo de Gestor")
    gestor = session.get(Gestor, auth.gestor_id)
    if gestor is None or gestor.tenant_id != tenant_id or gestor.deleted_at is not None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Gestor sin ámbito válido")
    remitentes = list(
        session.scalars(
            select(CorreoRemitente.direccion)
            .where(
                CorreoRemitente.tenant_id == tenant_id,
                CorreoRemitente.gestor_id == gestor.id,
                CorreoRemitente.activo.is_(True),
            )
            .order_by(CorreoRemitente.direccion)
        )
    )
    mensajes = list(
        session.scalars(
            select(CorreoMensaje)
            .where(
                CorreoMensaje.tenant_id == tenant_id,
                CorreoMensaje.gestor_id == gestor.id,
            )
            .order_by(CorreoMensaje.created_at.desc())
            .limit(100)
        )
    )
    return {
        "gestor": gestor.nombre,
        "remitentes": remitentes,
        "mensajes": [
            {
                "id": str(m.id),
                "buzon_id": str(m.buzon_id),
                "remitente": m.remitente,
                "estado": m.estado,
                "fecha": m.created_at.isoformat(),
            }
            for m in mensajes
        ],
    }


@router.get("/incidencias")
def listar_incidencias(
    session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep
) -> list[dict[str, str | None]]:
    """Incidencias de correo del tenant para la Administración, solo lectura."""
    _solo_administracion(auth.rol)
    registros = session.execute(
        select(CorreoMensaje, CorreoBuzon, Gestor)
        .join(
            CorreoBuzon,
            (CorreoMensaje.buzon_id == CorreoBuzon.id) & (CorreoBuzon.tenant_id == tenant_id),
        )
        .outerjoin(
            Gestor,
            (CorreoMensaje.gestor_id == Gestor.id) & (Gestor.tenant_id == tenant_id),
        )
        .where(
            CorreoMensaje.tenant_id == tenant_id,
            CorreoMensaje.estado.in_(("REVISION", "PENDIENTE")),
        )
        .order_by(CorreoMensaje.created_at.desc(), CorreoMensaje.id.desc())
        .limit(100)
    )
    return [
        {
            "id": str(m.id),
            "fecha": m.created_at.isoformat(),
            "buzon": b.direccion,
            "remitente": m.remitente,
            "gestor": g.nombre if g else None,
            "estado": m.estado,
            "motivo": m.error,
        }
        for m, b, g in registros
    ]


@router.get("/estado-proveedores")
def estado_proveedores(auth: OperativeAuthDep) -> dict[str, bool]:
    """Informa preparación de OAuth sin exponer credenciales ni simular una conexión."""
    _solo_administracion(auth.rol)
    config = get_settings()
    return {
        "google_configurado": bool(
            config.google_oauth_client_id
            and config.google_oauth_redirect_uri
            and config.google_oauth_redirect_uri.startswith("https://")
        ),
        "microsoft_configurado": bool(
            config.microsoft_oauth_client_id
            and config.microsoft_oauth_redirect_uri
            and config.microsoft_oauth_redirect_uri.startswith("https://")
        ),
    }
