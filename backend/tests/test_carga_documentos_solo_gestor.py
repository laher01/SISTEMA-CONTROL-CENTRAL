import uuid
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from tests.conftest import AuthPrueba

RUTAS_CARGA = (
    "/api/v1/documentos",
    "/api/v1/documentos/paquete",
    "/api/v1/documentos/lote-imagenes",
)

ROLES_NO_GESTOR = (
    "SUPERADMIN",
    "ADMINISTRADOR",
    "GERENTE",
    "SECRETARIA",
    "RESPONSABLE",
    "USUARIO",
)


@pytest.mark.parametrize("ruta", RUTAS_CARGA)
@pytest.mark.parametrize("rol", ROLES_NO_GESTOR)
def test_solo_gestores_pueden_ingresar_documentos(
    client_estricto: TestClient, auth_prueba: AuthPrueba, ruta: str, rol: str
) -> None:
    auth_prueba.contexto = replace(auth_prueba.contexto, rol=rol)
    if ruta.endswith("/lote-imagenes"):
        respuesta = client_estricto.post(
            ruta,
            files=[("archivos", ("prueba.jpg", b"imagen", "image/jpeg"))],
        )
    else:
        respuesta = client_estricto.post(
            ruta,
            files={"archivo": ("prueba.pdf", b"%PDF-1.7\\n", "application/pdf")},
        )
    assert respuesta.status_code == 403, respuesta.text


@pytest.mark.parametrize("ruta", RUTAS_CARGA)
def test_gestor_pasa_el_control_de_rol_de_carga(
    client_estricto: TestClient, auth_prueba: AuthPrueba, ruta: str
) -> None:
    auth_prueba.contexto = replace(
        auth_prueba.contexto,
        rol="GESTOR",
        gestor_id=uuid.uuid4(),
    )
    respuesta = client_estricto.post(ruta)
    # Sin archivo, la validación del endpoint debe responder 422; un 403
    # indicaría que el permiso de Gestor quedó bloqueado por error.
    assert respuesta.status_code == 422, respuesta.text
