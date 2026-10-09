import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Documento, Expediente, Gestor, PerfilExtraccion
from app.services.aprendizaje_documental import (
    aplicar_perfiles_aprendidos,
    registrar_correccion_y_aprender,
)
from app.services.expedientes import obtener_tenant
from app.services.extraccion_campos import extraer_campos
from tests.conftest import AuthPrueba
from tests.xml import factura


def _subir_factura(client: TestClient, numero: str, importe: str) -> dict[str, object]:
    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": (numero + ".xml", factura(numero=numero, importe=importe))},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_registros_totalizan_y_filtran_por_emisor(
    client: TestClient,
) -> None:
    _subir_factura(client, "F001-00000091", "100.00")
    _subir_factura(client, "F001-00000092", "200.00")

    respuesta = client.get("/api/v1/registros")
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["total_registros"] == 2
    assert Decimal(datos["total_pen"]) == Decimal("300.00")
    assert Decimal(datos["total_usd"]) == Decimal("0")
    assert {fila["correlativo"] for fila in datos["filas"]} == {"91", "92"}
    assert all(fila["emisor_ruc"] == "20500000002" for fila in datos["filas"])
    assert all(fila["emisor_razon_social"] == "PROVEEDOR SAC" for fila in datos["filas"])

    filtrada = client.get("/api/v1/registros", params={"emisor": "PROVEEDOR"})
    assert filtrada.status_code == 200, filtrada.text
    assert filtrada.json()["total_registros"] == 2


def test_usuario_no_puede_eliminar_registro_por_defecto(client: TestClient) -> None:
    documento = _subir_factura(client, "F001-00000093", "150.00")
    respuesta = client.delete(f"/api/v1/expedientes/{documento['expediente_id']}")
    assert respuesta.status_code == 403


def test_pago_erp_calcula_produccion_adelanto_y_saldo(
    client: TestClient,
    auth_prueba: AuthPrueba,
) -> None:
    usuario_id = auth_prueba.contexto.usuario_id
    assert usuario_id is not None

    _subir_factura(client, "F001-00000094", "1000.00")
    _subir_factura(client, "F001-00000095", "500.00")

    auth_prueba.como_admin()

    plan = client.post(
        "/api/v1/pagos/planes",
        json={
            "usuario_id": str(usuario_id),
            "nombre": "Plan prueba",
            "porcentaje": "1.5",
            "vigencia_desde": "2026-09-01",
            "vigencia_hasta": None,
        },
    )
    assert plan.status_code == 201, plan.text

    adelanto = client.post(
        "/api/v1/pagos/adelantos",
        json={
            "usuario_id": str(usuario_id),
            "fecha": "2026-09-11",
            "moneda": "PEN",
            "monto": "5.00",
            "descripcion": "Prueba",
        },
    )
    assert adelanto.status_code == 201, adelanto.text

    pago = client.post(
        "/api/v1/pagos",
        json={
            "usuario_id": str(usuario_id),
            "periodo_desde": "2026-09-01",
            "periodo_hasta": "2026-09-30",
            "moneda": "PEN",
            "ajustes": "1.00",
            "fecha_programada": None,
        },
    )
    assert pago.status_code == 403
    assert "Responsable" in pago.json()["detail"]


def test_alerta_manual_llega_al_usuario_destinatario(
    client: TestClient,
    auth_prueba: AuthPrueba,
) -> None:
    usuario_id = auth_prueba.contexto.usuario_id
    assert usuario_id is not None

    auth_prueba.como_admin()
    creada = client.post(
        "/api/v1/mensajes-alerta",
        json={
            "expediente_id": None,
            "destinatario_usuario_id": str(usuario_id),
            "destinatario_gestor_id": None,
            "para_administracion": True,
            "asunto": "Revisar documento",
            "mensaje": "Falta sustento del expediente.",
        },
    )
    assert creada.status_code == 201, creada.text

    auth_prueba.como_usuario(usuario_id)
    bandeja = client.get("/api/v1/mensajes-alerta")
    assert bandeja.status_code == 200, bandeja.text
    assert [item["asunto"] for item in bandeja.json()] == ["Revisar documento"]


