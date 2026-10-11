"""La bandeja de recepción solo muestra correos atribuidos al gestor autenticado."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CorreoBuzon, CorreoMensaje, CorreoRemitente, Gestor, Miembro
from tests.conftest import AuthPrueba


def test_mi_recepcion_aisla_gestores(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    usuario = Miembro(tenant_id=tenant_id, codigo="WILLI-TEST", nombre="Willi",
                     rol="USUARIO", activo=True)
    responsable = Miembro(tenant_id=tenant_id, codigo="RESP-MAIL", nombre="Responsable",
                         rol="RESPONSABLE", activo=True)
    session.add_all([usuario, responsable])
    session.flush()
    jenny = Gestor(tenant_id=tenant_id, codigo="JENNY-MAIL", nombre="Jenny",
                   usuario_id=usuario.id)
    otro = Gestor(tenant_id=tenant_id, codigo="OTRO-MAIL", nombre="Otro",
                  usuario_id=usuario.id)
    session.add_all([jenny, otro])
    session.flush()
    buzon = CorreoBuzon(tenant_id=tenant_id, direccion="entrada@example.test",
                        proveedor="GOOGLE", responsable_id=responsable.id, activo=False)
    session.add(buzon)
    session.flush()
    session.add_all([
        CorreoRemitente(tenant_id=tenant_id, direccion="jenny2026@gmail.com",
                       gestor_id=jenny.id, activo=True),
        CorreoRemitente(tenant_id=tenant_id, direccion="astro15@gmail.com",
                       gestor_id=jenny.id, activo=True),
        CorreoRemitente(tenant_id=tenant_id, direccion="otro@example.test",
                       gestor_id=otro.id, activo=True),
        CorreoMensaje(tenant_id=tenant_id, buzon_id=buzon.id,
                      identificador_externo="uid-j", remitente="jenny2026@gmail.com",
                      gestor_id=jenny.id, estado="INGRESADO"),
        CorreoMensaje(tenant_id=tenant_id, buzon_id=buzon.id,
                      identificador_externo="uid-o", remitente="otro@example.test",
                      gestor_id=otro.id, estado="INGRESADO"),
    ])
    session.commit()
    auth_prueba.como_gestor(jenny.id, usuario.id, "JENNY-MAIL")
    resp = client.get("/api/v1/correo/mi-recepcion")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert sorted(data["remitentes"]) == ["astro15@gmail.com", "jenny2026@gmail.com"]
    assert len(data["mensajes"]) == 1
    assert data["mensajes"][0]["remitente"] == "jenny2026@gmail.com"
    auth_prueba.como_admin()
    assert client.get("/api/v1/correo/mi-recepcion").status_code == 403
