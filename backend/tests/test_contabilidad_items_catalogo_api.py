"""Permisos, aislamiento y reescaneo persistente de Contabilidad de Ítems."""

import hashlib
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.item_models import LineaComprobanteItem, ProductoItem
from app.models import Documento
from app.storage import AlmacenLocal
from tests.conftest import AuthPrueba

XML = b"""<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
<cac:InvoiceLine><cbc:InvoicedQuantity unitCode="NIU">2</cbc:InvoicedQuantity>
<cbc:LineExtensionAmount>10.00</cbc:LineExtensionAmount>
<cac:Item><cbc:Name>Producto de prueba</cbc:Name></cac:Item></cac:InvoiceLine></Invoice>"""


def _documento_xml(session: Session, settings, tenant_id) -> Documento:
    contenido = XML
    almacen = AlmacenLocal(settings.storage_dir)
    digest = hashlib.sha256(contenido).hexdigest()
    ruta = almacen.guardar(tenant_id, digest, contenido)
    documento = Documento(
        tenant_id=tenant_id,
        tipo_documento="FACT",
        estado="PENDIENTE_RELACION",
        sha256=digest,
        nombre_original="factura.xml",
        mime_type="text/xml",
        tamano_bytes=len(contenido),
        ruta_storage=ruta,
    )
    session.add(documento)
    session.flush()
    return documento


def _clave(descripcion: str, unidad: str) -> str:
    import hashlib

    from app.services.contabilidad_items_rules import texto_normalizado

    return hashlib.sha256(f"{texto_normalizado(descripcion)}|{unidad}".encode()).hexdigest()


def test_catalogo_y_categorias_solo_administrador_y_aislados_por_tenant(
    client: TestClient, session: Session, settings, auth_prueba: AuthPrueba
) -> None:
    auth_prueba.como_usuario(auth_prueba.usuario_id)
    denied = client.post("/api/v1/contabilidad-items/categorias", json={"nombre": "Bebidas"})
    assert denied.status_code == 403

    auth_prueba.como_admin()
    creada = client.post("/api/v1/contabilidad-items/categorias", json={"nombre": " Bebidas "})
    assert creada.status_code == 201, creada.text
    categoria_id = creada.json()["id"]
    duplicada = client.post("/api/v1/contabilidad-items/categorias", json={"nombre": "bebidas"})
    assert duplicada.status_code == 409

    creado = client.post(
        "/api/v1/contabilidad-items/catalogo",
        json={"descripcion": "Agua Mineral", "unidad_base": "niu", "categoria_id": categoria_id},
    )
    assert creado.status_code == 201, creado.text
    duplicado = client.post(
        "/api/v1/contabilidad-items/catalogo",
        json={"descripcion": "Agua Mineral", "unidad_base": "NIU", "categoria_id": categoria_id},
    )
    assert duplicado.status_code == 409
    producto = session.get(ProductoItem, UUID(creado.json()["id"]))
    assert producto is not None
    renombrada = client.patch(
        f"/api/v1/contabilidad-items/categorias/{categoria_id}", json={"nombre": "Bebidas frías"}
    )
    assert renombrada.status_code == 200, renombrada.text
    session.refresh(producto)
    assert producto.categoria == "Bebidas frías"
    assert producto.clasificacion_confirmada is True

    _documento_xml(session, settings, auth_prueba.contexto.tenant_id)
    # La API abre una sesión PostgreSQL independiente; publicar el fixture antes
    # de solicitar el trabajo para que el documento forme parte del lote.
    session.commit()
    trabajo_activo = client.post("/api/v1/contabilidad-items/reescaneo/trabajos")
    assert trabajo_activo.status_code == 201
    duplicado_activo = client.post("/api/v1/contabilidad-items/reescaneo/trabajos")
    assert duplicado_activo.status_code == 409


