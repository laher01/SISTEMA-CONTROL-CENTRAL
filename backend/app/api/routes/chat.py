import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func, or_, select

from app.api.deps import AlmacenDep, OperativeAuthDep, SessionDep, TenantDep
from app.enums import RolMiembro
from app.models import ChatMensaje, CuentaAcceso, Gestor, Miembro
from app.services import auditoria

router = APIRouter(prefix="/chat", tags=["chat"])
ADMIN_ROLES = (RolMiembro.SUPERADMIN, RolMiembro.ADMINISTRADOR, RolMiembro.SECRETARIA)
FORMATOS = {".pdf", ".xml", ".jpg", ".jpeg", ".png", ".webp", ".txt"}
LIMITE_ARCHIVO = 5 * 1024 * 1024


class ContactoOut(BaseModel):
    cuenta_id: uuid.UUID
    nombre: str
    codigo: str
    rol: str


class MensajeOut(BaseModel):
    id: uuid.UUID
    remitente_cuenta_id: uuid.UUID
    destinatario_cuenta_id: uuid.UUID
    texto: str
    archivo_nombre: str | None
    archivo_tamano: int | None
    created_at: datetime


def _contacto(session: SessionDep, tenant_id: uuid.UUID, cuenta_id: uuid.UUID) -> CuentaAcceso:
    cuenta = session.get(CuentaAcceso, cuenta_id)
    if (
        cuenta is None
        or cuenta.tenant_id != tenant_id
        or not cuenta.activo
        or cuenta.deleted_at is not None
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contacto no disponible")
    return cuenta


def _rol_contacto(session: SessionDep, cuenta: CuentaAcceso) -> str:
    if cuenta.gestor_id is not None:
        return "GESTOR"
    if cuenta.miembro_id is not None:
        miembro = session.get(Miembro, cuenta.miembro_id)
        if miembro is not None:
            return miembro.rol
    return "SIN_ROL"


def _permitido(session: SessionDep, auth: OperativeAuthDep, cuenta: CuentaAcceso) -> bool:
    if cuenta.id == auth.cuenta_id:
        return False
    if auth.rol in ADMIN_ROLES:
        return True
    rol_destino = _rol_contacto(session, cuenta)
    if rol_destino in ADMIN_ROLES:
        return True
    if auth.rol == RolMiembro.USUARIO:
        if cuenta.gestor_id is None:
            return False
        gestor = session.get(Gestor, cuenta.gestor_id)
        return gestor is not None and gestor.usuario_id == auth.usuario_id
    if auth.rol == "GESTOR":
        return rol_destino == RolMiembro.USUARIO and cuenta.miembro_id == auth.usuario_id
    return False


def _validar_contacto(
    session: SessionDep,
    tenant_id: uuid.UUID,
    auth: OperativeAuthDep,
    destinatario_id: uuid.UUID,
) -> CuentaAcceso:
    cuenta = _contacto(session, tenant_id, destinatario_id)
    if not _permitido(session, auth, cuenta):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contacto no disponible")
    return cuenta


def _salida(item: ChatMensaje) -> MensajeOut:
    return MensajeOut(
        id=item.id,
        remitente_cuenta_id=item.remitente_cuenta_id,
        destinatario_cuenta_id=item.destinatario_cuenta_id,
        texto=item.texto,
        archivo_nombre=item.archivo_nombre,
        archivo_tamano=item.archivo_tamano,
        created_at=item.created_at,
    )


@router.get("/contactos", response_model=list[ContactoOut])
def listar_contactos(
    session: SessionDep, tenant_id: TenantDep, auth: OperativeAuthDep
) -> list[ContactoOut]:
    cuentas = session.scalars(
        select(CuentaAcceso)
        .where(
            CuentaAcceso.tenant_id == tenant_id,
            CuentaAcceso.activo.is_(True),
            CuentaAcceso.deleted_at.is_(None),
        )
        .order_by(CuentaAcceso.login)
        .limit(500)
    )
    resultado: list[ContactoOut] = []
    for cuenta in cuentas:
        if not _permitido(session, auth, cuenta):
            continue
        nombre = cuenta.login
        if cuenta.gestor_id is not None:
            gestor = session.get(Gestor, cuenta.gestor_id)
            if gestor is not None:
                nombre = gestor.nombre
        elif cuenta.miembro_id is not None:
            miembro = session.get(Miembro, cuenta.miembro_id)
            if miembro is not None:
                nombre = miembro.nombre
        resultado.append(
            ContactoOut(
                cuenta_id=cuenta.id,
                nombre=nombre,
                codigo=cuenta.login,
                rol=_rol_contacto(session, cuenta),
            )
        )
    return resultado


@router.get("/mensajes", response_model=list[MensajeOut])
def listar_mensajes(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    con: uuid.UUID,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[MensajeOut]:
    _validar_contacto(session, tenant_id, auth, con)
    mensajes = session.scalars(
        select(ChatMensaje)
        .where(
            ChatMensaje.tenant_id == tenant_id,
            ChatMensaje.deleted_at.is_(None),
            or_(
                (
                    (ChatMensaje.remitente_cuenta_id == auth.cuenta_id)
                    & (ChatMensaje.destinatario_cuenta_id == con)
                ),
                (
                    (ChatMensaje.remitente_cuenta_id == con)
                    & (ChatMensaje.destinatario_cuenta_id == auth.cuenta_id)
                ),
            ),
        )
        .order_by(ChatMensaje.created_at.desc(), ChatMensaje.id.desc())
        .limit(limit)
    )
    return [_salida(item) for item in reversed(list(mensajes))]


@router.post("/mensajes", response_model=MensajeOut, status_code=status.HTTP_201_CREATED)
async def enviar_mensaje(
    session: SessionDep,
    almacen: AlmacenDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    destinatario_cuenta_id: Annotated[uuid.UUID, Form()],
    texto: Annotated[str, Form(max_length=2000)] = "",
    archivo: Annotated[UploadFile | None, File()] = None,
) -> MensajeOut:
    _validar_contacto(session, tenant_id, auth, destinatario_cuenta_id)
    texto_limpio = texto.strip()
    if not texto_limpio and archivo is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Mensaje vacío")
    recientes = session.scalar(
        select(func.count(ChatMensaje.id)).where(
            ChatMensaje.tenant_id == tenant_id,
            ChatMensaje.remitente_cuenta_id == auth.cuenta_id,
            ChatMensaje.created_at >= datetime.now(UTC) - timedelta(minutes=1),
        )
    )
    if (recientes or 0) >= 30:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Demasiados mensajes")
    datos_archivo: dict[str, str | int] = {}
    if archivo is not None:
        extension = Path(archivo.filename or "").suffix.lower()
        if extension not in FORMATOS:
            raise HTTPException(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Tipo de archivo no permitido"
            )
        contenido = await archivo.read(LIMITE_ARCHIVO + 1)
        if not contenido or len(contenido) > LIMITE_ARCHIVO:
            raise HTTPException(
                status.HTTP_413_CONTENT_TOO_LARGE, "Archivo vacío o demasiado grande"
            )
        if extension == ".pdf" and not contenido.startswith(b"%PDF-"):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "PDF inválido")
        if extension == ".png" and not contenido.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "PNG inválido")
        if extension in {".jpg", ".jpeg"} and not contenido.startswith(b"\xff\xd8"):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "JPEG inválido")
        sha = hashlib.sha256(contenido).hexdigest()
        datos_archivo = {
            "archivo_nombre": Path(archivo.filename or "archivo").name[:255],
            "archivo_mime": "application/octet-stream",
            "archivo_sha256": sha,
            "archivo_ruta": almacen.guardar(tenant_id, sha, contenido),
            "archivo_tamano": len(contenido),
        }
    mensaje = ChatMensaje(
        tenant_id=tenant_id,
        remitente_cuenta_id=auth.cuenta_id,
        destinatario_cuenta_id=destinatario_cuenta_id,
        texto=texto_limpio,
        **datos_archivo,
    )
    session.add(mensaje)
    session.flush()
    auditoria.registrar(
        session,
        tenant_id,
        "CHAT_MENSAJE_ENVIADO",
        "chat_mensaje",
        mensaje.id,
        {
            "remitente": str(auth.cuenta_id),
            "destinatario": str(destinatario_cuenta_id),
            "adjunto": bool(archivo),
        },
    )
    session.commit()
    return _salida(mensaje)


@router.get("/mensajes/{mensaje_id}/archivo")
def descargar_adjunto(
    session: SessionDep,
    almacen: AlmacenDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    mensaje_id: uuid.UUID,
) -> FileResponse:
    mensaje = session.get(ChatMensaje, mensaje_id)
    if (
        mensaje is None
        or mensaje.tenant_id != tenant_id
        or mensaje.deleted_at is not None
        or mensaje.archivo_ruta is None
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Adjunto no encontrado")
    if auth.cuenta_id not in (mensaje.remitente_cuenta_id, mensaje.destinatario_cuenta_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Adjunto no encontrado")
    otro = (
        mensaje.destinatario_cuenta_id
        if mensaje.remitente_cuenta_id == auth.cuenta_id
        else mensaje.remitente_cuenta_id
    )
    _validar_contacto(session, tenant_id, auth, otro)
    return FileResponse(
        almacen.ruta_absoluta(mensaje.archivo_ruta),
        media_type="application/octet-stream",
        filename=mensaje.archivo_nombre or "archivo",
        headers={"X-Content-Type-Options": "nosniff"},
    )