def test_detecta_ose_y_descarta_direccion_como_razon_social() -> None:
    texto = """FACTURA ELECTRONICA E001-00000111
    FACTURALAYA OSE
    JR. BUENOS AIRES PSTO 30 - 31 SN
    RUC EMISOR: 20538820050
    CLIENTE: INVERSIONES BORISO E.I.R.L. RUC RECEPTOR: 20602757111
    FECHA DE EMISION: 30/09/2026
    TOTAL: S/ 807.01"""
    resultado = extraer_campos(texto, "TEXTO_PDF", 1.0)
    assert resultado is not None
    assert resultado["formato_documental"] == "OSE_FACTURALAYA"
    campos = resultado["campos"]
    assert isinstance(campos, dict)
    assert campos["ruc_emisor"]["valor"] == "20538820050"
    assert "razon_social_emisor" not in campos
    assert campos["razon_social_receptor"]["valor"] == "INVERSIONES BORISO E.I.R.L."


def test_correccion_aprende_perfil_por_ruc_y_formato(
    session: Session,
) -> None:
    tenant = obtener_tenant(session, "pruebas-aprendizaje")
    documento = Documento(
        tenant_id=tenant.id,
        expediente_id=None,
        tipo_documento=None,
        estado="PENDIENTE_CLASIFICACION",
        sha256="a" * 64,
        nombre_original="factura.pdf",
        mime_type="application/pdf",
        tamano_bytes=100,
        ruta_storage="x/factura.pdf",
        datos_extraidos={
            "procesamiento_documental": {
                "extraccion_estructurada": {
                    "version": 3,
                    "formato_documental": "OSE",
                    "campos": {},
                }
            }
        },
        formato_origen="OSE",
        gestor_id=None,
        usuario_id=None,
    )
    session.add(documento)
    session.flush()

    registrar_correccion_y_aprender(
        session,
        documento,
        "ADMIN01",
        "ADMINISTRADOR",
        {
            "ruc_emisor": "20538820050",
            "razon_social_emisor": "EMPRESA CORRECTA S.A.C.",
        },
        "Corrección de prueba",
    )
    session.flush()

    perfil = session.scalar(
        select(PerfilExtraccion).where(
            PerfilExtraccion.tenant_id == tenant.id,
            PerfilExtraccion.ruc == "20538820050",
            PerfilExtraccion.formato == "OSE",
        )
    )
    assert perfil is not None

    procesamiento: dict[str, object] = {
        "extraccion_estructurada": {
            "version": 3,
            "formato_documental": "OSE",
            "campos": {
                "ruc_emisor": {
                    "valor": "20538820050",
                    "confianza": 0.90,
                }
            },
        }
    }
    aplicar_perfiles_aprendidos(session, documento, procesamiento)
    extraccion = procesamiento["extraccion_estructurada"]
    assert isinstance(extraccion, dict)
    campos = extraccion["campos"]
    assert isinstance(campos, dict)
    assert campos["razon_social_emisor"]["valor"] == "EMPRESA CORRECTA S.A.C."


def test_completa_dos_ruc_por_orden_cuando_no_hay_etiquetas() -> None:
    from app.services.automatizacion_documental import _completar_rucs

    campos: dict[str, str] = {}
    confianzas: dict[str, float] = {}
    candidatos = [
        ("20500000002", 0.90),
        ("20100000001", 0.90),
    ]

    _completar_rucs(campos, confianzas, candidatos, None)

    assert campos["ruc_emisor"] == "20500000002"
    assert campos["ruc_receptor"] == "20100000001"
    assert confianzas["ruc_emisor"] == 0.82
    assert confianzas["ruc_receptor"] == 0.82


def test_no_infiere_ruc_por_orden_si_hay_mas_de_dos_candidatos() -> None:
    from app.services.automatizacion_documental import _completar_rucs

    campos: dict[str, str] = {}
    confianzas: dict[str, float] = {}
    candidatos = [
        ("20500000002", 0.90),
        ("20100000001", 0.90),
        ("20600000003", 0.90),
    ]

    _completar_rucs(campos, confianzas, candidatos, None)

    assert "ruc_emisor" not in campos
    assert "ruc_receptor" not in campos


def test_admin_no_puede_programar_ni_eliminar_pago_usuario(
    client: TestClient,
    auth_prueba: AuthPrueba,
) -> None:
    usuario_id = auth_prueba.contexto.usuario_id
    assert usuario_id is not None
    auth_prueba.como_admin()
    intento = client.post(
        "/api/v1/pagos",
        json={
            "usuario_id": str(usuario_id),
            "periodo_desde": "2026-10-01",
            "periodo_hasta": "2026-10-31",
            "moneda": "PEN",
            "ajustes": "0",
            "fecha_programada": None,
        },
    )
    assert intento.status_code == 403
    from uuid import uuid4

    assert client.delete(f"/api/v1/pagos/{uuid4()}").status_code == 403


