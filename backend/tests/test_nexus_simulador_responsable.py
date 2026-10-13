"""Pruebas de acceso y cálculo del simulador JONA01 en Responsable."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Miembro
from tests.conftest import AuthPrueba


def test_simulacion_jona01_no_crea_pago(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    usuario = Miembro(
        tenant_id=auth_prueba.contexto.tenant_id,
        codigo="JONA01",
        nombre="Jonatan Lama",
        rol="USUARIO",
        activo=True,
    )
    session.add(usuario)
    session.commit()
    auth_prueba.como_admin()
    respuesta = client.post(
        "/api/v1/responsable/pagos/formulas/simular-jonatan",
        json={
            "usuario_id": str(usuario.id),
            "total_emitido": "100000.00",
            "base_autorizada": "100000.00",
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["gente_lima"] == "2250.00"
    assert datos["javier"] == "125.00"
    assert datos["jonatan"] == "312.50"
    assert datos["total_distribuido"] == "2687.50"
    assert datos["estado"] == "SIMULACION_NO_AUTORIZADA"

    incompatible = client.post(
        "/api/v1/responsable/pagos/formulas/simular-jonatan",
        json={
            "usuario_id": str(usuario.id),
            "total_emitido": "100000.00",
            "base_autorizada": "100.00",
            "usar_total_emitido": True,
        },
    )
    assert incompatible.status_code == 422


def test_simulador_rechaza_otro_usuario(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    usuario = Miembro(
        tenant_id=auth_prueba.contexto.tenant_id,
        codigo="OTRO01",
        nombre="Otro usuario",
        rol="USUARIO",
        activo=True,
    )
    session.add(usuario)
    session.commit()
    auth_prueba.como_admin()
    respuesta = client.post(
        "/api/v1/responsable/pagos/formulas/simular-jonatan",
        json={
            "usuario_id": str(usuario.id),
            "total_emitido": "100.00",
            "usar_total_emitido": True,
        },
    )
    assert respuesta.status_code == 422


def test_usuario_no_puede_administrar_formulas(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    usuario = Miembro(
        tenant_id=auth_prueba.contexto.tenant_id,
        codigo="OTRO02",
        nombre="Usuario sin permisos de Responsable",
        rol="USUARIO",
        activo=True,
    )
    session.add(usuario)
    session.commit()
    auth_prueba.como_usuario(usuario.id, codigo="OTRO02")
    listado = client.get("/api/v1/responsable/pagos/formulas")
    assert listado.status_code == 403
    creacion = client.post(
        "/api/v1/responsable/pagos/formulas",
        json={
            "usuario_id": str(usuario.id),
            "nombre": "Formula no autorizada",
            "descripcion": "Intento sin permiso de Responsable",
            "plantilla": "PAGO_ESTANDAR_V1",
        },
    )
    assert creacion.status_code == 403
