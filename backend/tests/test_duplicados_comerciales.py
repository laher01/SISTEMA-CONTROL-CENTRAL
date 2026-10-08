from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Gestor
from tests.conftest import AuthPrueba
from tests.xml import factura


def test_factura_repetida_no_crea_expediente_nuevo(client: TestClient) -> None:
    xml = factura(numero="F001-00000801")
    primero = client.post("/api/v1/documentos", files={"archivo": ("primero.xml", xml)})
    assert primero.status_code == 201, primero.text
    segundo = client.post("/api/v1/documentos", files={"archivo": ("copia.xml", xml + b"\n")})
    assert segundo.status_code == 409, segundo.text
    assert segundo.json()["detail"]["duplicado"] is True
    assert "F001-801" in segundo.json()["detail"]["mensaje"]
    registros = client.get("/api/v1/registros")
    assert registros.json()["total_registros"] == 1


def test_otro_gestor_no_recibe_datos_privados(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    user_id = auth_prueba.contexto.usuario_id
    assert user_id is not None
    a = Gestor(
        tenant_id=auth_prueba.contexto.tenant_id,
        codigo="GESTA",
        nombre="Gestor A",
        usuario_id=user_id,
    )
    b = Gestor(
        tenant_id=auth_prueba.contexto.tenant_id,
        codigo="GESTB",
        nombre="Gestor B",
        usuario_id=user_id,
    )
    session.add_all([a, b])
    session.commit()
    auth_prueba.como_gestor(a.id, user_id)
    xml = factura(numero="F001-00000802")
    primero = client.post("/api/v1/documentos", files={"archivo": ("primero.xml", xml)})
    assert primero.status_code == 201, primero.text
    auth_prueba.como_gestor(b.id, user_id)
    segundo = client.post(
        "/api/v1/documentos", files={"archivo": ("copia.xml", xml + b"\n")}
    )
    assert segundo.status_code == 409, segundo.text
    detalle = segundo.json()["detail"]
    assert detalle["duplicado"] is True
    assert "Gestor A" not in detalle["mensaje"]
    assert "expediente_id" not in detalle
    assert "100" not in detalle["mensaje"]
