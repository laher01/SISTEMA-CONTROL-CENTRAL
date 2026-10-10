"""Solo un Responsable puede editar las dos tasas de su propio Usuario."""

import uuid
from dataclasses import replace
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Miembro
from tests.conftest import AuthPrueba


def test_responsable_edita_solo_tasas_de_su_usuario(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    responsable = Miembro(
        tenant_id=tenant_id, codigo="RESP01", nombre="Responsable", rol="RESPONSABLE"
    )
    propio = session.query(Miembro).filter_by(tenant_id=tenant_id, codigo="TESTUSR").one()
    ajeno = Miembro(tenant_id=tenant_id, codigo="AJENO01", nombre="Ajeno", rol="USUARIO")
    session.add_all([responsable, ajeno])
    session.flush()
    propio.responsable_id = responsable.id
    session.commit()
    auth_prueba.contexto = replace(
        auth_prueba.contexto,
        rol="RESPONSABLE",
        miembro_id=responsable.id,
        usuario_id=None,
    )
    datos = {"porcentaje_con_agente": "2.35", "porcentaje_sin_agente": "2.85"}
    ruta = f"/api/v1/miembros/mis-usuarios/{propio.id}/porcentajes"
    correcto = client.patch(ruta, json=datos)
    assert correcto.status_code == 200, correcto.text
    session.refresh(propio)
    assert propio.porcentaje_con_agente == Decimal("2.35")
    assert propio.porcentaje_sin_agente == Decimal("2.85")
    prohibido = client.patch(f"/api/v1/miembros/mis-usuarios/{ajeno.id}/porcentajes", json=datos)
    assert prohibido.status_code == 403
    invalido = client.patch(ruta, json={**datos, "porcentaje_con_agente": "101"})
    assert invalido.status_code == 422
    auth_prueba.como_usuario(propio.id)
    assert client.patch(ruta, json=datos).status_code == 403


@pytest.mark.parametrize("rol", ["GERENTE", "SECRETARIA", "USUARIO", "GESTOR"])
def test_roles_no_responsables_no_editar_tasas(
    client: TestClient, auth_prueba: AuthPrueba, rol: str
) -> None:
    auth_prueba.contexto = replace(auth_prueba.contexto, rol=rol)
    r = client.patch(
        f"/api/v1/miembros/mis-usuarios/{uuid.uuid4()}/porcentajes",
        json={"porcentaje_con_agente": "2", "porcentaje_sin_agente": "3"},
    )
    assert r.status_code == 403
