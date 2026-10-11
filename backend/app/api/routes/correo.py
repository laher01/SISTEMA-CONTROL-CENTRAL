"""Configuración multi-tenant de recepción de correos.

Las direcciones son registros, no conexiones activas: OAuth se autoriza aparte.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import OperativeAuthDep, SessionDep, TenantDep
from app.core.config import get_settings
from app.enums import RolMiembro
from app.models import (
    CorreoBuzon,
    CorreoMensaje,
    CorreoOAuthCredencial,
    CorreoOAuthIntento,
    CorreoRemitente,
    CuentaAcceso,
    Gestor,
    Miembro,
)
from app.services.google_oauth_correo import (
    GoogleOAuthError,
    cifrar_refresh_token,
    comprobar_buzon_google,
    crear_url_autorizacion,
    intercambiar_codigo_google,
    nuevo_desafio_pkce,
)
from app.services.microsoft_oauth_correo import (
    MicrosoftOAuthError,
    comprobar_buzon_microsoft,
    crear_url_microsoft,
    intercambiar_codigo_microsoft,
)
from app.tenant_host import nombre_host, validar_sesion_host

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
            and config.google_oauth_client_secret
            and config.correo_token_encryption_key
            and config.google_oauth_redirect_uri
            and config.google_oauth_redirect_uri.startswith("https://")
        ),
        "microsoft_configurado": bool(
            config.microsoft_oauth_client_id
            and config.microsoft_oauth_redirect_uri
            and config.microsoft_oauth_redirect_uri.startswith("https://")
        ),
    }


@router.post("/buzones/{buzon_id}/google/iniciar")
def iniciar_google_oauth(
    buzon_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, str]:
    """Crea autorización PKCE temporal, asociada al tenant y administrador.

    Es únicamente el inicio. No activa buzones ni considera OAuth completado.
    """
    _solo_administracion(auth.rol)
    config = get_settings()
    if not all(
        (
            config.google_oauth_client_id,
            config.google_oauth_client_secret,
            config.google_oauth_redirect_uri,
            config.correo_token_encryption_key,
        )
    ):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Google OAuth no configurado")
    buzon = session.scalar(
        select(CorreoBuzon).where(
            CorreoBuzon.id == buzon_id,
            CorreoBuzon.tenant_id == tenant_id,
            CorreoBuzon.proveedor == "GOOGLE",
        )
    )
    if buzon is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Buzón Google no encontrado")
    if buzon.activo:
        raise HTTPException(status.HTTP_409_CONFLICT, "Buzón ya activo")
    state = secrets.token_urlsafe(48)
    verifier, challenge = nuevo_desafio_pkce()
    try:
        url = crear_url_autorizacion(
            client_id=config.google_oauth_client_id or "",
            redirect_uri=config.google_oauth_redirect_uri or "",
            state=state,
            code_challenge=challenge,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "OAuth mal configurado") from exc
    intento = CorreoOAuthIntento(
        tenant_id=tenant_id,
        buzon_id=buzon.id,
        cuenta_id=auth.cuenta_id,
        state_hash=hashlib.sha256(state.encode("ascii")).hexdigest(),
        pkce_verifier=verifier,
        vence_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    session.add(intento)
    session.commit()
    return {"authorization_url": url, "estado": "PENDIENTE_CONSENTIMIENTO"}


@router.get("/google/callback")
def callback_google_oauth(
    request: Request,
    session: SessionDep,
    state: str = "",
    code: str = "",
    error: str = "",
) -> RedirectResponse:
    """Valida state one-shot y buzón exacto sin depender de cookies cross-site."""
    if not state or not code or error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Autorización Google cancelada")
    estado_hash = hashlib.sha256(state.encode("utf-8")).hexdigest()
    intento = session.scalar(
        select(CorreoOAuthIntento)
        .where(
            CorreoOAuthIntento.state_hash == estado_hash,
            CorreoOAuthIntento.consumido_at.is_(None),
        )
        .with_for_update()
    )
    ahora = datetime.now(UTC)
    if intento is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Estado OAuth inválido")
    tenant_id = intento.tenant_id
    config = get_settings()
    from urllib.parse import urlparse

    host_permitido = urlparse(config.google_oauth_redirect_uri or "").hostname
    if not host_permitido or nombre_host(request) != host_permitido:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Dominio de callback no autorizado")
    validar_sesion_host(request, session, config, tenant_id)
    cuenta = session.scalar(
        select(CuentaAcceso).where(
            CuentaAcceso.id == intento.cuenta_id,
            CuentaAcceso.tenant_id == tenant_id,
            CuentaAcceso.activo.is_(True),
        )
    )
    if cuenta is None or cuenta.miembro_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administrador inválido")
    miembro = session.scalar(
        select(Miembro).where(
            Miembro.id == cuenta.miembro_id,
            Miembro.tenant_id == tenant_id,
            Miembro.rol == "ADMINISTRADOR",
            Miembro.activo.is_(True),
        )
    )
    if miembro is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administrador no autorizado")
    vence = intento.vence_at
    if vence.tzinfo is None:
        vence = vence.replace(tzinfo=UTC)
    if vence < ahora:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Autorización OAuth vencida")
    buzon = session.scalar(
        select(CorreoBuzon).where(
            CorreoBuzon.id == intento.buzon_id,
            CorreoBuzon.tenant_id == tenant_id,
            CorreoBuzon.proveedor == "GOOGLE",
        )
    )
    if buzon is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Buzón inválido")
    intento.consumido_at = ahora
    session.commit()
    config = get_settings()
    if not all(
        (
            config.google_oauth_client_id,
            config.google_oauth_client_secret,
            config.google_oauth_redirect_uri,
            config.correo_token_encryption_key,
        )
    ):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "OAuth no configurado")
    try:
        acceso, refresco, scope = intercambiar_codigo_google(
            code=code,
            verifier=intento.pkce_verifier,
            client_id=config.google_oauth_client_id or "",
            client_secret=config.google_oauth_client_secret or "",
            redirect_uri=config.google_oauth_redirect_uri or "",
        )
        comprobar_buzon_google(access_token=acceso, direccion=buzon.direccion)
        token_cifrado = cifrar_refresh_token(refresco, config.correo_token_encryption_key or "")
    except GoogleOAuthError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    credencial = session.scalar(
        select(CorreoOAuthCredencial).where(
            CorreoOAuthCredencial.buzon_id == buzon.id,
            CorreoOAuthCredencial.tenant_id == tenant_id,
        )
    )
    if credencial is None:
        credencial = CorreoOAuthCredencial(
            tenant_id=tenant_id,
            buzon_id=buzon.id,
            proveedor="GOOGLE",
            token_cifrado=token_cifrado,
            permisos=scope,
            verificado_at=ahora,
        )
        session.add(credencial)
    else:
        credencial.token_cifrado = token_cifrado
        credencial.permisos = scope
        credencial.verificado_at = ahora
    buzon.activo = True
    buzon.ultimo_error = None
    session.commit()
    return RedirectResponse(url="/configuracion?seccion=correos&oauth=conectado", status_code=303)


@router.post("/buzones/{buzon_id}/microsoft/iniciar")
def iniciar_microsoft_oauth(
    buzon_id: uuid.UUID, session: SessionDep, tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, str]:
    """Solo administración puede conectar un buzón de su tenant."""
    _solo_administracion(auth.rol)
    config = get_settings()
    if not all((
        config.microsoft_oauth_client_id, config.microsoft_oauth_client_secret,
        config.microsoft_oauth_redirect_uri, config.correo_token_encryption_key,
    )):
        raise HTTPException(503, "Microsoft OAuth no configurado")
    buzon = session.scalar(select(CorreoBuzon).where(
        CorreoBuzon.id == buzon_id,
        CorreoBuzon.tenant_id == tenant_id,
        CorreoBuzon.proveedor == "MICROSOFT",
    ))
    if buzon is None:
        raise HTTPException(404, "Buzón Microsoft no encontrado")
    if buzon.activo:
        raise HTTPException(409, "Buzón ya activo")
    state = secrets.token_urlsafe(48)
    verifier, challenge = nuevo_desafio_pkce()
    try:
        url = crear_url_microsoft(
            client_id=config.microsoft_oauth_client_id or "",
            redirect_uri=config.microsoft_oauth_redirect_uri or "",
            state=state, code_challenge=challenge,
        )
    except ValueError as exc:
        raise HTTPException(503, "Configuración Microsoft OAuth inválida") from exc
    session.add(CorreoOAuthIntento(
        tenant_id=tenant_id, buzon_id=buzon.id, cuenta_id=auth.cuenta_id,
        state_hash=hashlib.sha256(state.encode("ascii")).hexdigest(),
        pkce_verifier=verifier, vence_at=datetime.now(UTC) + timedelta(minutes=10),
    ))
    session.commit()
    return {"authorization_url": url, "estado": "PENDIENTE_CONSENTIMIENTO"}


@router.get("/microsoft/callback")
def callback_microsoft_oauth(
    request: Request, session: SessionDep,
    state: str = "", code: str = "", error: str = "",
) -> RedirectResponse:
    """Callback de un solo uso, con tenant, administrador y buzón verificados."""
    if error or not code or not state:
        raise HTTPException(400, "Autorización Microsoft cancelada")
    config = get_settings()
    from urllib.parse import urlparse

    redirect_uri = config.microsoft_oauth_redirect_uri or ""
    permitted_host = urlparse(redirect_uri).hostname
    if not permitted_host or nombre_host(request) != permitted_host:
        raise HTTPException(403, "Host de callback no autorizado")
    intento = session.scalar(select(CorreoOAuthIntento).where(
        CorreoOAuthIntento.state_hash == hashlib.sha256(state.encode("utf-8")).hexdigest(),
        CorreoOAuthIntento.consumido_at.is_(None),
    ).with_for_update())
    if intento is None:
        raise HTTPException(400, "Estado OAuth inválido")
    ahora = datetime.now(UTC)
    vence = intento.vence_at
    if vence.tzinfo is None:
        vence = vence.replace(tzinfo=UTC)
    if vence < ahora:
        raise HTTPException(400, "Autorización vencida")
    validar_sesion_host(request, session, config, intento.tenant_id)
    cuenta = session.scalar(select(CuentaAcceso).where(
        CuentaAcceso.id == intento.cuenta_id,
        CuentaAcceso.tenant_id == intento.tenant_id,
        CuentaAcceso.activo.is_(True),
    ))
    miembro = session.scalar(select(Miembro).where(
        Miembro.id == cuenta.miembro_id,
        Miembro.tenant_id == intento.tenant_id,
        Miembro.rol == "ADMINISTRADOR",
        Miembro.activo.is_(True),
    )) if cuenta is not None and cuenta.miembro_id is not None else None
    if miembro is None:
        raise HTTPException(403, "Administrador inválido")
    buzon = session.scalar(select(CorreoBuzon).where(
        CorreoBuzon.id == intento.buzon_id,
        CorreoBuzon.tenant_id == intento.tenant_id,
        CorreoBuzon.proveedor == "MICROSOFT",
    ))
    if buzon is None:
        raise HTTPException(404, "Buzón no encontrado")
    if not all((
        config.microsoft_oauth_client_id, config.microsoft_oauth_client_secret,
        config.correo_token_encryption_key, config.microsoft_oauth_redirect_uri,
    )):
        raise HTTPException(503, "Microsoft OAuth no configurado")
    intento.consumido_at = ahora
    session.commit()
    try:
        acceso, refresco, permisos = intercambiar_codigo_microsoft(
            code=code, verifier=intento.pkce_verifier,
            client_id=config.microsoft_oauth_client_id or "",
            client_secret=config.microsoft_oauth_client_secret,
            redirect_uri=redirect_uri,
        )
        comprobar_buzon_microsoft(access_token=acceso, direccion=buzon.direccion)
        cifrado = cifrar_refresh_token(refresco, config.correo_token_encryption_key or "")
    except (MicrosoftOAuthError, GoogleOAuthError) as exc:
        raise HTTPException(400, str(exc)) from exc
    credencial = session.scalar(select(CorreoOAuthCredencial).where(
        CorreoOAuthCredencial.buzon_id == buzon.id,
        CorreoOAuthCredencial.tenant_id == intento.tenant_id,
    ))
    if credencial is None:
        credencial = CorreoOAuthCredencial(
            tenant_id=intento.tenant_id, buzon_id=buzon.id,
            proveedor="MICROSOFT", token_cifrado=cifrado,
            permisos=permisos, verificado_at=ahora,
        )
        session.add(credencial)
    else:
        credencial.proveedor = "MICROSOFT"
        credencial.token_cifrado = cifrado
        credencial.permisos = permisos
        credencial.verificado_at = ahora
    buzon.activo = True
    buzon.ultimo_error = None
    session.commit()
    return RedirectResponse(url="/configuracion?seccion=correos&oauth=conectado", status_code=303)
