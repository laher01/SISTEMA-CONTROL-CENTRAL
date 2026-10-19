"""NEXUS lee estados documentales existentes sin activar OCR ni mutar expedientes."""

import uuid
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.models import Documento, Gestor, Miembro
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


def _documento_cartera(session, tenant_id, usuario_id, gestor_id, etiqueta: str) -> None:
    session.add(
        Documento(
            tenant_id=tenant_id,
            estado="RECIBIDO",
            sha256=uuid.uuid4().hex,
            nombre_original=f"{etiqueta}.xml",
            mime_type="application/xml",
            tamano_bytes=1,
            ruta_storage=f"test/{etiqueta}.xml",
            usuario_id=usuario_id,
            gestor_id=gestor_id,
        )
    )


def test_nexus_documentos_carteras_gestor_responsable_y_gerente(
    client: TestClient, session, auth_prueba
) -> None:
    """Prueba contra datos separados; gerencia no debe leer carteras ajenas."""
    tenant = auth_prueba.contexto.tenant_id
    usuario_asignado = auth_prueba.contexto.usuario_id
    responsable = Miembro(
        tenant_id=tenant,
        codigo="RESP-N1",
        nombre="Responsable N1",
        rol="RESPONSABLE",
        activo=True,
    )
    usuario_ajeno = Miembro(
        tenant_id=tenant,
        codigo="USR-AJENO-N1",
        nombre="Usuario ajeno N1",
        rol="USUARIO",
        activo=True,
    )
    gestor_asignado = Gestor(
        tenant_id=tenant,
        codigo="GEST-N1",
        nombre="Gestor N1",
        usuario_id=usuario_asignado,
    )
    gestor_ajeno = Gestor(
        tenant_id=tenant,
        codigo="GEST-AJ-N1",
        nombre="Gestor ajeno N1",
        usuario_id=usuario_ajeno.id,
    )
    session.add_all([responsable, usuario_ajeno])
    session.flush()
    asignado = session.get(Miembro, usuario_asignado)
    assert asignado is not None
    asignado.responsable_id = responsable.id
    session.add_all([gestor_asignado, gestor_ajeno])
    session.flush()
    _documento_cartera(session, tenant, usuario_asignado, gestor_asignado.id, "permitido")
    _documento_cartera(session, tenant, usuario_ajeno.id, gestor_ajeno.id, "ajeno")
    session.commit()

    consulta = {"mensaje": "¿Cómo van mis documentos?", "ruta": "/documentos"}

    auth_prueba.como_gestor(gestor_asignado.id, usuario_asignado)
    gestor = client.post("/api/v1/nexus/chat", json=consulta)
    assert gestor.status_code == 200, gestor.text
    assert gestor.json()["datos"]["documentos_por_estado"] == {"RECIBIDO": 1}

    auth_prueba.contexto = replace(
        auth_prueba.contexto,
        rol="RESPONSABLE",
        miembro_id=responsable.id,
        gestor_id=None,
        usuario_id=None,
    )
    resp = client.post("/api/v1/nexus/chat", json=consulta)
    assert resp.status_code == 200, resp.text
    assert resp.json()["datos"]["documentos_por_estado"] == {"RECIBIDO": 1}

    auth_prueba.como_gerente()
    gerencia = client.post("/api/v1/nexus/chat", json=consulta)
    assert gerencia.status_code == 200, gerencia.text
    # No se asignó ninguna de las carteras de prueba a esta gerencia.
    assert gerencia.json()["datos"]["documentos_por_estado"] == {}
