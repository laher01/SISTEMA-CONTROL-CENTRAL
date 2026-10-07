import io
from datetime import date

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from app.api.routes import documentos as documentos_routes
from app.core.config import Settings
from app.models import Expediente
from app.services import procesamiento_documental
from app.services.procesamiento_documental import ResultadoProcesamiento, sugerir_tipo
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
    doc_factura = subir(client, "f.xml", factura(importe="2500.00"))
    expediente_id = doc_factura["expediente_id"]
    autorizar_receptor(client)

    reloj.hoy = date(2026, 10, 8)
    assert client.post("/api/v1/expedientes/recalcular").json() == {"actualizados": 1}

    detalle = expediente(client, expediente_id)
    assert detalle["estado"] == "ROJO"
    assert alertas_abiertas(detalle) == {
        "BANCARIZACION_SIN_VOUCHER",
        "EXPEDIENTE_VENCIDO",
    }


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
    assert detalle["faltantes"] == ["RHE"]
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


def test_procesar_pdf_conserva_resultado_verificable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(procesamiento_documental.shutil, "which", lambda _: None)
    documento = subir(client, "escaneo.pdf", pdf_vacio())
    respuesta = client.post(f"/api/v1/documentos/{documento['id']}/procesar")
    assert respuesta.status_code == 200, respuesta.text
    procesamiento = respuesta.json()["datos_extraidos"]["procesamiento_documental"]
    assert procesamiento["metodo"] == "TEXTO_PDF"
    assert procesamiento["motor"] == "pypdf"
    assert procesamiento["paginas"] == 1
    assert procesamiento["requiere_ocr"] is True


