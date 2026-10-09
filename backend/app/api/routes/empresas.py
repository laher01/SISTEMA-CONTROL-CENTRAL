import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import exists, or_, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import HoyDep, OperativeAuthDep, SessionDep, SettingsDep, TenantDep
from app.api.errores import no_encontrado
from app.enums import RolMiembro
from app.models import ChatMensaje, CuentaAcceso, Empresa, Expediente, Miembro, ahora
from app.schemas import (
    EmpresaActualizar,
    EmpresaListadoOut,
    EmpresaOut,
    EmpresasEliminarIn,
    EmpresasEliminarOut,
    EmpresaUsuarioOut,
)
from app.services import auditoria
from app.services.expedientes import recalcular_expedientes

router = APIRouter(prefix="/empresas", tags=["empresas"])


@router.get("", response_model=list[EmpresaListadoOut])
def listar(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    autorizada: bool | None = None,
    sin_clasificar: bool = False,
    ruc: str | None = None,
) -> list[EmpresaListadoOut]:
    consulta = select(Empresa).where(Empresa.tenant_id == tenant_id, Empresa.deleted_at.is_(None))
    if auth.rol == "GESTOR":
        consulta = consulta.where(
            exists().where(
                Expediente.tenant_id == tenant_id,
                Expediente.deleted_at.is_(None),
                Expediente.gestor_id == auth.gestor_id,
                or_(Expediente.emisor_id == Empresa.id, Expediente.receptor_id == Empresa.id),
            )
        )
    elif auth.rol == RolMiembro.USUARIO:
        consulta = consulta.where(
            exists().where(
                Expediente.tenant_id == tenant_id,
                Expediente.deleted_at.is_(None),
                Expediente.usuario_id == auth.usuario_id,
                or_(Expediente.emisor_id == Empresa.id, Expediente.receptor_id == Empresa.id),
            )
        )
    if autorizada is not None:
        consulta = consulta.where(Empresa.autorizada == autorizada)
    if sin_clasificar:
        consulta = consulta.where(
            or_(
                Empresa.tipo_relacion == "SIN_CLASIFICAR",
                (Empresa.tipo_relacion.in_(["PROVEEDOR", "AMBOS"]))
                & (Empresa.clasificacion_proveedor.is_(None)),
            )
        )
    if ruc:
        consulta = consulta.where(Empresa.ruc == ruc)

    empresas = list(session.scalars(consulta.order_by(Empresa.razon_social)))
    salida: list[EmpresaListadoOut] = []
    for empresa in empresas:
        usuarios_q = (
            select(Miembro)
            .join(Expediente, Expediente.usuario_id == Miembro.id)
            .where(
                Expediente.tenant_id == tenant_id,
                Expediente.deleted_at.is_(None),
                Miembro.deleted_at.is_(None),
                or_(
                    Expediente.emisor_id == empresa.id,
                    Expediente.receptor_id == empresa.id,
                ),
            )
            .distinct()
            .order_by(Miembro.codigo)
        )
        if auth.rol == "GESTOR":
            usuarios_q = usuarios_q.where(Expediente.gestor_id == auth.gestor_id)
        elif auth.rol == RolMiembro.USUARIO:
            usuarios_q = usuarios_q.where(Expediente.usuario_id == auth.usuario_id)

        usuarios = [
            EmpresaUsuarioOut(id=u.id, codigo=u.codigo, nombre=u.nombre)
            for u in session.scalars(usuarios_q)
        ]
        salida.append(
            EmpresaListadoOut(
                **EmpresaOut.model_validate(empresa).model_dump(),
                usuarios=usuarios,
            )
        )
    return salida


class SolicitudClasificacionIn(BaseModel):
    empresa_ids: list[uuid.UUID] = Field(min_length=1, max_length=50)


