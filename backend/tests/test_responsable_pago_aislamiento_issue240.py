"""Regresiones de autorización financiera por jerarquía y tenant."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Miembro
from app.security import ContextoAcceso
from tests.conftest import AuthPrueba


def test_responsable_no_cotiza_usuarios_ajenos_o_de_otro_tenant(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    responsable = Miembro(
        tenant_id=tenant_id, codigo="RESP-PAGO-A", nombre="Responsable A",
        rol="RESPONSABLE", activo=True,
    )
    otro_responsable = Miembro(
        tenant_id=tenant_id, codigo="RESP-PAGO-B", nombre="Responsable B",
        rol="RESPONSABLE", activo=True,
    )
    session.add_all([responsable, otro_responsable])
    session.flush()
    propio = Miembro(
        tenant_id=tenant_id, codigo="USER-PAGO-A", nombre="Propio",
        rol="USUARIO", responsable_id=responsable.id, activo=True,
    )
    ajeno = Miembro(
        tenant_id=tenant_id, codigo="USER-PAGO-B", nombre="Ajeno",
        rol="USUARIO", responsable_id=otro_responsable.id, activo=True,
    )
    otro_tenant = Miembro(
        tenant_id=uuid.uuid4(), codigo="USER-PAGO-EX", nombre="Otro tenant",
        rol="USUARIO", responsable_id=None, activo=True,
    )
    session.add_all([propio, ajeno, otro_tenant])
    session.commit()
    auth_prueba.contexto = ContextoAcceso(
        cuenta_id=auth_prueba.contexto.cuenta_id,
        tenant_id=tenant_id,
        rol="RESPONSABLE",
        miembro_id=responsable.id,
        gestor_id=None,
        usuario_id=None,
        codigo=responsable.codigo,
        nombre=responsable.nombre,
        cambio_clave_obligatorio=False,
    )
    for usuario in (ajeno, otro_tenant):
        datos = {
            "usuario_id": str(usuario.id),
            "desde": "2026-09-01",
            "hasta": "2026-09-30",
            "moneda": "PEN",
        }
        cotizacion = client.post("/api/v1/responsable/pagos/cotizar", json=datos)
        programacion = client.post("/api/v1/responsable/pagos/programar", json=datos)
        assert cotizacion.status_code == 403, cotizacion.text
        assert programacion.status_code == 403, programacion.text
        listado = client.get(
            "/api/v1/responsable/pagos/liquidaciones",
            params={"usuario_id": str(usuario.id)},
        )
        assert listado.status_code == 403, listado.text
