"""NEXUS lee estados documentales existentes sin activar OCR ni mutar expedientes."""

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.services.expedientes import obtener_tenant
from tests.xml import factura


def test_nexus_observa_documentos_sin_reprocesar(client: TestClient) -> None:
    respuesta = client.post(
        "/api/v1/nexus/chat",
        json={
            "mensaje": "¿Cómo van mis documentos?",
            "ruta": "/documentos",
            "expediente_id": None,
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["accion"] == "RESUMEN_DOCUMENTOS"
    assert datos["motor"] == "ESPECIALISTA_DOCUMENTOS"
    assert datos["seccion"] == "DOCUMENTOS"
    assert datos["llm_usado"] is False
    assert datos["fuentes"] == []
    assert "no he reprocesado ni cambiado archivos" in datos["respuesta"]
    assert "documentos_por_estado" in datos["datos"]


def test_nexus_no_inventa_documentos_al_consultar_vacio(client: TestClient) -> None:
    respuesta = client.post(
        "/api/v1/nexus/chat",
        json={
            "mensaje": "¿Qué documentos tengo?",
            "ruta": "/documentos",
            "expediente_id": None,
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["accion"] == "RESUMEN_DOCUMENTOS"


@pytest.mark.parametrize("rol", ["ADMINISTRADOR", "GERENTE", "USUARIO"])
def test_nexus_documentos_respeta_rol_activo_sin_datos(
    client: TestClient, auth_prueba, rol: str
) -> None:
    """La consulta de lectura admite roles autorizados sin inventar resultados."""
    if rol == "ADMINISTRADOR":
        auth_prueba.como_admin()
    elif rol == "GERENTE":
        auth_prueba.como_gerente()
    respuesta = client.post(
        "/api/v1/nexus/chat",
        json={"mensaje": "¿Cómo van mis documentos?", "ruta": "/documentos"},
    )
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["accion"] == "RESUMEN_DOCUMENTOS"
    assert datos["llm_usado"] is False
    assert "documentos_por_estado" in datos["datos"]


def test_nexus_resumen_documental_aislado_por_tenant(
    client: TestClient, session, settings, auth_prueba
) -> None:
    """Un tenant ajeno no recibe los estados del documento cargado al tenant original."""
    # La carga operativa pertenece al rol USUARIO; no se relaja RBAC.
    subido = client.post(
        "/api/v1/documentos",
        files={
            "archivo": (
                "F001-00009031.xml",
                factura(numero="F001-00009031", importe="1500.00", fecha="2026-10-01"),
            )
        },
    )
    assert subido.status_code == 201, subido.text
    consulta = {"mensaje": "¿Cómo van mis documentos?", "ruta": "/documentos"}
    origen = client.post("/api/v1/nexus/chat", json=consulta)
    assert origen.status_code == 200, origen.text
    estados_origen = origen.json()["datos"]["documentos_por_estado"]
    assert sum(estados_origen.values()) > 0

    tenant_ajeno = obtener_tenant(session, "tenant-aislado-nexus")
    session.commit()
    auth_prueba.contexto = replace(auth_prueba.contexto, tenant_id=tenant_ajeno.id)
    ajeno = client.post("/api/v1/nexus/chat", json=consulta)
    assert ajeno.status_code == 200, ajeno.text
    assert ajeno.json()["datos"]["documentos_por_estado"] == {}
    assert "F001-00009031" not in ajeno.text
