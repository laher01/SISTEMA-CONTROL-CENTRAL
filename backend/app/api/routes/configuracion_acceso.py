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
    SolicitudAcceso,
)
from app.schemas import (
    ConfiguracionAccesoIn,
    ConfiguracionAccesoOut,
    CorreoAutorizadoIn,
    CorreoAutorizadoOut,
    CredencialTemporalOut,
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
    if datos.requiere_email_verificado:
        config_actual = _configuracion(session, tenant_id)
        if not config_actual.proveedor_email_configurado:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "No puede exigir correo verificado hasta configurar un proveedor de email",
            )
    config = _configuracion(session, tenant_id)
    config.registro_publico = datos.registro_publico
    config.requiere_aprobacion = datos.requiere_aprobacion
    config.solo_correos_autorizados = datos.solo_correos_autorizados
    config.requiere_email_verificado = datos.requiere_email_verificado
    config.acceso_cloudflare_activo = datos.acceso_cloudflare_activo
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
