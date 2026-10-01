import io
from datetime import date

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.api.routes import documentos as documentos_routes
from app.services.procesamiento_documental import ResultadoProcesamiento
from tests.conftest import Reloj
from tests.xml import RECEPTOR, factura, guia


def subir(client: TestClient, nombre: str, contenido: bytes, **form: str) -> dict[str, object]:
    respuesta = client.post("/api/v1/documentos", files={"archivo": (nombre, contenido)}, data=form)
    assert respuesta.status_code == 201, respuesta.text
    datos: dict[str, object] = respuesta.json()
    return datos


def expediente(client: TestClient, expediente_id: object) -> dict[str, object]:
    respuesta = client.get(f"/api/v1/expedientes/{expediente_id}")
    assert respuesta.status_code == 200, respuesta.text
    datos: dict[str, object] = respuesta.json()
    return datos


def pdf_vacio() -> bytes:
    salida = io.BytesIO()
    escritor = PdfWriter()
    escritor.add_blank_page(width=100, height=100)
    escritor.write(salida)
    return salida.getvalue()


def alertas_abiertas(detalle: dict[str, object]) -> set[str]:
    alertas = detalle["alertas"]
    assert isinstance(alertas, list)
    return {a["tipo"] for a in alertas if not a["resuelta"]}


def autorizar_receptor(client: TestClient, **extra: bool) -> None:
    empresas = client.get("/api/v1/empresas").json()
    receptor = next(e for e in empresas if e["ruc"] == RECEPTOR)
    respuesta = client.patch(
        f"/api/v1/empresas/{receptor['id']}", json={"autorizada": True, **extra}
    )
    assert respuesta.status_code == 200, respuesta.text


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_factura_xml_crea_expediente_con_alertas(client: TestClient) -> None:
    documento = subir(client, "F001-123.xml", factura())
    assert documento["tipo_documento"] == "FACT"
    assert documento["estado"] == "RELACIONADO"
    assert len(str(documento["sha256"])) == 64

    detalle = expediente(client, documento["expediente_id"])
    assert detalle["estado"] == "NARANJA"
    assert detalle["pendiente_aprobacion"] is True
    assert detalle["faltantes"] == ["GRR", "VCHR"]
    assert detalle["fecha_limite"] == "2026-10-07"
    assert alertas_abiertas(detalle) == {"BANCARIZACION_SIN_VOUCHER", "RECEPTOR_NO_AUTORIZADO"}


def test_duplicado_por_hash_y_no_por_nombre(client: TestClient) -> None:
    subir(client, "a.xml", factura())
    respuesta = client.post("/api/v1/documentos", files={"archivo": ("otro_nombre.xml", factura())})
    assert respuesta.status_code == 409
    subir(client, "a.xml", factura(numero="F001-00000124"))


