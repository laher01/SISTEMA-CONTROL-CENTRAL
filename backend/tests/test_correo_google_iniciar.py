"""OAuth Google: aislamiento entre tenants y configuración obligatoria."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CorreoBuzon, Miembro
from tests.conftest import AuthPrueba


def test_google_no_inicia_sin_configuracion(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    responsable = Miembro(
        tenant_id=tenant_id,
        codigo="RESP-GOOGLE",
        nombre="Responsable",
        rol="RESPONSABLE",
        activo=True,
    )
    session.add(responsable)
    session.flush()
    buzon = CorreoBuzon(
        tenant_id=tenant_id,
        direccion="factura.central.2023@gmail.com",
        proveedor="GOOGLE",
        responsable_id=responsable.id,
        activo=False,
    )
    session.add(buzon)
    session.commit()
    auth_prueba.como_admin()
    respuesta = client.post(f"/api/v1/correo/buzones/{buzon.id}/google/iniciar")
    assert respuesta.status_code == 503
    auth_prueba.como_gerente()
    prohibido = client.post(f"/api/v1/correo/buzones/{buzon.id}/google/iniciar")
    assert prohibido.status_code == 403
