import uuid
from decimal import InvalidOperation
from typing import Literal

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy import exists, or_, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import HoyDep, OperativeAuthDep, SessionDep, SettingsDep, TenantDep
from app.api.errores import no_encontrado
from app.enums import RolMiembro
from app.models import (
    ChatMensaje,
    ConfiguracionConsultasEmpresa,
    CuentaAcceso,
    Empresa,
    Expediente,
    GerenteEmpresa,
    Miembro,
    Tenant,
    ahora,
)
from app.schemas import (
    EmpresaActualizar,
    EmpresaListadoOut,
    EmpresaOut,
    EmpresasEliminarIn,
    EmpresasEliminarOut,
    EmpresaUsuarioOut,
)
from app.services import auditoria, consultas_empresas
from app.services.ambito_gerencia import alcance_expedientes_gerente
from app.services.expedientes import expediente_tiene_documentos_activos, recalcular_expedientes

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
                expediente_tiene_documentos_activos(),
                Expediente.gestor_id == auth.gestor_id,
                or_(Expediente.emisor_id == Empresa.id, Expediente.receptor_id == Empresa.id),
            )
        )
    elif auth.rol == RolMiembro.GERENTE:
        consulta = consulta.where(
            or_(
                exists().where(
                    GerenteEmpresa.tenant_id == tenant_id,
                    GerenteEmpresa.gerente_id == auth.miembro_id,
                    GerenteEmpresa.empresa_id == Empresa.id,
                    GerenteEmpresa.activo.is_(True),
                ),
                exists().where(
                    Expediente.tenant_id == tenant_id,
                    alcance_expedientes_gerente(auth),
                    Expediente.deleted_at.is_(None),
                    expediente_tiene_documentos_activos(),
                    or_(Expediente.emisor_id == Empresa.id, Expediente.receptor_id == Empresa.id),
                ),
            )
        )
    elif auth.rol == RolMiembro.USUARIO:
        consulta = consulta.where(
            exists().where(
                Expediente.tenant_id == tenant_id,
                Expediente.deleted_at.is_(None),
                expediente_tiene_documentos_activos(),
                Expediente.usuario_id == auth.usuario_id,
                or_(Expediente.emisor_id == Empresa.id, Expediente.receptor_id == Empresa.id),
            )
        )
    elif auth.rol == RolMiembro.RESPONSABLE:
        subordinados = select(Miembro.id).where(
            Miembro.tenant_id == tenant_id,
            Miembro.responsable_id == auth.miembro_id,
            Miembro.rol == RolMiembro.USUARIO,
            Miembro.deleted_at.is_(None),
        )
        consulta = consulta.where(
            exists().where(
                Expediente.tenant_id == tenant_id,
                Expediente.deleted_at.is_(None),
                expediente_tiene_documentos_activos(),
                Expediente.usuario_id.in_(subordinados),
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
                expediente_tiene_documentos_activos(),
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
        elif auth.rol == RolMiembro.GERENTE:
            usuarios_q = usuarios_q.where(alcance_expedientes_gerente(auth))
        elif auth.rol == RolMiembro.USUARIO:
            usuarios_q = usuarios_q.where(Expediente.usuario_id == auth.usuario_id)
        elif auth.rol == RolMiembro.RESPONSABLE:
            usuarios_q = usuarios_q.where(Miembro.responsable_id == auth.miembro_id)

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


class ConfigConsultasIn(BaseModel):
    api_token: SecretStr | None = None
    endpoints: dict[str, str]


def _admin_consultas(rol: str) -> None:
    if rol != "ADMINISTRADOR":
        raise HTTPException(403, "Solo Administración puede configurar APIPERU")


def _estado_config_consultas(
    config: ConfiguracionConsultasEmpresa | None, token_servidor: str | None
) -> dict[str, object]:
    return {
        "token_configurado": bool((config and config.token_cifrado) or token_servidor),
        "endpoints": config.endpoints if config else consultas_empresas.ENDPOINTS,
        "permitidos": consultas_empresas.PERMITIDOS,
    }


@router.get("/consultas/configuracion")
def configuracion_consultas(
    auth: OperativeAuthDep,
    session: SessionDep,
    tenant_id: TenantDep,
    settings: SettingsDep,
) -> dict[str, object]:
    _admin_consultas(auth.rol)
    config = session.get(ConfiguracionConsultasEmpresa, tenant_id)
    return _estado_config_consultas(config, settings.consulta_coactiva_token)


@router.patch("/consultas/configuracion")
def actualizar_configuracion_consultas(
    datos: ConfigConsultasIn,
    auth: OperativeAuthDep,
    session: SessionDep,
    tenant_id: TenantDep,
    settings: SettingsDep,
) -> dict[str, object]:
    _admin_consultas(auth.rol)
    if datos.endpoints.keys() != consultas_empresas.PERMITIDOS.keys() or any(
        url not in consultas_empresas.PERMITIDOS[tipo] for tipo, url in datos.endpoints.items()
    ):
        raise HTTPException(422, "Seleccione únicamente endpoints autorizados de APIPERU")
    cifrado = None
    if datos.api_token is not None:
        token = datos.api_token.get_secret_value().strip()
        if (
            not 8 <= len(token) <= 512
            or not token.isascii()
            or not token.isprintable()
            or " " in token
        ):
            raise HTTPException(422, "Formato de token inválido")
        try:
            cifrado = (
                Fernet(settings.consultas_empresas_encryption_key or "")
                .encrypt(token.encode())
                .decode()
            )
        except ValueError:
            raise HTTPException(503, "Cifrado de credenciales sin configurar") from None
    session.scalar(select(Tenant.id).where(Tenant.id == tenant_id).with_for_update())
    config = session.get(ConfiguracionConsultasEmpresa, tenant_id)
    if config is None:
        config = ConfiguracionConsultasEmpresa(tenant_id=tenant_id)
        session.add(config)
    config.endpoints = datos.endpoints
    if cifrado is not None:
        config.token_cifrado = cifrado
    auditoria.registrar(
        session,
        tenant_id,
        "CONFIGURACION_APIPERU_ACTUALIZADA",
        "configuracion_consultas_empresa",
        tenant_id,
        {"actor": auth.codigo, "token_reemplazado": cifrado is not None},
    )
    session.commit()
    return _estado_config_consultas(config, settings.consulta_coactiva_token)


@router.get("/consultas/{tipo}/{ruc}")
def consultar_empresa(
    tipo: Literal["coactiva", "ssco", "domicilio", "sunat"],
    ruc: str,
    auth: OperativeAuthDep,
    settings: SettingsDep,
    session: SessionDep,
    tenant_id: TenantDep,
    buscar_razon: bool = False,
    ssco_apiperu: bool = False,
) -> dict[str, object]:
    if auth.rol not in {
        "ADMINISTRADOR",
        "GERENTE",
        "SECRETARIA",
        "RESPONSABLE",
        "USUARIO",
        "GESTOR",
    }:
        raise HTTPException(403, "Rol sin acceso a consultas de empresas")
    if len(ruc) != 11 or not ruc.isascii() or not ruc.isdigit():
        raise HTTPException(422, "El RUC debe tener 11 dígitos")
    config = session.get(ConfiguracionConsultasEmpresa, tenant_id)
    token = settings.consulta_coactiva_token
    endpoint = config.endpoints.get(tipo) if config else None
    if endpoint not in consultas_empresas.PERMITIDOS[tipo]:
        endpoint = consultas_empresas.ENDPOINTS[tipo]
    if config and config.token_cifrado:
        try:
            token = (
                Fernet(settings.consultas_empresas_encryption_key or "")
                .decrypt(config.token_cifrado.encode())
                .decode()
            )
        except (ValueError, InvalidToken):
            token = None
    try:
        if tipo == "ssco":
            try:
                resultado = (
                    consultas_empresas.consultar_ssco_apiperu(ruc, token, endpoint)
                    if ssco_apiperu and token
                    else consultas_empresas.consultar_ssco(ruc)
                )
            except (httpx.HTTPError, ValueError):
                if not ssco_apiperu or not token:
                    raise
                resultado = consultas_empresas.consultar_ssco(ruc)
        elif token and tipo == "coactiva":
            resultado = consultas_empresas.consultar_coactiva(ruc, token, endpoint)
        elif token:
            resultado = consultas_empresas.consultar_ficha(ruc, token, tipo, endpoint)
        else:
            raise ValueError("Servicio sin configurar")
    except (httpx.HTTPError, ValueError, InvalidOperation):
        raise HTTPException(503, "Consulta no disponible") from None
    if buscar_razon and token and not resultado.get("coincidencias"):
        resultado["razon_social"] = consultas_empresas.consultar_razon_social(ruc, token)
    return resultado


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
        RolMiembro.SUPERADMIN,
        RolMiembro.ADMINISTRADOR,
        RolMiembro.SECRETARIA,
        RolMiembro.USUARIO,
        "GESTOR",
        RolMiembro.RESPONSABLE,
        RolMiembro.GERENTE,
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
    if auth.rol in (
        RolMiembro.USUARIO,
        "GESTOR",
        RolMiembro.RESPONSABLE,
        RolMiembro.GERENTE,
    ):
        if auth.rol == RolMiembro.USUARIO:
            filtro = Expediente.usuario_id == auth.usuario_id
        elif auth.rol == "GESTOR":
            filtro = Expediente.gestor_id == auth.gestor_id
        elif auth.rol == RolMiembro.RESPONSABLE:
            filtro = Expediente.usuario_id.in_(
                select(Miembro.id).where(
                    Miembro.tenant_id == tenant_id,
                    Miembro.responsable_id == auth.miembro_id,
                    Miembro.rol == RolMiembro.USUARIO,
                    Miembro.deleted_at.is_(None),
                )
            )
        else:
            filtro = alcance_expedientes_gerente(auth)
        permitidas = set(
            session.scalars(
                select(Empresa.id).where(
                    Empresa.id.in_([e.id for e in empresas]),
                    exists().where(
                        Expediente.tenant_id == tenant_id,
                        Expediente.deleted_at.is_(None),
                        expediente_tiene_documentos_activos(),
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
        session,
        tenant_id,
        "CLASIFICACION_SOLICITADA",
        "empresa",
        empresas[0].id,
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
    if auth.rol not in (
        RolMiembro.SUPERADMIN,
        RolMiembro.ADMINISTRADOR,
        RolMiembro.SECRETARIA,
        RolMiembro.RESPONSABLE,
        RolMiembro.GERENTE,
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene permiso para modificar Empresas")
    empresa = session.get(Empresa, empresa_id)
    if empresa is None or empresa.tenant_id != tenant_id or empresa.deleted_at:
        raise no_encontrado("Empresa")
    if auth.rol in (RolMiembro.RESPONSABLE, RolMiembro.GERENTE):
        if datos.model_fields_set != {"autorizada"}:
            raise HTTPException(403, "Solo puede autorizar clientes dentro de su ámbito")
        if auth.rol == RolMiembro.RESPONSABLE:
            ámbito = exists().where(
                Expediente.tenant_id == tenant_id,
                Expediente.deleted_at.is_(None),
                expediente_tiene_documentos_activos(),
                Expediente.receptor_id == empresa.id,
                Expediente.usuario_id.in_(
                    select(Miembro.id).where(
                        Miembro.tenant_id == tenant_id,
                        Miembro.responsable_id == auth.miembro_id,
                        Miembro.rol == RolMiembro.USUARIO,
                        Miembro.deleted_at.is_(None),
                    )
                ),
            )
        else:
            ámbito = exists().where(
                Expediente.tenant_id == tenant_id,
                Expediente.deleted_at.is_(None),
                expediente_tiene_documentos_activos(),
                Expediente.receptor_id == empresa.id,
                alcance_expedientes_gerente(auth),
            )
        if not session.query(ámbito).scalar():
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
    # La autorización es vigente hacia adelante. Cada expediente conserva su
    # estado de aprobación capturado al ingresar; cambiar la empresa no reescribe
    # estados, alertas ni cálculos históricos.
    campos_cambiados = datos.model_fields_set
    if "autorizada" not in campos_cambiados or campos_cambiados - {"autorizada"}:
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
    settings: SettingsDep,
    hoy: HoyDep,
    datos: EmpresasEliminarIn,
) -> EmpresasEliminarOut:
    if auth.rol != RolMiembro.ADMINISTRADOR:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo el ADMINISTRADOR del tenant puede eliminar empresas registradas",
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
        empresa.autorizada = False
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
    for empresa in empresas:
        recalcular_expedientes(session, tenant_id, hoy, settings, receptor_id=empresa.id)
    session.commit()
    return EmpresasEliminarOut(eliminadas=len(empresas))
