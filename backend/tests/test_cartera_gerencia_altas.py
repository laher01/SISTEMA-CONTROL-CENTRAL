"""Altas manuales/importadas y vínculo por RUC único en el tenant."""

from dataclasses import replace

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Empresa, GerenteEmpresa, Miembro
from tests.conftest import AuthPrueba


def test_admin_importa_y_reutiliza_empresa_del_tenant(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    tenant = auth_prueba.contexto.tenant_id
    gerente_a = Miembro(tenant_id=tenant, rol="GERENTE", codigo="GER-A", nombre="Gerencia A")
    gerente_b = Miembro(tenant_id=tenant, rol="GERENTE", codigo="GER-B", nombre="Gerencia B")
    session.add_all([gerente_a, gerente_b])
    session.commit()
    auth_prueba.como_admin()
    empresa = {"ruc": "20538821374", "razon_social": "MAREUF", "tipo_relacion": "CLIENTE"}
    primera = client.post(
        "/api/v1/gerencias/empresas/alta", json={**empresa, "gerente_id": str(gerente_a.id)}
    )
    assert primera.status_code == 201, primera.text
    assert primera.json()["resultado"] == "CREADA"

    segunda = client.post(
        "/api/v1/gerencias/empresas/importar",
        json={"gerente_id": str(gerente_b.id), "empresas": [
            {**empresa, "razon_social": "NO ALTERAR FICHA ORIGINAL"},
            {"ruc": "20444444444", "razon_social": "Proveedor nuevo", "tipo_relacion": "PROVEEDOR"},
        ]},
    )
    assert segunda.status_code == 200, segunda.text
    assert segunda.json() == {"creadas": 1, "vinculadas": 1}
    assert len(session.scalars(select(Empresa).where(Empresa.tenant_id == tenant)).all()) == 2
    original = session.scalar(select(Empresa).where(Empresa.ruc == "20538821374"))
    assert original.razon_social == "MAREUF"
    assert len(session.scalars(select(GerenteEmpresa).where(
        GerenteEmpresa.empresa_id == original.id,
        GerenteEmpresa.activo.is_(True),
    )).all()) == 2


def test_gerente_no_puede_operar_cartera_de_otro(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    tenant = auth_prueba.contexto.tenant_id
    gerente = Miembro(tenant_id=tenant, rol="GERENTE", codigo="GER-C", nombre="Gerencia C")
    ajeno = Miembro(tenant_id=tenant, rol="GERENTE", codigo="GER-D", nombre="Gerencia D")
    session.add_all([gerente, ajeno])
    session.commit()
    auth_prueba.contexto = replace(
        auth_prueba.contexto, rol="GERENTE", miembro_id=gerente.id, usuario_id=None
    )
    datos = {"ruc": "20999999999", "razon_social": "Empresa exclusiva", "tipo_relacion": "CLIENTE"}
    negado = client.post(
        "/api/v1/gerencias/empresas/alta", json={**datos, "gerente_id": str(ajeno.id)}
    )
    assert negado.status_code == 403
    permitido = client.post("/api/v1/gerencias/empresas/alta", json=datos)
    assert permitido.status_code == 201, permitido.text
    repetida = client.post("/api/v1/gerencias/empresas/alta", json=datos)
    assert repetida.json()["resultado"] == "VINCULADA"


def test_importacion_rechaza_ruc_duplicado_y_rol_no_autorizado(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    gerente = Miembro(
        tenant_id=auth_prueba.contexto.tenant_id,
        rol="GERENTE", codigo="GER-E", nombre="Gerencia E"
    )
    session.add(gerente)
    session.commit()
    auth_prueba.como_admin()
    datos = {"ruc": "20538821374", "razon_social": "MAREUF"}
    duplicado = client.post(
        "/api/v1/gerencias/empresas/importar",
        json={"gerente_id": str(gerente.id), "empresas": [datos, datos]},
    )
    assert duplicado.status_code == 422
    auth_prueba.como_usuario(auth_prueba.contexto.miembro_id)
    prohibido = client.post(
        "/api/v1/gerencias/empresas/alta",
        json={**datos, "gerente_id": str(gerente.id)},
    )
    assert prohibido.status_code == 403
