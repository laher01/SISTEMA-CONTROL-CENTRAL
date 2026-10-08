import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import OperativeAuthDep, SessionDep, TenantDep
from app.enums import RolMiembro
from app.models import (
    ConfiguracionAcceso,
    CorreoAutorizado,
    CuentaAcceso,
    Miembro,
    SesionAcceso,
    SolicitudAcceso,
)
from app.schemas import (
    ConfiguracionAccesoIn,
    ConfiguracionAccesoOut,
    CorreoAutorizadoIn,
    CorreoAutorizadoOut,
    CredencialTemporalOut,
    CuentaAccesoAdminActualizar,
    CuentaAccesoAdminOut,
    SesionAccesoAdminOut,
    SolicitudAccesoOut,
    SolicitudAccesoResolverIn,
)
from app.security import crear_o_restablecer_cuenta

router = APIRouter(prefix="/configuracion/acceso", tags=["configuracion-acceso"])


def _solo_superadmin(rol: str) -> None:
    if rol != RolMiembro.SUPERADMIN:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo SUPERADMIN puede administrar la configuración de acceso",
        )


def _configuracion(session: SessionDep, tenant_id: uuid.UUID) -> ConfiguracionAcceso:
    config = session.scalar(
        select(ConfiguracionAcceso).where(ConfiguracionAcceso.tenant_id == tenant_id)
    )
    if config is None:
        config = ConfiguracionAcceso(tenant_id=tenant_id)
        session.add(config)
        session.flush()
    return config