def test_registros_totalizan_por_receptor_dia_y_mes(client: TestClient) -> None:
    casos = [
        ("F001-00000101", "100.00", "2026-09-10", "20100000001"),
        ("F001-00000102", "200.00", "2026-09-10", "20100000002"),
        ("F001-00000103", "300.00", "2026-10-01", "20100000001"),
    ]
    for numero, importe, fecha, receptor in casos:
        respuesta = client.post(
            "/api/v1/documentos",
            files={
                "archivo": (
                    numero + ".xml",
                    factura(
                        numero=numero,
                        importe=importe,
                        fecha=fecha,
                        receptor=receptor,
                    ),
                )
            },
        )
        assert respuesta.status_code == 201, respuesta.text

    por_dia = client.get("/api/v1/registros", params={"dia": "2026-09-10"})
    assert por_dia.status_code == 200, por_dia.text
    assert por_dia.json()["total_registros"] == 2
    assert Decimal(por_dia.json()["total_pen"]) == Decimal("300.00")

    por_mes = client.get("/api/v1/registros", params={"mes": "2026-09"})
    assert por_mes.status_code == 200, por_mes.text
    assert por_mes.json()["total_registros"] == 2
    assert Decimal(por_mes.json()["total_pen"]) == Decimal("300.00")

    por_receptor = client.get(
        "/api/v1/registros",
        params={"receptor": "20100000001"},
    )
    assert por_receptor.status_code == 200, por_receptor.text
    assert por_receptor.json()["total_registros"] == 2
    assert Decimal(por_receptor.json()["total_pen"]) == Decimal("400.00")


def test_filtros_jerarquicos_por_rol(
    client: TestClient,
    session: Session,
    auth_prueba: AuthPrueba,
) -> None:
    usuario_id = auth_prueba.contexto.usuario_id
    assert usuario_id is not None

    documento = _subir_factura(client, "F001-00000104", "500.00")
    expediente = session.get(Expediente, uuid.UUID(str(documento["expediente_id"])))
    assert expediente is not None

    gestor = Gestor(
        tenant_id=auth_prueba.contexto.tenant_id,
        codigo="GEST-FILTRO",
        nombre="Gestor filtro",
        usuario_id=usuario_id,
        creado_por_cuenta_id=None,
    )
    session.add(gestor)
    session.flush()
    expediente.gestor_id = gestor.id
    session.commit()

    auth_prueba.como_gerente()
    opciones = client.get("/api/v1/registros/opciones")
    assert opciones.status_code == 200, opciones.text
    assert any(item["id"] == str(usuario_id) for item in opciones.json()["usuarios"])
    gestor_opcion = next(
        item for item in opciones.json()["gestores"] if item["id"] == str(gestor.id)
    )
    assert gestor_opcion["usuario_id"] == str(usuario_id)

    filtrado_gerencia = client.get(
        "/api/v1/registros",
        params={
            "usuario_id": str(usuario_id),
            "gestor_id": str(gestor.id),
        },
    )
    assert filtrado_gerencia.status_code == 200, filtrado_gerencia.text
    assert filtrado_gerencia.json()["total_registros"] == 1
    assert Decimal(filtrado_gerencia.json()["total_pen"]) == Decimal("500.00")

    auth_prueba.como_usuario(usuario_id)
    opciones_usuario = client.get("/api/v1/registros/opciones")
    assert opciones_usuario.status_code == 200, opciones_usuario.text
    assert opciones_usuario.json()["usuarios"] == []
    assert [item["id"] for item in opciones_usuario.json()["gestores"]] == [str(gestor.id)]

    filtrado_usuario = client.get(
        "/api/v1/registros",
        params={"gestor_id": str(gestor.id)},
    )
    assert filtrado_usuario.status_code == 200, filtrado_usuario.text
    assert filtrado_usuario.json()["total_registros"] == 1

    auth_prueba.como_gestor(gestor.id, usuario_id)
    propio = client.get("/api/v1/registros")
    assert propio.status_code == 200, propio.text
    assert propio.json()["total_registros"] == 1
    intento_cambiar = client.get(
        "/api/v1/registros",
        params={"gestor_id": str(gestor.id)},
    )
    assert intento_cambiar.status_code == 403


