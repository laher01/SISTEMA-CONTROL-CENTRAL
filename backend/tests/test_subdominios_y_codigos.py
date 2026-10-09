import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.codigos import codigo_automatico, iniciales
from app.core.config import Settings
from app.models import Miembro, Tenant
from app.tenant_host import tenant_de_host, validar_sesion_host, validar_subdominio
from tests.conftest import AuthPrueba


def _request(host: str) -> Request:
    return Request({"type": "http", "headers": [(b"host", host.encode())]})


def test_subdominios_unicos_y_sesion_aislada(session: Session) -> None:
    admin_a = Tenant(nombre="Empresa A", codigo="AAA-001-AD", subdominio="empresa-a")
    admin_b = Tenant(nombre="Empresa B", codigo="BBB-002-AD", subdominio="empresa-b")
    session.add_all([admin_a, admin_b])
    session.commit()
    config = Settings(tenant_domain="factcentral.online")
    assert tenant_de_host(_request("empresa-a.factcentral.online"), session, config) == admin_a
    assert tenant_de_host(_request("empresa-b.factcentral.online"), session, config) == admin_b
    assert tenant_de_host(_request("app.nexomarnegocioseirl.online"), session, config) is None
    validar_sesion_host(_request("empresa-a.factcentral.online"), session, config, admin_a.id)
    with pytest.raises(HTTPException) as error:
        validar_sesion_host(_request("empresa-b.factcentral.online"), session, config, admin_a.id)
    assert error.value.status_code == 403
    with pytest.raises(HTTPException) as desconocido:
        tenant_de_host(_request("desconocida.factcentral.online"), session, config)
    assert desconocido.value.status_code == 404
    with pytest.raises(HTTPException):
        tenant_de_host(_request("otros.empresa-a.factcentral.online"), session, config)


def test_validacion_de_subdominio() -> None:
    assert validar_subdominio(" NEXOMAR ") == "nexomar"
    for nombre in ("www", "api", "app", "-abc", "abc-", "ab", "a.b", "nexomar.local"):
        with pytest.raises(ValueError):
            validar_subdominio(nombre)


def test_codigos_automaticos_sin_reutilizar_login(session: Session) -> None:
    tenant = Tenant(nombre="Prueba código", codigo="PCC-003-AD")
    session.add(tenant)
    session.flush()
    assert iniciales("Eduardo Ayala") == "EAX"
    assert codigo_automatico(session, tenant.id, "Eduardo Ayala", "USUARIO") == "EAX-001-US"
    session.add(Miembro(tenant_id=tenant.id, codigo="EAX-001-US", nombre="Eduardo", rol="USUARIO"))
    session.flush()
    assert codigo_automatico(session, tenant.id, "Eduardo Ayala", "USUARIO") == "EAX-002-US"


def test_alta_miembro_generando_codigo(
    client: TestClient, auth_prueba: AuthPrueba,
) -> None:
    auth_prueba.como_admin()
    respuesta = client.post("/api/v1/miembros", json={"nombre": "Eduardo Ayala", "rol": "USUARIO"})
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["miembro"]["codigo"] == "EAX-001-US"
    assert respuesta.json()["credencial"]["login"] == "EAX-001-US"