@router.get("", response_model=ConfiguracionAccesoOut)
def obtener(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> ConfiguracionAcceso:
    _solo_superadmin(auth.rol)
    config = _configuracion(session, tenant_id)
    session.commit()
    return config


@router.put("", response_model=ConfiguracionAccesoOut)
def actualizar(
    datos: ConfiguracionAccesoIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> ConfiguracionAcceso:
    _solo_superadmin(auth.rol)
    config_actual = _configuracion(session, tenant_id)
    if datos.requiere_email_verificado and not config_actual.proveedor_email_configurado:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No puede exigir correo verificado hasta configurar un proveedor de email",
        )
    if not datos.requiere_aprobacion and (
        not config_actual.proveedor_email_configurado or not datos.requiere_email_verificado
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No puede desactivar la aprobación sin proveedor de email y correo verificado",
        )
    config = config_actual
    config.registro_publico = datos.registro_publico
    config.requiere_aprobacion = datos.requiere_aprobacion
    config.solo_correos_autorizados = datos.solo_correos_autorizados
    config.requiere_email_verificado = datos.requiere_email_verificado
    config.acceso_cloudflare_activo = datos.acceso_cloudflare_activo
    config.duracion_sesion_horas = datos.duracion_sesion_horas
    config.intentos_fallidos_max = datos.intentos_fallidos_max
    config.bloqueo_minutos = datos.bloqueo_minutos
    config.clave_min_longitud = datos.clave_min_longitud
    config.clave_requiere_letra = datos.clave_requiere_letra
    config.clave_requiere_numero = datos.clave_requiere_numero
    session.commit()
    return config


@router.get("/correos", response_model=list[CorreoAutorizadoOut])
def listar_correos(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[CorreoAutorizado]:
    _solo_superadmin(auth.rol)
    return list(
        session.scalars(
            select(CorreoAutorizado)
            .where(
                CorreoAutorizado.tenant_id == tenant_id,
                CorreoAutorizado.activo.is_(True),
            )
            .order_by(CorreoAutorizado.email)
        )
    )


@router.post("/correos", response_model=CorreoAutorizadoOut, status_code=status.HTTP_201_CREATED)
def autorizar_correo(
    datos: CorreoAutorizadoIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> CorreoAutorizado:
    _solo_superadmin(auth.rol)
    email = datos.email.strip().lower()
    if "@" not in email:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Correo inválido")
    if datos.rol_sugerido == RolMiembro.SUPERADMIN:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "SUPERADMIN no puede asignarse mediante invitación o solicitud pública",
        )
    registro = CorreoAutorizado(
        tenant_id=tenant_id,
        email=email,
        rol_sugerido=datos.rol_sugerido,
        activo=True,
    )
    session.add(registro)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está autorizado") from exc
    return registro


@router.delete("/correos/{correo_id}", status_code=status.HTTP_204_NO_CONTENT)
def revocar_correo(
    correo_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> None:
    _solo_superadmin(auth.rol)
    registro = session.get(CorreoAutorizado, correo_id)
    if registro is None or registro.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Correo no encontrado")
    registro.activo = False
    session.commit()


@router.get("/solicitudes", response_model=list[SolicitudAccesoOut])
def listar_solicitudes(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[SolicitudAcceso]:
    _solo_superadmin(auth.rol)
    return list(
        session.scalars(
            select(SolicitudAcceso)
            .where(SolicitudAcceso.tenant_id == tenant_id)
            .order_by(SolicitudAcceso.created_at.desc())
        )
    )


@router.post("/solicitudes/{solicitud_id}/resolver")
def resolver_solicitud(
    solicitud_id: uuid.UUID,
    datos: SolicitudAccesoResolverIn,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> dict[str, object]:
    _solo_superadmin(auth.rol)
    solicitud = session.get(SolicitudAcceso, solicitud_id)
    if solicitud is None or solicitud.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitud no encontrada")
    if solicitud.estado != "PENDIENTE":
        raise HTTPException(status.HTTP_409_CONFLICT, "La solicitud ya fue resuelta")

    if not datos.aprobar:
        solicitud.estado = "RECHAZADA"
        solicitud.resuelta_at = datetime.now(UTC)
        session.commit()
        return {"estado": solicitud.estado}

    rol = datos.rol
    if rol is None:
        correo = session.scalar(
            select(CorreoAutorizado).where(
                CorreoAutorizado.tenant_id == tenant_id,
                CorreoAutorizado.email == solicitud.email,
                CorreoAutorizado.activo.is_(True),
            )
        )
        rol = RolMiembro(correo.rol_sugerido) if correo and correo.rol_sugerido else None
    if rol is None or rol == RolMiembro.SUPERADMIN:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Debe asignar un rol válido distinto de SUPERADMIN",
        )
    miembro = Miembro(
        tenant_id=tenant_id,
        codigo=solicitud.codigo_solicitado.strip().upper(),
        nombre=solicitud.nombre.strip(),
        rol=rol,
        creado_por_cuenta_id=auth.cuenta_id,
        activo=True,
    )
    session.add(miembro)
    try:
        session.flush()
        cuenta, temporal = crear_o_restablecer_cuenta(
            session,
            tenant_id,
            miembro.codigo,
            miembro_id=miembro.id,
        )
        cuenta.email = solicitud.email.strip().lower()
        solicitud.estado = "APROBADA"
        solicitud.rol_asignado = rol
        solicitud.resuelta_at = datetime.now(UTC)
        session.commit()
    except (IntegrityError, ValueError) as exc:
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No se pudo crear la cuenta; revise código o correo duplicado",
        ) from exc

    return {
        "estado": solicitud.estado,
        "login": miembro.codigo,
        "email": cuenta.email,
        "clave_temporal": temporal,
    }


@router.get("/cuentas", response_model=list[CuentaAccesoAdminOut])
def listar_cuentas(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[CuentaAcceso]:
    _solo_superadmin(auth.rol)
    return list(
        session.scalars(
            select(CuentaAcceso)
            .where(
                CuentaAcceso.tenant_id == tenant_id,
                CuentaAcceso.deleted_at.is_(None),
            )
            .order_by(CuentaAcceso.login)
        )
    )


@router.patch("/cuentas/{cuenta_id}", response_model=CuentaAccesoAdminOut)
def actualizar_cuenta(
    cuenta_id: uuid.UUID,
    datos: CuentaAccesoAdminActualizar,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> CuentaAcceso:
    _solo_superadmin(auth.rol)
    cuenta = session.get(CuentaAcceso, cuenta_id)
    if cuenta is None or cuenta.tenant_id != tenant_id or cuenta.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cuenta no encontrada")
    if datos.activo is False and cuenta.id == auth.cuenta_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "SUPERADMIN no puede desactivar su propia cuenta",
        )
    if datos.activo is not None:
        cuenta.activo = datos.activo
    if datos.email_verificado is not None:
        cuenta.email_verificado = datos.email_verificado
    if datos.activo is True:
        cuenta.intentos_fallidos = 0
        cuenta.bloqueado_hasta = None
    session.commit()
    return cuenta


@router.post(
    "/cuentas/{cuenta_id}/restablecer-clave",
    response_model=CredencialTemporalOut,
)
def restablecer_clave(
    cuenta_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> CredencialTemporalOut:
    _solo_superadmin(auth.rol)
    cuenta = session.get(CuentaAcceso, cuenta_id)
    if cuenta is None or cuenta.tenant_id != tenant_id or cuenta.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cuenta no encontrada")
    _, temporal = crear_o_restablecer_cuenta(
        session,
        tenant_id,
        cuenta.login,
        miembro_id=cuenta.miembro_id,
        gestor_id=cuenta.gestor_id,
    )
    cuenta.intentos_fallidos = 0
    cuenta.bloqueado_hasta = None
    session.commit()
    return CredencialTemporalOut(login=cuenta.login, clave_temporal=temporal)


@router.get("/sesiones", response_model=list[SesionAccesoAdminOut])
def listar_sesiones(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> list[SesionAccesoAdminOut]:
    _solo_superadmin(auth.rol)
    filas = session.execute(
        select(SesionAcceso, CuentaAcceso.login)
        .join(CuentaAcceso, CuentaAcceso.id == SesionAcceso.cuenta_id)
        .where(SesionAcceso.tenant_id == tenant_id)
        .order_by(SesionAcceso.ultima_actividad.desc())
        .limit(200)
    ).all()
    return [
        SesionAccesoAdminOut(
            id=sesion.id,
            cuenta_id=sesion.cuenta_id,
            login=login,
            rol_activo=sesion.rol_activo,
            expira_at=sesion.expira_at,
            ultima_actividad=sesion.ultima_actividad,
            revocada_at=sesion.revocada_at,
        )
        for sesion, login in filas
    ]


@router.delete("/sesiones/{sesion_id}", status_code=status.HTTP_204_NO_CONTENT)
def revocar_sesion_admin(
    sesion_id: uuid.UUID,
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
) -> None:
    _solo_superadmin(auth.rol)
    sesion = session.get(SesionAcceso, sesion_id)
    if sesion is None or sesion.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sesión no encontrada")
    if sesion.revocada_at is None:
        sesion.revocada_at = datetime.now(UTC)
    session.commit()
