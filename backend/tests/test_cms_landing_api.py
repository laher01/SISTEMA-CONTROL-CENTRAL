"""Seguridad de rutas globales CMS y validación de contenido no confiable."""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.routes.cms_landing import (
    BorradorCms,
    TransicionCms,
    consultar_cms,
    guardar_cms,
    transicionar_cms,
)
from app.services.cms_landing_core import EstadoEditorial
from app.services.cms_landing_validation import ContenidoCms

CONTENIDO = {
    "marca": "FACT CENTRAL",
    "etiqueta": "Soluciones",
    "titulo": "Control documental",
    "descripcion": "Expedientes organizados",
    "beneficiosTitulo": "Ventajas",
    "beneficios": [{"id": "expedientes", "titulo": "Orden", "descripcion": "Documentos ordenados"}],
    "planesTitulo": "Planes",
    "planesDescripcion": "Pendientes de aprobación",
    "registroTitulo": "Registro",
    "registroDescripcion": "Con autorización",
}


def auth(rol: str, *, cambio: bool = False):
    return SimpleNamespace(rol=rol, cambio_clave_obligatorio=cambio, cuenta_id=uuid4())


@pytest.mark.parametrize("rol", ["ADMINISTRADOR", "GERENTE", "RESPONSABLE", "GESTOR"])
def test_otros_roles_no_leen_ni_modifican_cms(rol: str) -> None:
    session = MagicMock()
    cuenta = auth(rol)
    with pytest.raises(HTTPException) as exc:
        consultar_cms(session, cuenta)
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException) as exc:
        guardar_cms(
            BorradorCms.model_validate({"version": 0, "contenido": CONTENIDO}),
            session,
            cuenta,
        )
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException) as exc:
        transicionar_cms(
            TransicionCms(version=1, destino=EstadoEditorial.PUBLICADO), session, cuenta
        )
    assert exc.value.status_code == 403
    session.execute.assert_not_called()
    session.commit.assert_not_called()


def test_superadmin_con_cambio_de_clave_pendiente_es_rechazado() -> None:
    session = MagicMock()
    with pytest.raises(HTTPException) as exc:
        consultar_cms(session, auth("SUPERADMIN", cambio=True))
    assert exc.value.status_code == 403
    session.execute.assert_not_called()


def test_backend_rechaza_html_e_identificadores_duplicados() -> None:
    with pytest.raises(ValidationError):
        ContenidoCms.model_validate({**CONTENIDO, "titulo": "<script>malicioso</script>"})
    with pytest.raises(ValidationError):
        ContenidoCms.model_validate(
            {
                **CONTENIDO,
                "beneficios": [CONTENIDO["beneficios"][0], CONTENIDO["beneficios"][0]],
            }
        )


def test_backend_rechaza_campos_desconocidos() -> None:
    with pytest.raises(ValidationError):
        ContenidoCms.model_validate({**CONTENIDO, "tenant_id": str(uuid4())})
