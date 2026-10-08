from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CuentaAcceso, Miembro
from tests.conftest import AuthPrueba


def _crear_contacto(session: Session, tenant_id: object, codigo: str, rol: str) -> str:
    miembro = Miembro(
        tenant_id=tenant_id,
        codigo=codigo,
        nombre=codigo,
        rol=rol,
        activo=True,
    )
    session.add(miembro)
    session.flush()
    cuenta = CuentaAcceso(
        tenant_id=tenant_id,
        login=codigo,
        password_hash="test-hash",
        miembro_id=miembro.id,
        activo=True,
        cambio_clave_obligatorio=False,
    )
    session.add(cuenta)
    session.commit()
    return str(cuenta.id)


def test_chat_privado_mensaje_y_adjunto(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    admin_id = _crear_contacto(session, tenant_id, "ADMIN-CHAT", "ADMINISTRADOR")
    externo_id = _crear_contacto(session, tenant_id, "USUARIO-AJENO", "USUARIO")
    contactos = client.get("/api/v1/chat/contactos")
    assert contactos.status_code == 200, contactos.text
    ids = {item["cuenta_id"] for item in contactos.json()}
    assert admin_id in ids
    assert externo_id not in ids

    prohibido = client.post(
        "/api/v1/chat/mensajes",
        data={"destinatario_cuenta_id": externo_id, "texto": "No permitido"},
    )
    assert prohibido.status_code == 404

    enviado = client.post(
        "/api/v1/chat/mensajes",
        data={"destinatario_cuenta_id": admin_id, "texto": "Revisar expediente"},
        files={"archivo": ("nota.txt", b"Datos permitidos", "text/plain")},
    )
    assert enviado.status_code == 201, enviado.text
    mensaje_id = enviado.json()["id"]
    mensajes = client.get("/api/v1/chat/mensajes", params={"con": admin_id})
    assert mensajes.status_code == 200, mensajes.text
    assert [m["texto"] for m in mensajes.json()] == ["Revisar expediente"]
    archivo = client.get(f"/api/v1/chat/mensajes/{mensaje_id}/archivo")
    assert archivo.status_code == 200, archivo.text
    assert archivo.content == b"Datos permitidos"
    assert "attachment" in archivo.headers["content-disposition"].lower()
