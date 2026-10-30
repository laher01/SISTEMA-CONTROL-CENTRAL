from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Expediente, Miembro
from app.security import ContextoAcceso
from tests.conftest import AuthPrueba
from tests.xml import factura


def _subir_factura(client: TestClient, numero: str = "F001-00000991") -> dict[str, object]:
    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": (numero + ".xml", factura(numero=numero, importe="123.45"))},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_eliminar_ultimo_documento_elimina_expediente_y_permite_reingreso(
    client: TestClient,
    auth_prueba: AuthPrueba,
    session: Session,
) -> None:
    documento = _subir_factura(client)
    expediente_id = UUID(str(documento["expediente_id"]))
    assert client.get(f"/api/v1/expedientes/{expediente_id}").status_code == 200

    auth_prueba.como_admin()
    eliminacion = client.delete(f"/api/v1/documentos/{documento['id']}")
    assert eliminacion.status_code == 200, eliminacion.text
    assert session.get(Expediente, expediente_id) is None
    assert client.get(f"/api/v1/expedientes/{expediente_id}").status_code == 404
    assert client.get("/api/v1/expedientes").json() == []

    resumen = client.get("/api/v1/expedientes/resumen")
    assert resumen.status_code == 200, resumen.text
    assert resumen.json()["total_expedientes"] == 0
    assert Decimal(resumen.json()["total_pen"]) == Decimal("0")

    auth_prueba.como_usuario(auth_prueba.usuario_id)
    nuevo = _subir_factura(client)
    assert nuevo["expediente_id"] != str(expediente_id)


def test_resumen_de_responsable_respeta_filtros_de_usuario_y_gestor(
    client: TestClient,
    auth_prueba: AuthPrueba,
    session: Session,
) -> None:
    documento = _subir_factura(client, "F001-00000992")
    usuario = session.get(Miembro, auth_prueba.usuario_id)
    assert usuario is not None
    responsable = Miembro(
        tenant_id=auth_prueba.contexto.tenant_id,
        codigo="RESP-TEST",
        nombre="Responsable de pruebas",
        rol="RESPONSABLE",
        activo=True,
    )
    session.add(responsable)
    session.flush()
    usuario.responsable_id = responsable.id
    session.commit()

    actual = auth_prueba.contexto
    auth_prueba.contexto = ContextoAcceso(
        cuenta_id=actual.cuenta_id,
        tenant_id=actual.tenant_id,
        rol="RESPONSABLE",
        miembro_id=responsable.id,
        gestor_id=None,
        usuario_id=None,
        codigo=responsable.codigo,
        nombre=responsable.nombre,
        cambio_clave_obligatorio=False,
    )
    params = {"usuario_id": str(usuario.id), "gestor_id": str(auth_prueba.gestor_id)}
    lista = client.get("/api/v1/expedientes", params=params)
    resumen = client.get("/api/v1/expedientes/resumen", params=params)

    assert lista.status_code == 200, lista.text
    assert resumen.status_code == 200, resumen.text
    assert len(lista.json()) == resumen.json()["total_expedientes"] == 1
    assert lista.json()[0]["id"] == documento["expediente_id"]
    assert Decimal(resumen.json()["total_pen"]) == Decimal("123.45")