def test_reescaneo_por_lotes_no_reemplaza_lineas_clasificacion_o_documentos(
    client: TestClient,
    session: Session,
    settings,
    auth_prueba: AuthPrueba,
) -> None:
    auth_prueba.como_admin()
    tenant_id = auth_prueba.contexto.tenant_id
    documento = _documento_xml(session, settings, tenant_id)
    producto = ProductoItem(
        tenant_id=tenant_id,
        clave_catalogo=_clave("Clasificación manual", "NIU"),
        descripcion="Clasificación manual",
        categoria="Categoría confirmada",
        clasificacion_confirmada=True,
    )
    session.add(producto)
    session.flush()
    linea = LineaComprobanteItem(
        tenant_id=tenant_id,
        documento_id=documento.id,
        producto_id=producto.id,
        numero_linea=1,
        descripcion_original="Línea revisada por persona",
        cantidad=Decimal("9"),
        unidad="NIU",
        importe_linea=Decimal("99.00"),
    )
    session.add(linea)
    session.commit()

    preview = client.get("/api/v1/contabilidad-items/reescaneo/preview")
    assert preview.status_code == 200, preview.text
    assert preview.json()["facturas"] == 1
    assert preview.json()["con_lineas"] == 1
    assert preview.json()["por_formato"]["XML"] == 1

    creado = client.post("/api/v1/contabilidad-items/reescaneo/trabajos")
    assert creado.status_code == 201, creado.text
    trabajo_id = creado.json()["id"]
    lote = client.post(
        f"/api/v1/contabilidad-items/reescaneo/trabajos/{trabajo_id}/lote",
        params={"limite": 3},
    )
    assert lote.status_code == 200, lote.text
    assert lote.json()["procesados"] == 1
    assert lote.json()["estado"] == "COMPLETADO"
    assert lote.json()["lineas_nuevas"] == 0

    session.refresh(linea)
    session.refresh(producto)
    session.refresh(documento)
    assert session.scalar(select(func.count()).select_from(LineaComprobanteItem)) == 1
    assert linea.descripcion_original == "Línea revisada por persona"
    assert linea.cantidad == Decimal("9")
    assert producto.categoria == "Categoría confirmada"
    assert producto.clasificacion_confirmada is True
    assert documento.expediente_id is None
    assert documento.deleted_at is None


def test_reescaneo_no_expone_trabajos_de_otro_tenant(
    client: TestClient, session: Session, auth_prueba: AuthPrueba
) -> None:
    from app.item_models import TrabajoReescaneoItems
    from app.models import Tenant

    auth_prueba.como_admin()
    otro = Tenant(nombre=f"catalogo_ajeno_{uuid4().hex[:8]}")
    session.add(otro)
    session.flush()
    trabajo = TrabajoReescaneoItems(
        tenant_id=otro.id,
        solicitado_por_cuenta_id=auth_prueba.contexto.cuenta_id,
        estado="COMPLETADO",
    )
    session.add(trabajo)
    session.commit()
    resultado = client.get(f"/api/v1/contabilidad-items/reescaneo/trabajos/{trabajo.id}")
    assert resultado.status_code == 404


def test_lote_fuera_de_limite_no_se_ejecuta(client: TestClient, auth_prueba: AuthPrueba) -> None:
    auth_prueba.como_admin()
    respuesta = client.post(
        f"/api/v1/contabilidad-items/reescaneo/trabajos/{uuid4()}/lote",
        params={"limite": 4},
    )
    assert respuesta.status_code == 422


def test_reescaneo_rechaza_original_con_hash_distinto(
    client: TestClient,
    session: Session,
    settings,
    auth_prueba: AuthPrueba,
) -> None:
    auth_prueba.como_admin()
    documento = _documento_xml(session, settings, auth_prueba.contexto.tenant_id)
    documento.sha256 = "b" * 64
    session.commit()
    trabajo = client.post("/api/v1/contabilidad-items/reescaneo/trabajos")
    assert trabajo.status_code == 201, trabajo.text
    resultado = client.post(
        f"/api/v1/contabilidad-items/reescaneo/trabajos/{trabajo.json()['id']}/lote"
    )
    assert resultado.status_code == 200, resultado.text
    assert resultado.json()["errores"] == 1
    assert resultado.json()["lineas_nuevas"] == 0
    assert session.scalar(select(func.count()).select_from(LineaComprobanteItem)) == 0


def test_reescaneo_ubl_agrega_lineas_una_vez_y_es_idempotente(
    client: TestClient,
    session: Session,
    settings,
    auth_prueba: AuthPrueba,
) -> None:
    auth_prueba.como_admin()
    _documento_xml(session, settings, auth_prueba.contexto.tenant_id)
    # No depender de StaticPool/SQLite: CI usa sesiones PostgreSQL separadas.
    session.commit()
    for lineas_esperadas in (1, 0):
        trabajo = client.post("/api/v1/contabilidad-items/reescaneo/trabajos")
        assert trabajo.status_code == 201, trabajo.text
        resultado = client.post(
            f"/api/v1/contabilidad-items/reescaneo/trabajos/{trabajo.json()['id']}/lote"
        )
        assert resultado.status_code == 200, resultado.text
        assert resultado.json()["lineas_nuevas"] == lineas_esperadas
        assert resultado.json()["estado"] == "COMPLETADO"
    assert session.scalar(select(func.count()).select_from(LineaComprobanteItem)) == 1
