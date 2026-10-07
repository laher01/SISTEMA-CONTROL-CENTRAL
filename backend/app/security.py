import base64
import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CuentaAcceso, Gestor, Miembro, SesionAcceso


@dataclass(frozen=True)
class ContextoAcceso:
    cuenta_id: uuid.UUID
    tenant_id: uuid.UUID
    rol: str
    miembro_id: uuid.UUID | None
    gestor_id: uuid.UUID | None
    usuario_id: uuid.UUID | None
    codigo: str
    nombre: str
    cambio_clave_obligatorio: bool


def clave_temporal() -> str:
    return secrets.token_urlsafe(12)


def hash_clave(clave: str) -> str:
    salt = secrets.token_bytes(16)
    derivada = hashlib.scrypt(
        clave.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        dklen=32,
    )
    return "scrypt$16384$8$1$" + base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(derivada).decode()


def verificar_clave(clave: str, almacenada: str) -> bool:
    try:
        algoritmo, n, r, p, salt_b64, hash_b64 = almacenada.split("$", 5)
        if algoritmo != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        esperado = base64.urlsafe_b64decode(hash_b64.encode())
        derivada = hashlib.scrypt(
            clave.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(esperado),
        )
        return secrets.compare_digest(derivada, esperado)
    except (ValueError, TypeError):
        return False


def token_sesion() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode()).hexdigest()


def crear_sesion(
    session: Session,
    cuenta: CuentaAcceso,
    rol: str,
    horas: int = 12,
) -> tuple[SesionAcceso, str]:
    token, token_hash = token_sesion()
    ahora = datetime.now(UTC)
    sesion = SesionAcceso(
        tenant_id=cuenta.tenant_id,
        cuenta_id=cuenta.id,
        token_hash=token_hash,
        rol_activo=rol,
        expira_at=ahora + timedelta(hours=horas),
        ultima_actividad=ahora,
    )
    cuenta.ultimo_acceso = ahora
    session.add(sesion)
    session.flush()
    return sesion, token


def contexto_desde_token(session: Session, token: str) -> ContextoAcceso | None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    sesion = session.scalar(
        select(SesionAcceso).where(
            SesionAcceso.token_hash == token_hash,
            SesionAcceso.revocada_at.is_(None),
        )
    )
    if sesion is None:
        return None
    ahora = datetime.now(UTC)
    if sesion.expira_at <= ahora:
        sesion.revocada_at = ahora
        session.flush()
        return None

    cuenta = session.get(CuentaAcceso, sesion.cuenta_id)
    if cuenta is None or not cuenta.activo or cuenta.deleted_at is not None:
        return None

    sesion.ultima_actividad = ahora
    if cuenta.gestor_id is not None:
        gestor = session.get(Gestor, cuenta.gestor_id)
        if gestor is None or gestor.deleted_at is not None:
            return None
        return ContextoAcceso(
            cuenta_id=cuenta.id,
            tenant_id=cuenta.tenant_id,
            rol="GESTOR",
            miembro_id=None,
            gestor_id=gestor.id,
            usuario_id=gestor.usuario_id,
            codigo=gestor.codigo,
            nombre=gestor.nombre,
            cambio_clave_obligatorio=cuenta.cambio_clave_obligatorio,
        )

    if cuenta.miembro_id is not None:
        miembro = session.get(Miembro, cuenta.miembro_id)
        if miembro is None or miembro.deleted_at is not None or not miembro.activo:
            return None
        usuario_id = miembro.id if miembro.rol == "USUARIO" else None
        return ContextoAcceso(
            cuenta_id=cuenta.id,
            tenant_id=cuenta.tenant_id,
            rol=miembro.rol,
            miembro_id=miembro.id,
            gestor_id=None,
            usuario_id=usuario_id,
            codigo=miembro.codigo,
            nombre=miembro.nombre,
            cambio_clave_obligatorio=cuenta.cambio_clave_obligatorio,
        )
    return None


def revocar_sesion(session: Session, token: str) -> None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    sesion = session.scalar(select(SesionAcceso).where(SesionAcceso.token_hash == token_hash))
    if sesion is not None and sesion.revocada_at is None:
        sesion.revocada_at = datetime.now(UTC)
