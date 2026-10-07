from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select

from app.api.deps import AuthDep, SessionDep, SettingsDep
from app.models import CuentaAcceso, Gestor, Miembro, Tenant
from app.schemas import CambioClaveIn, LoginIn, SesionOut
from app.security import crear_sesion, hash_clave, revocar_sesion, verificar_clave
from app.services import auditoria

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=SesionOut)
def login(
    datos: LoginIn,
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
) -> SesionOut:
    tenant = session.scalar(select(Tenant).where(Tenant.nombre == settings.tenant_default))
    if tenant is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")

    cuenta = session.scalar(
        select(CuentaAcceso).where(
            CuentaAcceso.tenant_id == tenant.id,
            CuentaAcceso.login == datos.login.strip().upper(),
            CuentaAcceso.deleted_at.is_(None),
            CuentaAcceso.activo.is_(True),
        )
    )
    if cuenta is None or not verificar_clave(datos.clave, cuenta.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")

    rol = _rol_de_cuenta(session, cuenta)
    if rol is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "La cuenta no tiene un rol activo")

    sesion, token = crear_sesion(session, cuenta, rol, settings.session_hours)
    auditoria.registrar(
        session,
        cuenta.tenant_id,
        "SESION_INICIADA",
        "sesion",
        sesion.id,
        {"cuenta_id": str(cuenta.id), "rol": rol},
    )
    session.commit()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=settings.session_hours * 3600,
        path="/",
    )
    return _salida_sesion(session, cuenta, rol)


@router.get("/me", response_model=SesionOut)
def me(contexto: AuthDep) -> SesionOut:
    return SesionOut(
        rol=contexto.rol,
        codigo=contexto.codigo,
        nombre=contexto.nombre,
        miembro_id=contexto.miembro_id,
        gestor_id=contexto.gestor_id,
        usuario_id=contexto.usuario_id,
        cambio_clave_obligatorio=contexto.cambio_clave_obligatorio,
    )


@router.post("/cambiar-clave", response_model=SesionOut)
def cambiar_clave(
    datos: CambioClaveIn,
    contexto: AuthDep,
    session: SessionDep,
) -> SesionOut:
    cuenta = session.get(CuentaAcceso, contexto.cuenta_id)
    if cuenta is None or not verificar_clave(datos.clave_actual, cuenta.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La clave actual no es correcta")
    if datos.clave_actual == datos.clave_nueva:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La nueva clave debe ser diferente")
    if not _clave_valida(datos.clave_nueva):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "La nueva clave debe tener al menos 10 caracteres, una letra y un número",
        )
    cuenta.password_hash = hash_clave(datos.clave_nueva)
    cuenta.cambio_clave_obligatorio = False
    auditoria.registrar(
        session,
        cuenta.tenant_id,
        "CLAVE_CAMBIADA",
        "cuenta_acceso",
        cuenta.id,
        {"cambio_obligatorio": contexto.cambio_clave_obligatorio},
    )
    session.commit()
    return SesionOut(
        rol=contexto.rol,
        codigo=contexto.codigo,
        nombre=contexto.nombre,
        miembro_id=contexto.miembro_id,
        gestor_id=contexto.gestor_id,
        usuario_id=contexto.usuario_id,
        cambio_clave_obligatorio=False,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
) -> Response:
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        revocar_sesion(session, token)
        session.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


def _rol_de_cuenta(session: SessionDep, cuenta: CuentaAcceso) -> str | None:
    if cuenta.gestor_id is not None:
        gestor = session.get(Gestor, cuenta.gestor_id)
        if gestor is None or gestor.deleted_at is not None:
            return None
        return "GESTOR"
    if cuenta.miembro_id is not None:
        miembro = session.get(Miembro, cuenta.miembro_id)
        if miembro is None or miembro.deleted_at is not None or not miembro.activo:
            return None
        return miembro.rol
    return None


def _salida_sesion(session: SessionDep, cuenta: CuentaAcceso, rol: str) -> SesionOut:
    if cuenta.gestor_id is not None:
        gestor = session.get(Gestor, cuenta.gestor_id)
        if gestor is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Gestor no disponible")
        return SesionOut(
            rol=rol,
            codigo=gestor.codigo,
            nombre=gestor.nombre,
            miembro_id=None,
            gestor_id=gestor.id,
            usuario_id=gestor.usuario_id,
            cambio_clave_obligatorio=cuenta.cambio_clave_obligatorio,
        )
    miembro = session.get(Miembro, cuenta.miembro_id)
    if miembro is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Miembro no disponible")
    return SesionOut(
        rol=rol,
        codigo=miembro.codigo,
        nombre=miembro.nombre,
        miembro_id=miembro.id,
        gestor_id=None,
        usuario_id=miembro.id if miembro.rol == "USUARIO" else None,
        cambio_clave_obligatorio=cuenta.cambio_clave_obligatorio,
    )


def _clave_valida(clave: str) -> bool:
    return len(clave) >= 10 and any(c.isalpha() for c in clave) and any(c.isdigit() for c in clave)
