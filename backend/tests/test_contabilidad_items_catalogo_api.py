"""Permisos, aislamiento y reescaneo persistente de Contabilidad de Ítems."""

import hashlib
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.item_models import LineaComprobanteItem, ProductoItem, TrabajoReescaneoItems
from app.models import Documento, Empresa, Expediente, Miembro
from app.security import ContextoAcceso
from app.services.contabilidad_items_ubl import registrar_items_ubl
from app.storage import AlmacenLocal
from tests.conftest import AuthPrueba

XML = b"""<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
<cac:InvoiceLine><cbc:InvoicedQuantity unitCode="NIU">2</cbc:InvoicedQuantity>
<cbc:LineExtensionAmount>10.00</cbc:LineExtensionAmount>
<cac:Item><cbc:Name>Producto de prueba</cbc:Name></cac:Item></cac:InvoiceLine></Invoice>"""


def _documento_xml(
    session: Session,
    settings,
    tenant_id,
    documento_id: UUID | None = None,
    contenido: bytes = XML,
) -> Documento:
    almacen = AlmacenLocal(settings.storage_dir)
    digest = hashlib.sha256(contenido).hexdigest()
    ruta = almacen.guardar(tenant_id, digest, contenido)
    documento = Documento(
        id=documento_id,
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


def test_catalogo_lectura_por_roles_y_edicion_solo_administrador_aislada_por_tenant(
    client: TestClient, session: Session, settings, auth_prueba: AuthPrueba
) -> None:
    auth_prueba.como_usuario(auth_prueba.usuario_id)
    categorias_lectura = client.get("/api/v1/contabilidad-items/categorias")
    catalogo_lectura = client.get("/api/v1/contabilidad-items/catalogo")
    assert categorias_lectura.status_code == 200
    assert catalogo_lectura.status_code == 200
    assert catalogo_lectura.json() == {"total": 0, "items": []}
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


def test_reescaneo_cubre_roles_operativos_y_confirmar_categoria_en_cartera(
    client: TestClient,
    session: Session,
    settings,
    auth_prueba: AuthPrueba,
) -> None:
    tenant_id = auth_prueba.contexto.tenant_id
    gerente = Miembro(
        tenant_id=tenant_id,
        codigo="GER-RESCAN",
        nombre="Gerente de prueba",
        rol="GERENTE",
    )
    responsable = Miembro(
        tenant_id=tenant_id,
        codigo="RESP-RESCAN",
        nombre="Responsable de prueba",
        rol="RESPONSABLE",
    )
    usuario = session.get(Miembro, auth_prueba.usuario_id)
    assert usuario is not None
    session.add_all([gerente, responsable])
    session.flush()
    usuario.responsable_id = responsable.id
    emisor = Empresa(tenant_id=tenant_id, ruc="20600000001", razon_social="Proveedor prueba")
    receptor = Empresa(tenant_id=tenant_id, ruc="20600000002", razon_social="Cliente prueba")
    session.add_all([emisor, receptor])
    session.flush()
    expediente = Expediente(
        tenant_id=tenant_id,
        gerente_id=gerente.id,
        usuario_id=auth_prueba.usuario_id,
        gestor_id=auth_prueba.gestor_id,
        emisor_id=emisor.id,
        receptor_id=receptor.id,
        tipo_comprobante="FACT",
        serie="F001",
        correlativo="500",
        fecha_emision=date(2026, 11, 1),
        moneda="PEN",
        importe_total=Decimal("10.00"),
    )
    session.add(expediente)
    session.flush()
    documento = _documento_xml(session, settings, tenant_id)
    documento.expediente_id = expediente.id
    session.commit()
    assert usuario.responsable_id == responsable.id

    roles = [
        ("ADMINISTRADOR", None, None, None, "ADMIN-TEST"),
        ("SECRETARIA", None, None, None, "SECRETARIA-TEST"),
        ("GERENTE", gerente.id, None, None, "GERENTE-TEST"),
        ("RESPONSABLE", responsable.id, None, None, "RESPONSABLE-TEST"),
        ("USUARIO", usuario.id, usuario.id, None, "USUARIO-TEST"),
        ("GESTOR", None, usuario.id, auth_prueba.gestor_id, "GESTOR-TEST"),
    ]
    trabajo_administrador_id = None
    for rol, miembro_id, usuario_id, gestor_id, codigo in roles:
        auth_prueba.contexto = ContextoAcceso(
            cuenta_id=auth_prueba.contexto.cuenta_id,
            tenant_id=tenant_id,
            rol=rol,
            miembro_id=miembro_id,
            gestor_id=gestor_id,
            usuario_id=usuario_id,
            codigo=codigo,
            nombre=codigo,
            cambio_clave_obligatorio=False,
        )
        preview = client.get("/api/v1/contabilidad-items/reescaneo/preview")
        assert preview.status_code == 200, f"{rol}: {preview.text}"
        assert preview.json()["por_tipo"]["FACT"] == 1, f"{rol}: {preview.json()}"
        categorias = client.get("/api/v1/contabilidad-items/categorias")
        catalogo = client.get("/api/v1/contabilidad-items/catalogo")
        assert categorias.status_code == 200, f"{rol}: {categorias.text}"
        assert catalogo.status_code == 200, f"{rol}: {catalogo.text}"
        trabajo = client.post("/api/v1/contabilidad-items/reescaneo/trabajos")
        assert trabajo.status_code == 201, f"{rol}: {trabajo.text}"
        trabajo_id = trabajo.json()["id"]
        if rol == "ADMINISTRADOR":
            trabajo_administrador_id = trabajo_id
        lote = client.post(f"/api/v1/contabilidad-items/reescaneo/trabajos/{trabajo_id}/lote")
        assert lote.status_code == 200, f"{rol}: {lote.text}"
        resultado = client.get(
            f"/api/v1/contabilidad-items/reescaneo/trabajos/{trabajo_id}/resultado"
        )
        assert resultado.status_code == 200, f"{rol}: {resultado.text}"
        assert resultado.json()["ultima_factura"]["comprobante"] == "F001-500"
        assert resultado.json()["items"][0]["categoria_sugerida"] == "POR_CATEGORIZAR"

    linea = session.scalar(select(LineaComprobanteItem))
    assert linea is not None
    auth_prueba.contexto = ContextoAcceso(
        cuenta_id=auth_prueba.contexto.cuenta_id,
        tenant_id=tenant_id,
        rol="USUARIO",
        miembro_id=usuario.id,
        gestor_id=None,
        usuario_id=usuario.id,
        codigo="USUARIO-TEST",
        nombre="Usuario de prueba",
        cambio_clave_obligatorio=False,
    )
    assert trabajo_administrador_id is not None
    assert (
        client.get(
            f"/api/v1/contabilidad-items/reescaneo/trabajos/{trabajo_administrador_id}/resultado"
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/contabilidad-items/reescaneo/trabajos/{trabajo_administrador_id}/lote"
        ).status_code
        == 404
    )
    clasificada = client.patch(
        f"/api/v1/contabilidad-items/lineas/{linea.id}/clasificacion",
        json={"categoria": "Artículos de prueba", "descripcion": "Descripción larga autorizada"},
    )
    assert clasificada.status_code == 200, clasificada.text
    assert clasificada.json()["categoria"] == "Artículos de prueba"
    assert clasificada.json()["descripcion"] == "Descripción larga autorizada"
    assert session.scalar(select(func.count()).select_from(LineaComprobanteItem)) == 1


def test_reescaneo_avanza_si_el_documento_actual_dejo_de_ser_elegible(
    client: TestClient,
    session: Session,
    settings,
    auth_prueba: AuthPrueba,
) -> None:
    auth_prueba.como_admin()
    tenant_id = auth_prueba.contexto.tenant_id
    primero = _documento_xml(session, settings, tenant_id, UUID(int=10))
    no_disponible = _documento_xml(
        session, settings, tenant_id, UUID(int=20), contenido=XML + b"\n"
    )
    siguiente = _documento_xml(session, settings, tenant_id, UUID(int=30), contenido=XML + b"  ")
    session.commit()

    iniciado = client.post("/api/v1/contabilidad-items/reescaneo/trabajos")
    assert iniciado.status_code == 201, iniciado.text
    trabajo_id = UUID(iniciado.json()["id"])
    trabajo = session.get(TrabajoReescaneoItems, trabajo_id)
    assert trabajo is not None
    trabajo.cursor_documento_id = primero.id
    trabajo.documento_actual_id = no_disponible.id
    trabajo.documento_actual_started_at = datetime.now(UTC) - timedelta(hours=1)
    trabajo.procesados = 1
    no_disponible.deleted_at = datetime.now(UTC)
    session.commit()

    lote = client.post(f"/api/v1/contabilidad-items/reescaneo/trabajos/{trabajo_id}/lote")
    assert lote.status_code == 200, lote.text
    assert lote.json()["estado"] == "COMPLETADO_CON_OBSERVACIONES"
    assert lote.json()["procesados"] == 3
    assert lote.json()["errores"] == 1
    assert (
        session.scalar(
            select(func.count())
            .select_from(LineaComprobanteItem)
            .where(LineaComprobanteItem.documento_id == siguiente.id)
        )
        == 1
    )


def test_reescaneo_rhe_extrae_concepto_y_lo_marca_para_revision(
    client: TestClient,
    session: Session,
    settings,
    auth_prueba: AuthPrueba,
    monkeypatch,
) -> None:
    import app.api.routes.contabilidad_items_catalogo as catalogo_route

    auth_prueba.como_admin()
    tenant_id = auth_prueba.contexto.tenant_id
    contenido = b"%PDF-recibo-honorarios"
    almacen = AlmacenLocal(settings.storage_dir)
    digest = hashlib.sha256(contenido).hexdigest()
    ruta = almacen.guardar(tenant_id, digest, contenido)
    documento = Documento(
        tenant_id=tenant_id,
        tipo_documento="RHE",
        estado="RELACIONADO",
        sha256=digest,
        nombre_original="recibo.pdf",
        mime_type="application/pdf",
        tamano_bytes=len(contenido),
        ruta_storage=ruta,
    )
    session.add(documento)
    session.commit()
    texto = """RECIBO POR HONORARIOS ELECTRÓNICO
Por concepto de SERVICIO DE ASESORIA Y DOCUMENTACION-PAITA
Inciso A DEL ARTICULO 33
Total por honorarios:
1,500.00
Retención (8 %) IR:
0.00
Total Neto Recibido:
1,500.00"""
    monkeypatch.setattr(
        catalogo_route, "procesar_con_cache", lambda *args, **kwargs: {"texto": texto}
    )
    trabajo = client.post("/api/v1/contabilidad-items/reescaneo/trabajos")
    assert trabajo.status_code == 201, trabajo.text
    lote = client.post(f"/api/v1/contabilidad-items/reescaneo/trabajos/{trabajo.json()['id']}/lote")
    assert lote.status_code == 200, lote.text
    linea = session.scalar(select(LineaComprobanteItem))
    assert linea is not None
    assert linea.descripcion_original == "SERVICIO DE ASESORIA Y DOCUMENTACION-PAITA"
    assert linea.importe_linea == Decimal("1500.00")
    assert lote.json()["lineas_nuevas"] == 1


def test_combinar_conserva_variante_y_precio(client, session, settings, auth_prueba):
    auth_prueba.como_admin()
    tenant_id = auth_prueba.contexto.tenant_id
    principal = ProductoItem(
        tenant_id=tenant_id,
        clave_catalogo=_clave("Producto principal", "NIU"),
        descripcion="Producto principal",
        unidad_base="NIU",
    )
    session.add(principal)
    contenido = XML.replace(
        b"</cac:InvoiceLine>",
        b"<cac:Price><cbc:PriceAmount>5.001</cbc:PriceAmount></cac:Price></cac:InvoiceLine>",
    )
    documento = _documento_xml(session, settings, tenant_id, contenido=contenido)
    assert registrar_items_ubl(session, tenant_id, documento.id, contenido) == 1
    session.commit()
    variante = session.scalar(
        select(ProductoItem).where(ProductoItem.descripcion == "Producto de prueba")
    )
    respuesta = client.patch(
        f"/api/v1/contabilidad-items/catalogo/{variante.id}",
        json={"combinar_en": str(principal.id)},
    )
    assert respuesta.status_code == 200, respuesta.text
    session.expire_all()
    assert variante.combinado_en_id == principal.id
    nueva = _documento_xml(session, settings, tenant_id, contenido=contenido + b"\n")
    assert registrar_items_ubl(session, tenant_id, nueva.id, contenido) == 1
    session.flush()
    lineas = list(session.scalars(select(LineaComprobanteItem)))
    assert len(lineas) == 2
    assert all(linea.producto_id == principal.id for linea in lineas)
    assert all(linea.precio_unitario == Decimal("5.001") for linea in lineas)
