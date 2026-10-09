import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.routes.administraciones import AltaDemoIn, crear_administracion_demo
from app.core.config import Settings
from app.models import Miembro, Tenant


def test_demo_desactivada_por_defecto(session: Session) -> None:
    datos = AltaDemoIn(
        plan="inicial",
        nombre_administrador="Carlos Juarez Perez",
        correo="carlos@example.com",
        dni="12345678",
        nombre_espacio="Prueba Carlos",
        subdominio="prueba-carlos",
        clave_demo="clave-cualquiera",
    )
    with pytest.raises(HTTPException) as error:
        crear_administracion_demo(datos, session, Settings(demo_signup_key=None))
    assert error.value.status_code == 403


def test_demo_autorizada_crea_tenant_aislado(session: Session) -> None:
    from sqlalchemy import select

    datos = AltaDemoIn(
        plan="profesional",
        nombre_administrador="Carlos Juarez",
        correo="carlos@example.com",
        dni="12345678",
        nombre_espacio="Administracion Carlos Juarez",
        subdominio="carlos-juarez",
        clave_demo="A" * 48,
    )
    config = Settings(demo_signup_key="A" * 48, tenant_domain="factcentral.online")
    resultado = crear_administracion_demo(datos, session, config)
    assert resultado["login"] == "ADMIN01"
    assert resultado["clave_temporal"]
    assert resultado["plan_demo"] == "profesional"
    assert resultado["url"] == "https://carlos-juarez.factcentral.online/ingresar"
    tenant = session.scalar(select(Tenant).where(Tenant.subdominio == "carlos-juarez"))
    assert tenant is not None
    assert tenant.plan_demo == "profesional"
    assert tenant.correo_contacto == "carlos@example.com"
    assert tenant.dni_contacto == "12345678"
    miembro = session.scalar(select(Miembro).where(Miembro.tenant_id == tenant.id))
    assert miembro is not None and miembro.rol == "ADMINISTRADOR"