def test_cartera_clientes_suma_saldo_anterior_abonos_y_mes(
    client: TestClient,
    auth_prueba: AuthPrueba,
) -> None:
    respuesta_agosto = client.post(
        "/api/v1/documentos",
        files={
            "archivo": (
                "F001-00000201.xml",
                factura(numero="F001-00000201", importe="100.00", fecha="2026-08-20"),
            )
        },
    )
    assert respuesta_agosto.status_code == 201, respuesta_agosto.text

    respuesta_setiembre = client.post(
        "/api/v1/documentos",
        files={
            "archivo": (
                "F001-00000202.xml",
                factura(numero="F001-00000202", importe="200.00", fecha="2026-09-10"),
            )
        },
    )
    assert respuesta_setiembre.status_code == 201, respuesta_setiembre.text

    auth_prueba.como_admin()
    clientes = client.get("/api/v1/pagos/clientes")
    assert clientes.status_code == 200, clientes.text
    cliente = next(item for item in clientes.json() if item["codigo"] == "20100000001")

    abono = client.post(
        "/api/v1/pagos/clientes/abonos",
        json={
            "cliente_id": cliente["id"],
            "fecha": "2026-08-25",
            "moneda": "PEN",
            "monto": "40.00",
            "descripcion": "Abono agosto",
            "referencia": "OP-001",
        },
    )
    assert abono.status_code == 201, abono.text

    resumen = client.get(
        "/api/v1/pagos/clientes/resumen",
        params={"mes": "2026-09", "moneda": "PEN"},
    )
    assert resumen.status_code == 200, resumen.text
    datos = resumen.json()
    fila = next(item for item in datos["filas"] if item["cliente_id"] == cliente["id"])
    assert Decimal(fila["compras_mes"]) == Decimal("200.00")
    assert Decimal(fila["saldo_anterior"]) == Decimal("60.00")
    assert Decimal(fila["abonos_mes"]) == Decimal("0.00")
    assert Decimal(fila["saldo_total"]) == Decimal("260.00")

    retencion = client.patch(
        f"/api/v1/pagos/clientes/{cliente['id']}/agente-retencion",
        json={"agente_retencion": True},
    )
    assert retencion.status_code == 200, retencion.text
    assert retencion.json() is True


def test_pedido_gerencia_controla_solicitado_ejecutado_y_distribucion(
    client: TestClient,
    auth_prueba: AuthPrueba,
) -> None:
    usuario_id = auth_prueba.contexto.usuario_id
    assert usuario_id is not None

    _subir_factura(client, "F001-00000211", "100.00")
    _subir_factura(client, "F001-00000212", "200.00")

    auth_prueba.como_admin()
    clientes = client.get("/api/v1/pagos/clientes")
    assert clientes.status_code == 200, clientes.text
    cliente = next(item for item in clientes.json() if item["codigo"] == "20100000001")

    creado = client.post(
        "/api/v1/pagos/pedidos",
        json={
            "cliente_id": cliente["id"],
            "periodo_mes": "2026-09-01",
            "moneda": "PEN",
            "monto_solicitado": "1000.00",
            "modalidad": "POR_PEDIDO",
            "modo_distribucion": "AUTOMATICA",
            "observacion": "Pedido mensual",
        },
    )
    assert creado.status_code == 201, creado.text
    pedido = creado.json()
    assert Decimal(pedido["monto_solicitado"]) == Decimal("1000.00")
    assert Decimal(pedido["monto_ejecutado"]) == Decimal("300.00")
    assert Decimal(pedido["saldo_pendiente"]) == Decimal("700.00")
    assert Decimal(pedido["exceso"]) == Decimal("0.00")
    assert Decimal(pedido["avance_porcentaje"]) == Decimal("30.00")
    assert Decimal(pedido["monto_asignado"]) == Decimal("1000.00")
    assert len(pedido["asignaciones"]) == 1
    assert pedido["asignaciones"][0]["usuario_id"] == str(usuario_id)

    listado = client.get(
        "/api/v1/pagos/pedidos",
        params={"mes": "2026-09", "moneda": "PEN"},
    )
    assert listado.status_code == 200, listado.text
    assert len(listado.json()) == 1
    assert Decimal(listado.json()[0]["monto_ejecutado"]) == Decimal("300.00")


def test_porcentaje_produccion_predeterminado_aparece_en_pagos(
    client: TestClient,
    auth_prueba: AuthPrueba,
) -> None:
    usuario_id = auth_prueba.contexto.usuario_id
    assert usuario_id is not None

    auth_prueba.como_admin()
    actualizado = client.patch(
        f"/api/v1/miembros/{usuario_id}",
        json={"porcentaje_produccion": "2.2500"},
    )
    assert actualizado.status_code == 200, actualizado.text
    assert Decimal(actualizado.json()["porcentaje_produccion"]) == Decimal("2.2500")

    usuarios = client.get("/api/v1/pagos/usuarios")
    assert usuarios.status_code == 200, usuarios.text
    usuario = next(item for item in usuarios.json() if item["id"] == str(usuario_id))
    assert Decimal(usuario["porcentaje_produccion"]) == Decimal("2.2500")
