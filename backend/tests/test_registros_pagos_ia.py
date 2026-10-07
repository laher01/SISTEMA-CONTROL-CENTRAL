from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Documento, PerfilExtraccion
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
    assert pago.status_code == 201, pago.text
    datos = pago.json()
    assert Decimal(datos["produccion_total"]) == Decimal("1500.00")
    assert Decimal(datos["bruto"]) == Decimal("22.50")
    assert Decimal(datos["adelantos"]) == Decimal("5.00")
    assert Decimal(datos["saldo"]) == Decimal("18.50")


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
    assert resultado["formato_documental"] == "OSE"
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
