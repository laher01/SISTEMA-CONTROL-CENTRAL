"""Inventario global de espacios administrativos: exclusivo de SUPERADMIN."""

import hmac
import re
import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import OperativeAuthDep, SessionDep, SettingsDep
from app.enums import RolMiembro
from app.models import ChatMensaje, CuentaAcceso, Expediente, Gestor, Miembro, Tenant
from app.security import crear_o_restablecer_cuenta
from app.services import auditoria
from app.tenant_host import validar_subdominio


class AltaAdministracionIn(BaseModel):
    nombre_administrador: str = Field(min_length=3, max_length=180)
    nombre_espacio: str = Field(min_length=3, max_length=200)
    origen: str = "SUPERADMIN"
    subdominio: str | None = Field(default=None, max_length=63)


router = APIRouter(prefix="/configuracion/administraciones", tags=["configuracion"])


@router.get("")
def listar_administraciones(
    session: SessionDep,
    auth: OperativeAuthDep,
) -> list[dict[str, str | int]]:
    """Inventario de tenants, sin conceder acceso operativo cruzado."""
    if auth.rol != RolMiembro.SUPERADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo SUPERADMIN puede consultar tenants")
    miembros = {
        (tenant_id, rol): cantidad
        for tenant_id, rol, cantidad in session.execute(
            select(Miembro.tenant_id, Miembro.rol, func.count(Miembro.id))
            .where(Miembro.deleted_at.is_(None), Miembro.activo.is_(True))
            .group_by(Miembro.tenant_id, Miembro.rol)
        )
    }
    gestores = {
        tenant_id: cantidad
        for tenant_id, cantidad in session.execute(
            select(Gestor.tenant_id, func.count(Gestor.id))
            .where(Gestor.deleted_at.is_(None))
            .group_by(Gestor.tenant_id)
        )
    }
    cuentas = {
        tenant_id: cantidad
        for tenant_id, cantidad in session.execute(
            select(CuentaAcceso.tenant_id, func.count(CuentaAcceso.id))
            .where(CuentaAcceso.deleted_at.is_(None), CuentaAcceso.activo.is_(True))
            .group_by(CuentaAcceso.tenant_id)
        )
    }
    return [
        {
            "id": str(tenant.id),
            "nombre": tenant.nombre,
            "codigo": tenant.codigo or "",
            "subdominio": tenant.subdominio or "",
            "origen": tenant.origen_alta,
            "estado": tenant.estado,
            "administradores": miembros.get((tenant.id, RolMiembro.ADMINISTRADOR), 0),
            "gerentes": miembros.get((tenant.id, RolMiembro.GERENTE), 0),
            "secretarias": miembros.get((tenant.id, RolMiembro.SECRETARIA), 0),
            "usuarios": miembros.get((tenant.id, RolMiembro.USUARIO), 0),
            "gestores": gestores.get(tenant.id, 0),
            "cuentas_activas": cuentas.get(tenant.id, 0),
            "estado_suscripcion": "NO_IMPLEMENTADO",
        }
        for tenant in session.scalars(select(Tenant).order_by(Tenant.nombre))
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def crear_administracion(
    datos: AltaAdministracionIn,
    session: SessionDep,
    auth: OperativeAuthDep,
) -> dict[str, str]:
    """Provisión única de tenant y ADMIN01; no hereda datos de tenant anterior."""
    if auth.rol != RolMiembro.SUPERADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Exclusivo de SUPERADMIN")
    if datos.origen != "SUPERADMIN":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Origen no autorizado")
    return _provisionar_administracion(datos, session)


def _provisionar_administracion(
    datos: AltaAdministracionIn,
    session: SessionDep,
    *,
    plan_demo: str | None = None,
    correo_contacto: str | None = None,
    dni_contacto: str | None = None,
) -> dict[str, str]:
    nombre = " ".join(datos.nombre_administrador.strip().upper().split())
    partes = nombre.split()
    if len(partes) < 2:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Indique nombre y apellido")
    sigla = "".join(parte[0] for parte in partes[:3])
    if len(partes) == 2:
        sigla = (sigla + partes[-1][1:])[:3]
    if not re.fullmatch(r"[A-Z]{3}", sigla):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Iniciales inválidas")
    espacio = " ".join(datos.nombre_espacio.strip().split())
    if (
        session.scalar(select(Tenant.id).where(func.lower(Tenant.nombre) == espacio.lower()))
        is not None
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "Nombre administrativo ya registrado")
    if (
        session.scalar(select(Tenant.id).where(func.lower(Tenant.codigo) == espacio.lower()))
        is not None
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El nombre administrativo coincide con un código de Administración",
        )

    if session.bind is not None and session.bind.dialect.name == "postgresql":
        numero = session.scalar(select(func.nextval("secuencia_administraciones")))
    else:
        codigos = session.scalars(select(Tenant.codigo).where(Tenant.codigo.is_not(None))).all()
        numeros = []
        for existente in codigos:
            if existente is None:
                continue
            coincidencia = re.fullmatch(r"[A-Z]{3}-(\d{3})-AD", existente.upper())
            if coincidencia:
                numeros.append(int(coincidencia.group(1)))
        numero = max(numeros, default=0) + 1

    if numero is None or numero > 999:
        raise HTTPException(status.HTTP_409_CONFLICT, "Numeración agotada")
    codigo = f"{sigla}-{numero:03d}-AD"
    if (
        session.scalar(select(Tenant.id).where(func.lower(Tenant.nombre) == codigo.lower()))
        is not None
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El código generado coincide con el nombre de otra Administración",
        )
    try:
        subdominio = validar_subdominio(datos.subdominio) if datos.subdominio else None
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    tenant = Tenant(
        nombre=espacio,
        codigo=codigo,
        subdominio=subdominio,
        origen_alta="DEMO_AUTORIZADA" if plan_demo else "SUPERADMIN",
        plan_demo=plan_demo,
        correo_contacto=correo_contacto,
        dni_contacto=dni_contacto,
        estado="ACTIVO",
    )
    session.add(tenant)
    try:
        session.flush()
        administrador = Miembro(
            tenant_id=tenant.id,
            codigo="ADMIN01",
            nombre=nombre,
            rol=RolMiembro.ADMINISTRADOR,
            activo=True,
            creado_por_cuenta_id=None,
        )
        session.add(administrador)
        session.flush()
        _, temporal = crear_o_restablecer_cuenta(
            session, tenant.id, administrador.codigo, miembro_id=administrador.id
        )
        session.commit()
    except (IntegrityError, ValueError) as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "No se pudo crear la Administración") from exc
    return {
        "tenant_id": str(tenant.id),
        "codigo": codigo,
        "nombre": tenant.nombre,
        "subdominio": tenant.subdominio or "",
        "login": administrador.codigo,
        "clave_temporal": temporal,
        "origen": "SUPERADMIN",
    }