@router.post("/notificar-clasificacion")
def notificar_clasificacion(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    datos: SolicitudClasificacionIn,
) -> dict[str, int]:
    """Solicita revisión al administrador, sin conceder autorización."""
    if auth.rol not in (
        RolMiembro.SUPERADMIN, RolMiembro.ADMINISTRADOR,
        RolMiembro.SECRETARIA, RolMiembro.USUARIO, "GESTOR",
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin permiso para solicitar clasificación")
    empresas = list(
        session.scalars(
            select(Empresa).where(
                Empresa.tenant_id == tenant_id,
                Empresa.deleted_at.is_(None),
                Empresa.id.in_(datos.empresa_ids),
                or_(
                    Empresa.tipo_relacion == "SIN_CLASIFICAR",
                    (Empresa.tipo_relacion.in_(["PROVEEDOR", "AMBOS"]))
                    & (Empresa.clasificacion_proveedor.is_(None)),
                ),
            )
        )
    )
    if not empresas:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "No hay empresas pendientes")
    if auth.rol in (RolMiembro.USUARIO, "GESTOR"):
        filtro = (
            Expediente.usuario_id == auth.usuario_id
            if auth.rol == RolMiembro.USUARIO
            else Expediente.gestor_id == auth.gestor_id
        )
        permitidas = set(
            session.scalars(
                select(Empresa.id).where(
                    Empresa.id.in_([e.id for e in empresas]),
                    exists().where(
                        Expediente.tenant_id == tenant_id,
                        Expediente.deleted_at.is_(None),
                        filtro,
                        or_(
                            Expediente.emisor_id == Empresa.id,
                            Expediente.receptor_id == Empresa.id,
                        ),
                    ),
                )
            )
        )
        if any(e.id not in permitidas for e in empresas):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Empresa fuera de su ámbito")
    destinatarios = list(
        session.scalars(
            select(CuentaAcceso)
            .join(Miembro, CuentaAcceso.miembro_id == Miembro.id)
            .where(
                CuentaAcceso.tenant_id == tenant_id,
                CuentaAcceso.activo.is_(True),
                CuentaAcceso.deleted_at.is_(None),
                Miembro.rol.in_([RolMiembro.SUPERADMIN, RolMiembro.ADMINISTRADOR]),
                Miembro.activo.is_(True),
                Miembro.deleted_at.is_(None),
                CuentaAcceso.id != auth.cuenta_id,
            )
        )
    )
    if not destinatarios:
        raise HTTPException(status.HTTP_409_CONFLICT, "Sin administrador destinatario")
    detalles = ", ".join(f"{e.ruc} ({e.razon_social})" for e in empresas)
    for destinatario in destinatarios:
        session.add(
            ChatMensaje(
                tenant_id=tenant_id,
                remitente_cuenta_id=auth.cuenta_id,
                destinatario_cuenta_id=destinatario.id,
                texto=(
                    f"Solicitud de autorización y clasificación de empresas "
                    f"por {auth.codigo}: {detalles}"
                )[:2000],
            )
        )
    auditoria.registrar(
        session, tenant_id, "CLASIFICACION_SOLICITADA", "empresa", empresas[0].id,
        {"empresa_ids": [str(e.id) for e in empresas], "actor": auth.codigo},
    )
    session.commit()
    return {"empresas": len(empresas), "administradores": len(destinatarios)}


@router.patch("/{empresa_id}", response_model=EmpresaOut)
def actualizar(
    session: SessionDep,
    settings: SettingsDep,
    hoy: HoyDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    empresa_id: uuid.UUID,
    datos: EmpresaActualizar,
) -> Empresa:
    if auth.rol not in (RolMiembro.SUPERADMIN, RolMiembro.ADMINISTRADOR, RolMiembro.SECRETARIA):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene permiso para modificar Empresas")
    empresa = session.get(Empresa, empresa_id)
    if empresa is None or empresa.tenant_id != tenant_id or empresa.deleted_at:
        raise no_encontrado("Empresa")
    anterior = {
        "ruc": empresa.ruc,
        "razon_social": empresa.razon_social,
        "tipo_relacion": empresa.tipo_relacion,
        "clasificacion_proveedor": empresa.clasificacion_proveedor,
        "autorizada": empresa.autorizada,
        "agente_retencion": empresa.agente_retencion,
    }

    if datos.ruc is not None:
        nuevo_ruc = datos.ruc.strip()
        if nuevo_ruc != empresa.ruc:
            duplicada = session.scalar(
                select(Empresa).where(
                    Empresa.tenant_id == tenant_id,
                    Empresa.ruc == nuevo_ruc,
                    Empresa.id != empresa.id,
                )
            )
            if duplicada is not None:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "Ya existe una empresa registrada con ese RUC",
                )
        empresa.ruc = nuevo_ruc
    if datos.razon_social is not None:
        empresa.razon_social = datos.razon_social.strip()
    if datos.tipo_relacion is not None:
        empresa.tipo_relacion = datos.tipo_relacion
    if "clasificacion_proveedor" in datos.model_fields_set:
        empresa.clasificacion_proveedor = datos.clasificacion_proveedor

    if empresa.tipo_relacion in {"CLIENTE", "SIN_CLASIFICAR"}:
        empresa.clasificacion_proveedor = None

    if datos.autorizada is not None:
        empresa.autorizada = datos.autorizada
    if datos.agente_retencion is not None:
        empresa.agente_retencion = datos.agente_retencion

    cambios: dict[str, object] = datos.model_dump(exclude_unset=True, exclude_none=True)
    auditoria.registrar(
        session,
        tenant_id,
        "EMPRESA_ACTUALIZADA",
        "empresa",
        empresa.id,
        {"anterior": anterior, "nuevo": cambios, "actor": auth.codigo},
    )
    recalcular_expedientes(session, tenant_id, hoy, settings, receptor_id=empresa.id)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Ya existe una empresa registrada con ese RUC",
        ) from exc
    return empresa


@router.post("/eliminar-seleccion", response_model=EmpresasEliminarOut)
def eliminar_seleccion(
    session: SessionDep,
    tenant_id: TenantDep,
    auth: OperativeAuthDep,
    datos: EmpresasEliminarIn,
) -> EmpresasEliminarOut:
    if auth.rol != RolMiembro.SUPERADMIN:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo SUPERADMIN puede eliminar empresas registradas",
        )

    empresas = list(
        session.scalars(
            select(Empresa).where(
                Empresa.tenant_id == tenant_id,
                Empresa.id.in_(datos.empresa_ids),
                Empresa.deleted_at.is_(None),
            )
        )
    )
    momento = ahora()
    for empresa in empresas:
        empresa.deleted_at = momento
        auditoria.registrar(
            session,
            tenant_id,
            "EMPRESA_ELIMINADA_MANUALMENTE",
            "empresa",
            empresa.id,
            {
                "ruc": empresa.ruc,
                "razon_social": empresa.razon_social,
                "actor": auth.codigo,
            },
        )
    session.commit()
    return EmpresasEliminarOut(eliminadas=len(empresas))
