from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Empresa
from tests.conftest import AuthPrueba
from tests.xml import RECEPTOR, factura


def test_auditoria_fiscal_solo_consulta(
    client: TestClient, auth_prueba: AuthPrueba, session: Session
) -> None:
    session.add(
        Empresa(
            tenant_id=auth_prueba.contexto.tenant_id,
            ruc=RECEPTOR,
            razon_social="CLIENTE SAC",
            autorizada=True,
        )
    )
    session.commit()
    ruta = "/api/v1/registros/auditoria-fiscal"
    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("factura.xml", factura(numero="F001-00000901"))},
    )
    assert subida.status_code == 201, subida.text
    assert client.get(ruta).status_code == 403

    auth_prueba.como_admin()
    respuesta = client.get(ruta)
    assert respuesta.status_code == 200, respuesta.text
    resultado = respuesta.json()
    assert resultado["total"] == 1
    assert resultado["filas"][0]["estado_fiscal"] == "PENDIENTE_VERIFICACION"
    assert "credito_fiscal" not in resultado
    assert client.get(ruta, params={"emisor": "00000000000"}).json()["total"] == 0
    assert (
        client.get(
            ruta, params={"fecha_desde": "2026-10-10", "fecha_hasta": "2026-10-01"}
        ).status_code
        == 422
    )

    auth_prueba.como_gerente()
    respuesta = client.get(ruta)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["total"] == 0