class AltaDemoIn(BaseModel):
    plan: Literal["inicial", "profesional", "full"]
    nombre_administrador: str = Field(min_length=3, max_length=180)
    correo: str = Field(min_length=5, max_length=200)
    dni: str = Field(pattern=r"^[0-9]{8}$")
    nombre_espacio: str = Field(min_length=3, max_length=200)
    subdominio: str = Field(min_length=3, max_length=63)
    clave_demo: str = Field(min_length=1)


@router.post("/demo", status_code=status.HTTP_201_CREATED)
def crear_administracion_demo(
    datos: AltaDemoIn, session: SessionDep, settings: SettingsDep
) -> dict[str, str]:
    """Exclusivo de demos autorizadas. No equivale a confirmación de un pago."""
    if (
        not settings.demo_signup_key
        or len(settings.demo_signup_key) < 32
        or not hmac.compare_digest(datos.clave_demo, settings.demo_signup_key)
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Activación demo no autorizada")
    if "@" not in datos.correo or datos.correo.startswith("@"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Correo inválido")
    if not settings.tenant_domain:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Dominio de administraciones no configurado",
        )
    alta = _provisionar_administracion(
        AltaAdministracionIn(
            nombre_administrador=datos.nombre_administrador,
            nombre_espacio=datos.nombre_espacio,
            subdominio=datos.subdominio,
        ),
        session,
        plan_demo=datos.plan,
        correo_contacto=datos.correo.strip().lower(),
        dni_contacto=datos.dni,
    )
    return {
        **alta,
        "plan_demo": datos.plan,
        "url": f"https://{alta['subdominio']}.{settings.tenant_domain}/ingresar",
    }


@router.get("/{tenant_id}/estructura")
def estructura_global_tenant(
    tenant_id: uuid.UUID,
    session: SessionDep,
    auth: OperativeAuthDep,
) -> dict[str, object]:
    """Consulta global del tenant; no suplanta sesiones ni expone contraseñas."""
    if auth.rol != RolMiembro.SUPERADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo SUPERADMIN")
    tenant = session.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Administración no encontrada")
    miembros = session.scalars(
        select(Miembro)
        .where(
            Miembro.tenant_id == tenant_id,
            Miembro.deleted_at.is_(None),
        )
        .order_by(Miembro.rol, Miembro.codigo)
    ).all()
    gestores = session.scalars(
        select(Gestor)
        .where(
            Gestor.tenant_id == tenant_id,
            Gestor.deleted_at.is_(None),
        )
        .order_by(Gestor.codigo)
    ).all()
    return {
        "id": str(tenant.id),
        "nombre": tenant.nombre,
        "codigo": tenant.codigo or "",
        "subdominio": tenant.subdominio or "",
        "estado": tenant.estado,
        "miembros": [
            {
                "id": str(m.id),
                "codigo": m.codigo,
                "nombre": m.nombre,
                "rol": m.rol,
                "activo": m.activo,
                "responsable_id": str(m.responsable_id) if m.responsable_id else None,
            }
            for m in miembros
        ],
        "gestores": [
            {
                "id": str(g.id),
                "codigo": g.codigo,
                "nombre": g.nombre,
                "usuario_id": str(g.usuario_id) if g.usuario_id else None,
            }
            for g in gestores
        ],
    }


@router.get("/{tenant_id}/expedientes")
def expedientes_globales_tenant(
    tenant_id: uuid.UUID,
    session: SessionDep,
    auth: OperativeAuthDep,
    limite: int = 100,
) -> dict[str, object]:
    """Inspección supervisada, paginación acotada; ninguna suplantación de identidad."""
    if auth.rol != RolMiembro.SUPERADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo SUPERADMIN")
    if limite < 1 or limite > 100:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Límite fuera de rango")
    tenant = session.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Administración no encontrada")
    expedientes = session.scalars(
        select(Expediente)
        .where(Expediente.tenant_id == tenant_id, Expediente.deleted_at.is_(None))
        .order_by(Expediente.created_at.desc(), Expediente.id.desc())
        .limit(limite)
    ).all()
    auditoria.registrar(
        session,
        tenant_id,
        "SUPERADMIN_CONSULTA_EXPEDIENTES",
        "tenant",
        tenant_id,
        {"actor_cuenta_id": str(auth.cuenta_id), "limite": limite},
    )
    session.commit()
    return {
        "tenant_id": str(tenant_id),
        "expedientes": [
            {
                "id": str(e.id),
                "tipo": e.tipo_comprobante,
                "serie": e.serie,
                "correlativo": e.correlativo,
                "fecha_emision": e.fecha_emision.isoformat(),
                "moneda": e.moneda,
                "importe_total": str(e.importe_total),
                "estado": e.estado,
                "usuario_id": str(e.usuario_id) if e.usuario_id else None,
                "gestor_id": str(e.gestor_id) if e.gestor_id else None,
            }
            for e in expedientes
        ],
    }


@router.get("/{tenant_id}/chats")
def chats_globales_tenant(
    tenant_id: uuid.UUID,
    session: SessionDep,
    auth: OperativeAuthDep,
    limite: int = 100,
) -> dict[str, object]:
    """Historial auditado del tenant, solo lectura global, sin suplantación."""
    if auth.rol != RolMiembro.SUPERADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo SUPERADMIN")
    if not 1 <= limite <= 100:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Límite inválido")
    tenant = session.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant inexistente")
    items = session.scalars(
        select(ChatMensaje)
        .where(
            ChatMensaje.tenant_id == tenant_id,
            ChatMensaje.deleted_at.is_(None),
        )
        .order_by(ChatMensaje.created_at.desc(), ChatMensaje.id.desc())
        .limit(limite)
    ).all()
    auditoria.registrar(
        session,
        tenant_id,
        "SUPERADMIN_CONSULTA_CHATS",
        "tenant",
        tenant_id,
        {"actor_cuenta_id": str(auth.cuenta_id), "limite": limite},
    )
    session.commit()
    return {
        "tenant_id": str(tenant_id),
        "mensajes": [
            {
                "id": str(m.id),
                "remitente_cuenta_id": str(m.remitente_cuenta_id),
                "destinatario_cuenta_id": str(m.destinatario_cuenta_id),
                "texto": m.texto,
                "archivo_nombre": m.archivo_nombre,
                "created_at": m.created_at.isoformat(),
            }
            for m in items
        ],
    }


@router.delete("/{tenant_id}/chats/{mensaje_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_chat_global(
    tenant_id: uuid.UUID,
    mensaje_id: uuid.UUID,
    session: SessionDep,
    auth: OperativeAuthDep,
) -> None:
    """Eliminar lógicamente, conservar evidencia y autor identificable."""
    if auth.rol != RolMiembro.SUPERADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo SUPERADMIN")
    mensaje = session.get(ChatMensaje, mensaje_id)
    if mensaje is None or mensaje.tenant_id != tenant_id or mensaje.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mensaje no encontrado")
    mensaje.deleted_at = datetime.now(UTC)
    mensaje.eliminado_por_cuenta_id = auth.cuenta_id
    auditoria.registrar(
        session,
        tenant_id,
        "SUPERADMIN_ELIMINA_CHAT",
        "chat_mensaje",
        mensaje_id,
        {"actor_cuenta_id": str(auth.cuenta_id), "eliminacion": "logica"},
    )
    session.commit()
