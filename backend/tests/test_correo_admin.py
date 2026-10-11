"""Alta segura de buzones y alias de gestores dentro de cada tenant."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Gestor, Miembro
from tests.conftest import AuthPrueba


def test_admin_registra_buzones_y_alias_por_gestor(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    usuario = Miembro(
        tenant_id=tenant_id,
        codigo="USER-EMAIL-001",
        nombre="WILLI",
        rol="USUARIO",
        activo=True,
    )
    session.add(usuario)
    session.flush()
    gestor = Gestor(
        tenant_id=tenant_id,
        codigo="GEST-EMAIL-001",
        nombre="Jenny",
        usuario_id=usuario.id,
    )
    session.add(gestor)
    session.commit()
    auth_prueba.como_admin()

    for direccion, proveedor in (
        ("factur.central.2023@gmail.com", "GOOGLE"),
        ("factura_central@outlook.com", "MICROSOFT"),
        ("laher01.paita@gmail.com", "GOOGLE"),
    ):
        r = client.post(
            "/api/v1/correo/buzones",
            json={"direccion": direccion, "proveedor": proveedor},
        )
        assert r.status_code == 201, r.text
        assert r.json()["estado"] == "PENDIENTE_OAUTH"
    consulta = client.get("/api/v1/correo/buzones")
    assert consulta.status_code == 200, consulta.text
    assert len(consulta.json()) == 3
    assert all(not buzon["activo"] for buzon in consulta.json())

    for direccion in ("jenny2026@gmail.com", "astro15@gmail.com"):
        r = client.post(
            "/api/v1/correo/remitentes",
            json={"direccion": direccion, "gestor_id": str(gestor.id)},
        )
        assert r.status_code == 201, r.text
    remitentes = client.get("/api/v1/correo/remitentes")
    assert remitentes.status_code == 200, remitentes.text
    assert len(remitentes.json()) == 2
    assert all(fila["gestor_id"] == str(gestor.id) for fila in remitentes.json())


def test_remitente_no_se_asigna_a_dos_gestores(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    usuario = Miembro(
        tenant_id=tenant_id,
        codigo="USER-EMAIL-002",
        nombre="WILLI",
        rol="USUARIO",
        activo=True,
    )
    session.add(usuario)
    session.flush()
    gestores = [
        Gestor(
            tenant_id=tenant_id,
            codigo=codigo,
            nombre=nombre,
            usuario_id=usuario.id,
        )
        for codigo, nombre in (("JENNY-T1", "Jenny"), ("OTRO-T1", "Otro"))
    ]
    session.add_all(gestores)
    session.commit()
    auth_prueba.como_admin()
    url = "/api/v1/correo/remitentes"
    assert client.post(
        url,
        json={"direccion": "jenny2026@gmail.com", "gestor_id": str(gestores[0].id)},
    ).status_code == 201
    assert client.post(
        url,
        json={"direccion": "jenny2026@gmail.com", "gestor_id": str(gestores[1].id)},
    ).status_code == 409


def test_solo_admin_configura_recepcion(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    auth_prueba.como_gerente()
    assert client.get("/api/v1/correo/buzones").status_code == 403
    assert client.get("/api/v1/correo/remitentes").status_code == 403
    assert client.post(
        "/api/v1/correo/buzones",
        json={"direccion": "facturacion@example.com", "proveedor": "GOOGLE"},
    ).status_code == 403