def test_pdf_completo_crea_expediente_automaticamente(
    client: TestClient, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.tenant_ruc = RECEPTOR
    texto = """FACTURA ELECTRÓNICA F001-00000123
    RUC EMISOR: 20500000002 CLIENTE RUC: 20100000001
    Fecha de emisión: 17/09/2026 Moneda: SOLES TOTAL S/ 2,500.40"""
    monkeypatch.setattr(
        documentos_routes,
        "procesar",
        lambda *_: ResultadoProcesamiento(
            texto=texto,
            metodo="TEXTO_PDF",
            motor="prueba",
            paginas=1,
            confianza=1.0,
            sugerencia=sugerir_tipo(texto),
        ),
    )

    documento = subir(client, "factura.pdf", pdf_vacio())

    assert documento["estado"] == "RELACIONADO"
    assert documento["tipo_documento"] == "FACT"
    assert documento["expediente_id"] is not None
    datos = documento["datos_extraidos"]
    assert datos["extraccion_confirmada"]["origen"] == "AUTOMATICA"
    assert datos["automatizacion_documental"]["estado"] == "COMPLETADO"
    detalle = expediente(client, documento["expediente_id"])
    assert detalle["serie"] == "F001"
    assert detalle["correlativo"] == "123"
    assert detalle["receptor"]["ruc"] == RECEPTOR

    segunda = subir(client, "misma-factura-otra-representacion.pdf", pdf_vacio() + b"segunda")
    assert segunda["expediente_id"] == documento["expediente_id"]
    assert len(expediente(client, documento["expediente_id"])["documentos"]) == 2


def test_pdf_incompleto_queda_en_revision_con_motivo(
    client: TestClient, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.tenant_ruc = RECEPTOR
    texto = "FACTURA ELECTRÓNICA F001-00000123"
    monkeypatch.setattr(
        documentos_routes,
        "procesar",
        lambda *_: ResultadoProcesamiento(
            texto=texto,
            metodo="TEXTO_PDF",
            motor="prueba",
            paginas=1,
            confianza=1.0,
            sugerencia=sugerir_tipo(texto),
        ),
    )

    documento = subir(client, "incompleta.pdf", pdf_vacio())

    assert documento["estado"] == "PENDIENTE_RELACION"
    assert documento["expediente_id"] is None
    automatizacion = documento["datos_extraidos"]["automatizacion_documental"]
    assert automatizacion["estado"] == "REVISION_REQUERIDA"
    assert "Faltan campos fiscales" in automatizacion["motivos"][0]


def test_lote_reutiliza_extraccion_y_relaciona_documentos_existentes(
    client: TestClient, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.tenant_ruc = RECEPTOR
    settings.procesamiento_automatico = False
    documento = subir(client, "anterior.pdf", pdf_vacio())
    settings.procesamiento_automatico = True
    texto = """FACTURA ELECTRÓNICA F002-00000777
    RUC EMISOR: 20600000003 CLIENTE RUC: 20100000001
    Fecha de emisión: 18/09/2026 Moneda: SOLES TOTAL S/ 900.00"""
    monkeypatch.setattr(
        documentos_routes,
        "procesar",
        lambda *_: ResultadoProcesamiento(
            texto=texto,
            metodo="TEXTO_PDF",
            motor="prueba",
            paginas=1,
            confianza=1.0,
            sugerencia=sugerir_tipo(texto),
        ),
    )

    respuesta = client.post("/api/v1/documentos/procesar-pendientes", params={"limit": 50})

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {
        "considerados": 1,
        "relacionados": 1,
        "revision_requerida": 0,
        "fallidos": 0,
    }
    actualizado = client.get(f"/api/v1/documentos/{documento['id']}").json()
    assert actualizado["estado"] == "RELACIONADO"
    assert client.post("/api/v1/documentos/procesar-pendientes").json()["considerados"] == 0


def test_procesar_archivo_no_soportado_no_pierde_original(client: TestClient) -> None:
    documento = subir(client, "nota.txt", b"texto simple")
    respuesta = client.post(f"/api/v1/documentos/{documento['id']}/procesar")
    assert respuesta.status_code == 422
    descarga = client.get(f"/api/v1/documentos/{documento['id']}/archivo")
    assert descarga.content == b"texto simple"


def test_confirma_campos_extraidos_con_validacion_y_auditoria(client: TestClient) -> None:
    documento = subir(client, "voucher.pdf", b"%PDF-1.7 voucher")
    respuesta = client.put(
        f"/api/v1/documentos/{documento['id']}/extraccion-confirmada",
        json={
            "serie": "F001",
            "correlativo": "123",
            "ruc_emisor": "20500000002",
            "fecha_emision": "2026-09-17",
            "moneda": "PEN",
            "importe_total": "2500.40",
            "numero_operacion": "OP-908771",
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    confirmado = respuesta.json()["datos_extraidos"]["extraccion_confirmada"]
    assert confirmado["version"] == 1
    assert confirmado["campos"]["importe_total"] == "2500.40"
    assert confirmado["campos"]["fecha_emision"] == "2026-09-17"

    invalido = client.put(
        f"/api/v1/documentos/{documento['id']}/extraccion-confirmada",
        json={"ruc_emisor": "123", "importe_total": "-1"},
    )
    assert invalido.status_code == 422
    vacio = client.put(f"/api/v1/documentos/{documento['id']}/extraccion-confirmada", json={})
    assert vacio.status_code == 422


def test_creacion_asistida_es_idempotente_por_identidad_fiscal(client: TestClient) -> None:
    campos = {
        "serie": "F001",
        "correlativo": "123",
        "ruc_emisor": "20500000002",
        "ruc_receptor": RECEPTOR,
        "fecha_emision": "2026-09-17",
        "moneda": "PEN",
        "importe_total": "2500.40",
    }
    solicitud = {
        "tipo_comprobante": "FACT",
        "razon_social_emisor": "PROVEEDOR SAC",
        "razon_social_receptor": "CLIENTE SAC",
        "requiere_guia": True,
    }
    primero = subir(client, "factura.pdf", b"%PDF-1.7 primera recepcion")
    sin_confirmar = client.post(
        f"/api/v1/documentos/{primero['id']}/crear-expediente", json=solicitud
    )
    assert sin_confirmar.status_code == 409
    assert (
        client.put(
            f"/api/v1/documentos/{primero['id']}/extraccion-confirmada", json=campos
        ).status_code
        == 200
    )
    creado = client.post(f"/api/v1/documentos/{primero['id']}/crear-expediente", json=solicitud)
    assert creado.status_code == 200, creado.text
    assert creado.json()["creado"] is True
    expediente_id = creado.json()["expediente"]["id"]
    assert creado.json()["documento"]["estado"] == "RELACIONADO"

    repetido = client.post(f"/api/v1/documentos/{primero['id']}/crear-expediente", json=solicitud)
    assert repetido.status_code == 200
    assert repetido.json()["creado"] is False
    assert repetido.json()["expediente"]["id"] == expediente_id

    segunda_recepcion = subir(client, "foto-factura.jpg", b"\xff\xd8\xffsegunda recepcion")
    assert (
        client.put(
            f"/api/v1/documentos/{segunda_recepcion['id']}/extraccion-confirmada", json=campos
        ).status_code
        == 200
    )
    asociado = client.post(
        f"/api/v1/documentos/{segunda_recepcion['id']}/crear-expediente", json=solicitud
    )
    assert asociado.status_code == 200
    assert asociado.json()["creado"] is False
    assert asociado.json()["expediente"]["id"] == expediente_id
    detalle = expediente(client, expediente_id)
    assert len(detalle["documentos"]) == 2


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


def test_documentos_filtran_por_tipo_y_emisor(client: TestClient) -> None:
    primero = subir(client, "f1.xml", factura())
    subir(client, "f2.xml", factura(numero="F002-00000777", emisor="20600000003"))

    por_tipo = client.get("/api/v1/documentos", params={"tipo_documento": "FACT"})
    assert por_tipo.status_code == 200
    assert len(por_tipo.json()) == 2

    por_emisor = client.get("/api/v1/documentos", params={"emisor_ruc": "20600000003"})
    assert por_emisor.status_code == 200
    ids = {documento["id"] for documento in por_emisor.json()}
    assert primero["id"] not in ids
    assert len(ids) == 1

    futuro = client.get("/api/v1/documentos", params={"fecha_desde": "2099-01-01"})
    assert futuro.status_code == 200
    assert futuro.json() == []


def test_eliminar_documento_es_logico_y_deja_de_listarlo(client: TestClient) -> None:
    documento = subir(client, "eliminar.pdf", b"%PDF-1.7 documento temporal")
    documento_id = documento["id"]

    respuesta = client.delete(f"/api/v1/documentos/{documento_id}")
    assert respuesta.status_code == 204

    assert client.get(f"/api/v1/documentos/{documento_id}").status_code == 404
    listado = client.get("/api/v1/documentos")
    assert listado.status_code == 200
    assert all(d["id"] != documento_id for d in listado.json())


def test_reprocesamiento_masivo_repara_razones_sociales(
    client: TestClient, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.tenant_ruc = RECEPTOR
    settings.procesamiento_automatico = False
    documento = subir(client, "factura-anterior.pdf", pdf_vacio())
    settings.procesamiento_automatico = True
    texto = """FACTURA ELECTRÓNICA F003-00000888
    PROVEEDOR: PESQUERA DEL PACIFICO S.A.C. RUC EMISOR: 20600000003
    CLIENTE: NEXOMAR NEGOCIOS E.I.R.L. RUC: 20100000001
    Fecha de emisión: 19/09/2026 Moneda: SOLES TOTAL S/ 1,250.00"""
    monkeypatch.setattr(
        documentos_routes,
        "procesar",
        lambda *_: ResultadoProcesamiento(
            texto=texto,
            metodo="TEXTO_PDF",
            motor="prueba",
            paginas=1,
            confianza=1.0,
            sugerencia=sugerir_tipo(texto),
        ),
    )

    respuesta = client.post(
        "/api/v1/documentos/procesar-pendientes",
        params={"limit": 100, "forzar": True, "sin_expediente": True},
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["relacionados"] == 1

    actualizado = client.get(f"/api/v1/documentos/{documento['id']}").json()
    assert actualizado["estado"] == "RELACIONADO"
    detalle = expediente(client, actualizado["expediente_id"])
    assert detalle["emisor"]["razon_social"] == "PESQUERA DEL PACIFICO S.A.C."
    assert detalle["receptor"]["razon_social"] == "NEXOMAR NEGOCIOS E.I.R.L."


def test_recalcular_corrige_expedientes_historicos_menores_al_umbral(
    client: TestClient, engine: Engine
) -> None:
    documento = subir(client, "historica.xml", factura(importe="950.00"))
    expediente_id = documento["expediente_id"]
    autorizar_receptor(client)

    with sessionmaker(engine, expire_on_commit=False)() as session:
        historico = session.get(Expediente, expediente_id)
        assert historico is not None
        historico.requiere_guia = True
        historico.estado = "NARANJA"
        session.commit()

    respuesta = client.post("/api/v1/expedientes/recalcular")
    assert respuesta.status_code == 200, respuesta.text

    detalle = expediente(client, expediente_id)
    assert detalle["requiere_guia"] is False
    assert detalle["faltantes"] == []
    assert detalle["estado"] == "VERDE"

def test_rhe_pdf_crea_expediente_automaticamente_con_partes(
    client: TestClient, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.tenant_ruc = RECEPTOR
    texto = f"""RECIBO POR HONORARIOS ELECTRÓNICO
    JUAN PEREZ LOPEZ
    RUC: 10456789012
    E001-00000038
    RECIBÍ DE: CLIENTE SAC
    IDENTIFICADO CON RUC NÚMERO: {RECEPTOR}
    FECHA DE EMISIÓN: 02/10/2026
    TOTAL POR HONORARIOS: S/ 350.00"""
    monkeypatch.setattr(
        documentos_routes,
        "procesar",
        lambda *_: ResultadoProcesamiento(
            texto=texto,
            metodo="TEXTO_PDF",
            motor="prueba",
            paginas=1,
            confianza=1.0,
            sugerencia=sugerir_tipo(texto),
        ),
    )

    documento = subir(client, "rhe.pdf", pdf_vacio())

    assert documento["estado"] == "RELACIONADO"
    assert documento["tipo_documento"] == "RHE"
    assert documento["expediente_id"] is not None
    detalle = expediente(client, documento["expediente_id"])
    assert detalle["tipo_comprobante"] == "RHE"
    assert detalle["requiere_guia"] is False
    assert detalle["emisor"]["ruc"] == "10456789012"
    assert detalle["emisor"]["razon_social"] == "JUAN PEREZ LOPEZ"
    assert detalle["receptor"]["ruc"] == RECEPTOR
    assert detalle["receptor"]["razon_social"] == "CLIENTE SAC"


def test_listado_documentos_incluye_partes_del_expediente(client: TestClient) -> None:
    documento = subir(client, "factura.xml", factura())
    respuesta = client.get("/api/v1/documentos", params={"tipo_documento": "FACT"})
    assert respuesta.status_code == 200
    fila = next(d for d in respuesta.json() if d["id"] == documento["id"])
    assert fila["emisor"]["ruc"] == "20500000002"
    assert fila["emisor"]["razon_social"] == "PROVEEDOR SAC"
    assert fila["receptor"]["ruc"] == RECEPTOR
    assert fila["receptor"]["razon_social"] == "CLIENTE SAC"


def test_reprocesar_partes_repara_empresas_de_documento_relacionado(
    client: TestClient, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.tenant_ruc = RECEPTOR
    texto_inicial = """FACTURA ELECTRÓNICA F009-00000021
    RUC EMISOR: 20611111111 CLIENTE RUC: 20100000001
    Fecha de emisión: 20/09/2026 Moneda: SOLES TOTAL S/ 700.00"""
    monkeypatch.setattr(
        documentos_routes,
        "procesar",
        lambda *_: ResultadoProcesamiento(
            texto=texto_inicial,
            metodo="TEXTO_PDF",
            motor="prueba",
            paginas=1,
            confianza=1.0,
            sugerencia=sugerir_tipo(texto_inicial),
        ),
    )
    documento = subir(client, "factura-sin-nombres.pdf", pdf_vacio())
    assert documento["estado"] == "RELACIONADO"

    texto_actualizado = """FACTURA ELECTRÓNICA F009-00000021
    PROVEEDOR: PESQUERA ACTUALIZADA S.A.C. RUC EMISOR: 20611111111
    CLIENTE: CLIENTE ACTUALIZADO S.A.C. RUC: 20100000001
    Fecha de emisión: 20/09/2026 Moneda: SOLES TOTAL S/ 700.00"""
    monkeypatch.setattr(
        documentos_routes,
        "procesar",
        lambda *_: ResultadoProcesamiento(
            texto=texto_actualizado,
            metodo="TEXTO_PDF",
            motor="prueba",
            paginas=1,
            confianza=1.0,
            sugerencia=sugerir_tipo(texto_actualizado),
        ),
    )

    respuesta = client.post(
        "/api/v1/documentos/procesar-pendientes",
        params={"limit": 100, "forzar": True, "completar_partes": True},
    )
    assert respuesta.status_code == 200, respuesta.text
    detalle = expediente(client, documento["expediente_id"])
    assert detalle["emisor"]["razon_social"] == "PESQUERA ACTUALIZADA S.A.C."
    assert detalle["receptor"]["razon_social"] == "CLIENTE ACTUALIZADO S.A.C."
