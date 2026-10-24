import uuid
from datetime import date
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.models import PermisoConfigurado
from app.security import ContextoAcceso, contexto_desde_token
from app.storage import AlmacenLocal
from app.tenant_host import validar_sesion_host

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_hoy(settings: SettingsDep) -> date:
    return settings.hoy()


def get_almacen(settings: SettingsDep) -> AlmacenLocal:
    return AlmacenLocal(settings.storage_dir)


def get_contexto_actual(
    request: Request,
    session: SessionDep,
    settings: SettingsDep,
) -> ContextoAcceso:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Debe iniciar sesión")
    contexto = contexto_desde_token(session, token)
    if contexto is None:
        session.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión inválida o vencida")
    validar_sesion_host(request, session, settings, contexto.tenant_id)
    session.commit()
    return contexto


def get_contexto_operativo(
    request: Request,
    contexto: Annotated[ContextoAcceso, Depends(get_contexto_actual)],
    session: SessionDep,
) -> ContextoAcceso:
    if contexto.cambio_clave_obligatorio:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Debe cambiar la clave temporal antes de continuar",
        )
    if contexto.rol == "SUPERADMIN" and not (
        request.url.path == "/api/v1/configuracion/administraciones"
        or request.url.path.startswith("/api/v1/configuracion/administraciones/")
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "SUPERADMIN solo puede acceder a las funciones globales de plataforma",
        )
    if contexto.rol == "SECRETARIA":
        ruta = request.url.path
        modulo = None
        if ruta == "/api/v1/registros":
            modulo = "SECRETARIA_MENU_REGISTROS"
        elif ruta == "/api/v1/dashboard/secretaria-expedientes":
            modulo = "SECRETARIA_MENU_CONTROL_DOCUMENTAL"
        elif ruta in {"/api/v1/documentos", "/api/v1/documentos/resumen"}:
            modulo = "SECRETARIA_MENU_DOCUMENTOS"
        if modulo is not None:
            permiso = session.scalar(
                select(PermisoConfigurado).where(
                    PermisoConfigurado.tenant_id == contexto.tenant_id,
                    PermisoConfigurado.rol == "SECRETARIA",
                    PermisoConfigurado.permiso == modulo,
                )
            )
            if permiso is not None and not permiso.habilitado:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Módulo desactivado para Secretaría")
    permitido_responsable = (
        (
            request.method == "GET"
            and request.url.path
            in {
                "/api/v1/contabilidad-items",
                "/api/v1/contabilidad-items/conciliacion",
                "/api/v1/contabilidad-items/exportar-csv",
            }
            or (
                request.method == "GET"
                and request.url.path.startswith("/api/v1/contabilidad-items/expedientes/")
                and request.url.path.endswith("/detalle")
            )
        )
        or (
            request.method == "PATCH"
            and request.url.path.startswith("/api/v1/miembros/mis-usuarios/")
            and request.url.path.endswith("/porcentajes")
        )
        or (
            request.method in {"GET", "POST"}
            and request.url.path == "/api/v1/miembros/mis-usuarios"
        )
        or (request.method == "POST" and request.url.path == "/api/v1/comisiones/simular")
        or (request.method == "GET" and request.url.path == "/api/v1/comisiones/receptores")
        or (
            request.method == "GET"
            and request.url.path
            in {
                "/api/v1/dashboard/resumen",
                "/api/v1/dashboard/desglose",
                "/api/v1/dashboard/opciones",
            }
        )
        or (request.method == "GET" and request.url.path == "/api/v1/responsable/resumen")
        or (request.method == "GET" and request.url.path == "/api/v1/expedientes/resumen-empresas")
        or (request.method == "GET" and request.url.path == "/api/v1/gestores")
        or (
            request.method == "GET"
            and (
                request.url.path == "/api/v1/documentos"
                or request.url.path == "/api/v1/documentos/resumen"
                or (
                    request.url.path.startswith("/api/v1/documentos/")
                    and (
                        len(request.url.path.split("/")) == 5
                        or request.url.path.endswith("/archivo")
                    )
                )
            )
        )
        or (
            request.method == "GET"
            and (
                request.url.path == "/api/v1/expedientes"
                or request.url.path == "/api/v1/expedientes/ids"
                or (
                    request.url.path.startswith("/api/v1/expedientes/")
                    and request.url.path.split("/")[-1] not in {"resumen", "recalcular"}
                )
            )
        )
        or (
            request.method in {"GET", "POST"}
            and request.url.path == "/api/v1/responsable/pagos/formulas"
        )
        or (
            request.method == "POST"
            and request.url.path == "/api/v1/responsable/pagos/formulas/simular-jonatan"
        )
        or (
            request.method == "POST"
            and request.url.path.startswith("/api/v1/responsable/pagos/formulas/")
            and request.url.path.endswith(("/aprobar", "/revocar"))
        )
        or (request.method == "GET" and request.url.path == "/api/v1/gerencias/vinculos")
        or (
            request.method == "POST"
            and request.url.path
            in {
                "/api/v1/responsable/pagos/cotizar",
                "/api/v1/responsable/pagos/programar",
            }
        )
        or (
            request.method == "DELETE" and request.url.path.startswith("/api/v1/responsable/pagos/")
        )
        or (
            request.method == "POST"
            and request.url.path.startswith("/api/v1/responsable/pedidos/")
            and request.url.path.endswith("/distribuir")
        )
    )
    # MISD restringe cada solicitud por tenant, cartera y jerarquía en su ruta.
    # Autorizar entrada a la API no concede autorización sobre un expediente.
    permitido_responsable = permitido_responsable or (
        request.url.path == "/api/v1/misd/solicitudes"
        and request.method in {"GET", "POST"}
    ) or (
        request.method == "POST"
        and request.url.path.startswith("/api/v1/misd/solicitudes/")
        and request.url.path.endswith(("/resolver", "/ejecutar"))
    )
    if contexto.rol == "RESPONSABLE" and not permitido_responsable:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El rol Responsable solo tiene habilitada su cartera de Usuarios en esta etapa",
        )
    return contexto


def get_tenant_id(
    contexto: Annotated[ContextoAcceso, Depends(get_contexto_operativo)],
) -> uuid.UUID:
    return contexto.tenant_id


HoyDep = Annotated[date, Depends(get_hoy)]
AlmacenDep = Annotated[AlmacenLocal, Depends(get_almacen)]
AuthDep = Annotated[ContextoAcceso, Depends(get_contexto_actual)]
OperativeAuthDep = Annotated[ContextoAcceso, Depends(get_contexto_operativo)]
TenantDep = Annotated[uuid.UUID, Depends(get_tenant_id)]