def test_expediente_completo_queda_verde(client: TestClient) -> None:
    doc_factura = subir(client, "f.xml", factura())
    expediente_id = doc_factura["expediente_id"]

    doc_guia = subir(client, "g.xml", guia())
    assert doc_guia["tipo_documento"] == "GRR"
    assert doc_guia["expediente_id"] == expediente_id

    voucher = subir(client, "voucher.pdf", b"%PDF-1.7 voucher")
    assert voucher["estado"] == "PENDIENTE_CLASIFICACION"
    respuesta = client.post(
        f"/api/v1/documentos/{voucher['id']}/vincular",
        json={"expediente_id": expediente_id, "tipo_documento": "VCHR"},
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "RELACIONADO"

    autorizar_receptor(client)
    detalle = expediente(client, expediente_id)
    assert detalle["estado"] == "VERDE"
    assert detalle["pendiente_aprobacion"] is False
    assert detalle["faltantes"] == []
    assert alertas_abiertas(detalle) == set()


def test_agente_retencion_sin_constancia_queda_amarillo(client: TestClient) -> None:
    doc_factura = subir(client, "f.xml", factura())
    expediente_id = str(doc_factura["expediente_id"])
    subir(client, "g.xml", guia())
    subir(client, "v.jpg", b"\xff\xd8 voucher", tipo_documento="VCHR", expediente_id=expediente_id)
    autorizar_receptor(client, agente_retencion=True)

    detalle = expediente(client, expediente_id)
    assert detalle["estado"] == "AMARILLO"
    assert alertas_abiertas(detalle) == {"RETENCION_PENDIENTE"}

    subir(client, "ret.pdf", b"%PDF ret", tipo_documento="RET", expediente_id=expediente_id)
    assert expediente(client, expediente_id)["estado"] == "VERDE"


def test_expediente_vencido_queda_rojo(client: TestClient, reloj: Reloj) -> None:
    doc_factura = subir(client, "f.xml", factura(importe="150.00"))
    expediente_id = doc_factura["expediente_id"]
    autorizar_receptor(client)

    reloj.hoy = date(2026, 10, 8)
    assert client.post("/api/v1/expedientes/recalcular").json() == {"actualizados": 1}

    detalle = expediente(client, expediente_id)
    assert detalle["estado"] == "ROJO"
    assert alertas_abiertas(detalle) == {"EXPEDIENTE_VENCIDO"}


def test_crear_expediente_manual_rhe_sin_guia(client: TestClient) -> None:
    datos = {
        "receptor": {"ruc": RECEPTOR, "razon_social": "CLIENTE SAC"},
        "emisor": {"ruc": "10456789012", "razon_social": "JUAN PEREZ"},
        "tipo_comprobante": "RHE",
        "serie": "E001",
        "correlativo": "00000015",
        "fecha_emision": "2026-09-05",
        "importe_total": "1200.00",
    }
    respuesta = client.post("/api/v1/expedientes", json=datos)
    assert respuesta.status_code == 201, respuesta.text
    creado = respuesta.json()
    assert creado["correlativo"] == "15"
    assert creado["requiere_guia"] is False

    detalle = expediente(client, creado["id"])
    assert detalle["faltantes"] == ["RHE", "VCHR"]
    assert client.post("/api/v1/expedientes", json=datos).status_code == 409


def test_alertas_y_dashboard(client: TestClient) -> None:
    subir(client, "f1.xml", factura())
    subir(client, "f2.xml", factura(numero="F001-00000200", importe="800.00", moneda="USD"))
    subir(client, "suelto.png", b"\x89PNG foto")

    alertas = client.get("/api/v1/alertas", params={"tipo": "BANCARIZACION_SIN_VOUCHER"})
    assert len(alertas.json()) == 2

    resumen = client.get("/api/v1/dashboard/resumen").json()
    assert resumen["expedientes_total"] == 2
    assert resumen["por_estado"]["NARANJA"] == 2
    assert resumen["pendientes_aprobacion"] == 2
    assert resumen["alertas_abiertas"]["RECEPTOR_NO_AUTORIZADO"] == 2
    assert resumen["documentos_pendientes"]["PENDIENTE_CLASIFICACION"] == 1
    montos = {m["moneda"]: m for m in resumen["montos"]}
    assert montos["PEN"]["bancarizable"] == "2500.00"
    assert montos["USD"]["bancarizable"] == "800.00"


def test_validaciones_de_carga(client: TestClient) -> None:
    vacio = client.post("/api/v1/documentos", files={"archivo": ("x.pdf", b"")})
    assert vacio.status_code == 422
    sin_tipo = client.post(
        "/api/v1/documentos",
        files={"archivo": ("x.pdf", b"%PDF")},
        data={"expediente_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert sin_tipo.status_code == 422
    inexistente = client.post(
        "/api/v1/documentos",
        files={"archivo": ("x.pdf", b"%PDF")},
        data={"expediente_id": "00000000-0000-0000-0000-000000000000", "tipo_documento": "VCHR"},
    )
    assert inexistente.status_code == 404
    ubl_roto = client.post(
        "/api/v1/documentos", files={"archivo": ("f.xml", factura(emisor="123"))}
    )
    assert ubl_roto.status_code == 422


def test_descarga_del_original_sin_modificar(client: TestClient) -> None:
    contenido = b"%PDF-1.7 voucher original"
    documento = subir(client, "voucher ñ.pdf", contenido)
    respuesta = client.get(f"/api/v1/documentos/{documento['id']}/archivo")
    assert respuesta.status_code == 200
    assert respuesta.content == contenido
    assert "voucher%20%C3%B1.pdf" in respuesta.headers["content-disposition"]
    assert (
        client.get("/api/v1/documentos/00000000-0000-0000-0000-000000000000/archivo").status_code
        == 404
    )


def test_descarga_de_tipos_no_seguros_como_adjunto(client: TestClient) -> None:
    respuesta = client.post(
        "/api/v1/documentos",
        files={"archivo": ("x.html", b"<script>alert(1)</script>", "text/html")},
    )
    assert respuesta.status_code == 201
    descarga = client.get(f"/api/v1/documentos/{respuesta.json()['id']}/archivo")
    assert descarga.headers["content-type"] == "application/octet-stream"
    assert descarga.headers["content-disposition"].startswith("attachment;")


def test_busqueda_de_expedientes(client: TestClient) -> None:
    subir(client, "a.xml", factura(numero="F001-00000123"))
    subir(client, "b.xml", factura(numero="F002-00000777", emisor="20600000003"))

    def numeros(buscar: str) -> list[str]:
        respuesta = client.get("/api/v1/expedientes", params={"buscar": buscar})
        assert respuesta.status_code == 200
        return sorted(f"{e['serie']}-{e['correlativo']}" for e in respuesta.json())

    assert numeros("f002-00000777") == ["F002-777"]
    assert numeros("F002-777") == ["F002-777"]
    assert numeros("20600000003") == ["F002-777"]
    assert numeros("proveedor") == ["F001-123", "F002-777"]
    assert numeros("100%") == []


def test_procesar_pdf_conserva_resultado_verificable(client: TestClient) -> None:
    documento = subir(client, "escaneo.pdf", pdf_vacio())
    respuesta = client.post(f"/api/v1/documentos/{documento['id']}/procesar")
    assert respuesta.status_code == 200, respuesta.text
    procesamiento = respuesta.json()["datos_extraidos"]["procesamiento_documental"]
    assert procesamiento["metodo"] == "TEXTO_PDF"
    assert procesamiento["motor"] == "pypdf"
    assert procesamiento["paginas"] == 1
    assert procesamiento["requiere_ocr"] is True


def test_procesar_archivo_no_soportado_no_pierde_original(client: TestClient) -> None:
    documento = subir(client, "nota.txt", b"texto simple")
    respuesta = client.post(f"/api/v1/documentos/{documento['id']}/procesar")
    assert respuesta.status_code == 422
    descarga = client.get(f"/api/v1/documentos/{documento['id']}/archivo")
    assert descarga.content == b"texto simple"


def test_sugiere_relacion_por_evidencia_sin_vincular(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    factura_subida = subir(client, "factura.xml", factura())
    pendiente = subir(client, "voucher.png", b"\x89PNG\r\n\x1a\ncontenido")
    texto = "PAGO DE F001-00000123 RUC 20500000002 CLIENTE 20100000001 TOTAL 2,500.00"
    monkeypatch.setattr(
        documentos_routes,
        "procesar",
        lambda *_: ResultadoProcesamiento(
            texto=texto,
            metodo="OCR_IMAGEN",
            motor="prueba",
            paginas=1,
            confianza=0.95,
        ),
    )
    procesado = client.post(f"/api/v1/documentos/{pendiente['id']}/procesar")
    assert procesado.status_code == 200
    sugerencias = client.get(f"/api/v1/documentos/{pendiente['id']}/relaciones-sugeridas").json()
    assert len(sugerencias) == 1
    assert sugerencias[0]["expediente"]["id"] == factura_subida["expediente_id"]
    assert sugerencias[0]["puntaje"] == 1.0
    assert "Comprobante F001-123" in sugerencias[0]["evidencias"]
    detalle = expediente(client, factura_subida["expediente_id"])
    assert all(documento["id"] != pendiente["id"] for documento in detalle["documentos"])
