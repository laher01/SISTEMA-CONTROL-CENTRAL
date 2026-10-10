import io
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes import documentos as documentos_routes
from app.core.config import Settings
from app.models import Empresa, Expediente
from app.services import procesamiento_documental
from app.services.procesamiento_documental import ResultadoProcesamiento, sugerir_tipo
from tests.conftest import AuthPrueba, Reloj
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


def autorizar_receptor(
    client: TestClient,
    auth_prueba: AuthPrueba,
    **extra: bool,
) -> None:
    contexto_anterior = auth_prueba.contexto
    empresas = client.get("/api/v1/empresas").json()
    receptor = next(e for e in empresas if e["ruc"] == RECEPTOR)
    auth_prueba.como_admin()
    try:
        respuesta = client.patch(
            f"/api/v1/empresas/{receptor['id']}",
            json={"autorizada": True, **extra},
        )
        assert respuesta.status_code == 200, respuesta.text
    finally:
        auth_prueba.contexto = contexto_anterior


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


def test_expediente_completo_queda_verde(client: TestClient, auth_prueba: AuthPrueba) -> None:
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

    autorizar_receptor(client, auth_prueba)
    detalle = expediente(client, expediente_id)
    assert detalle["estado"] == "VERDE"
    assert detalle["pendiente_aprobacion"] is False
    assert detalle["faltantes"] == []
    assert alertas_abiertas(detalle) == set()


def test_agente_retencion_sin_constancia_queda_amarillo(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    doc_factura = subir(client, "f.xml", factura())
    expediente_id = str(doc_factura["expediente_id"])
    subir(client, "g.xml", guia())
    subir(client, "v.jpg", b"\xff\xd8 voucher", tipo_documento="VCHR", expediente_id=expediente_id)
    autorizar_receptor(client, auth_prueba, agente_retencion=True)

    detalle = expediente(client, expediente_id)
    assert detalle["estado"] == "AMARILLO"
    assert alertas_abiertas(detalle) == {"RETENCION_PENDIENTE"}

    subir(client, "ret.pdf", b"%PDF ret", tipo_documento="RET", expediente_id=expediente_id)
    assert expediente(client, expediente_id)["estado"] == "VERDE"


def test_expediente_vencido_queda_rojo(
    client: TestClient, reloj: Reloj, auth_prueba: AuthPrueba
) -> None:
    doc_factura = subir(client, "f.xml", factura(importe="2500.00"))
    expediente_id = doc_factura["expediente_id"]
    autorizar_receptor(client, auth_prueba)

    reloj.hoy = date(2026, 10, 8)
    auth_prueba.como_admin()
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

    # El receptor no redefine la identidad de un RHE ya emitido.
    # Mismo emisor + RHE + serie + correlativo debe seguir siendo el mismo
    # comprobante, incluso si llega con un receptor contradictorio.
    datos_otro_receptor = {
        **datos,
        "receptor": {"ruc": "20609762030", "razon_social": "MAIK FISHING S.A.C."},
    }
    conflicto = client.post("/api/v1/expedientes", json=datos_otro_receptor)
    assert conflicto.status_code == 409
    assert conflicto.json()["detail"]["expediente_id"] == creado["id"]


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
    assert confirmado["version"] == 2
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


def test_eliminar_documento_es_logico_y_deja_de_listarlo(
    client: TestClient,
    auth_prueba: AuthPrueba,
) -> None:
    documento = subir(client, "eliminar.pdf", b"%PDF-1.7 documento temporal")
    auth_prueba.como_admin()
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
    client: TestClient,
    engine: Engine,
    auth_prueba: AuthPrueba,
) -> None:
    documento = subir(client, "historica.xml", factura(importe="950.00"))
    expediente_id = documento["expediente_id"]
    autorizar_receptor(client, auth_prueba)

    with sessionmaker(engine, expire_on_commit=False)() as session:
        historico = session.get(Expediente, expediente_id)
        assert historico is not None
        historico.requiere_guia = True
        historico.estado = "NARANJA"
        session.commit()

    auth_prueba.como_admin()
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


def test_dashboard_desglose_agrupa_y_filtra(client: TestClient) -> None:
    subir(
        client,
        "septiembre.xml",
        factura(numero="F001-00001001", fecha="2026-09-10", importe="1200.00"),
    )
    subir(
        client,
        "octubre.xml",
        factura(
            numero="F002-00001002",
            fecha="2026-10-02",
            importe="800.00",
            emisor="20600000003",
        ),
    )

    por_mes = client.get(
        "/api/v1/dashboard/desglose",
        params={"agrupar_por": "mes", "orden": "asc"},
    )
    assert por_mes.status_code == 200, por_mes.text
    assert [fila["clave"] for fila in por_mes.json()["filas"]] == ["2026-09", "2026-10"]

    por_emisor = client.get(
        "/api/v1/dashboard/desglose",
        params={"agrupar_por": "emisor", "orden": "desc"},
    )
    assert por_emisor.status_code == 200, por_emisor.text
    assert {fila["ruc"] for fila in por_emisor.json()["filas"]} == {
        "20500000002",
        "20600000003",
    }

    empresa = next(fila for fila in por_emisor.json()["filas"] if fila["ruc"] == "20600000003")
    assert empresa["expedientes"] == 1
    assert empresa["total_pen"] == "800.00"

    octubre = client.get(
        "/api/v1/dashboard/desglose",
        params={
            "agrupar_por": "dia",
            "fecha_desde": "2026-10-01",
            "fecha_hasta": "2026-10-31",
        },
    )
    assert octubre.status_code == 200, octubre.text
    assert len(octubre.json()["filas"]) == 1
    assert octubre.json()["filas"][0]["clave"] == "2026-10-02"


def test_rhe_crea_expedientes_propios_y_suma_montos(
    client: TestClient,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings.tenant_ruc = None
    textos = iter(
        [
            """RECIBO POR HONORARIOS ELECTRÓNICO E001-33
AYALA AREVALO ELVIS EDUARDO R.U.C. 10753246920
Recibí de FRUTTI DEL PAESE E.I.R.L.
Identificado con RUC Número 20611909234
Fecha de emisión 17 de Agosto del 2026
Total por Honorarios : 1,500.00
Retención (8 %) IR : (0.00)
Total Neto Recibido : 1,500.00 SOLES""",
            """RECIBO POR HONORARIOS ELECTRÓNICO E001-34
AYALA AREVALO ELVIS EDUARDO R.U.C. 10753246920
Recibí de INVERSIONES YATAMURI E.I.R.L.
Identificado con RUC Número 20492560601
Fecha de emisión 18 de Agosto del 2026
Total por Honorarios : 1,500.00
Retención (8 %) IR : (0.00)
Total Neto Recibido : 1,500.00 SOLES""",
            """RECIBO POR HONORARIOS ELECTRÓNICO E001-35
AYALA AREVALO ELVIS EDUARDO R.U.C. 10753246920
Recibí de MAIK FISHING SOCIEDAD ANONIMA CERRADA
Identificado con RUC Número 20609762030
Fecha de emisión 19 de Agosto del 2026
Total por Honorarios : 1,500.00
Retención (8 %) IR : (0.00)
Total Neto Recibido : 1,500.00 SOLES""",
        ]
    )

    def procesar_rhe(*_: object) -> ResultadoProcesamiento:
        texto = next(textos)
        return ResultadoProcesamiento(
            texto=texto,
            metodo="TEXTO_PDF",
            motor="prueba",
            paginas=1,
            confianza=1.0,
            sugerencia=sugerir_tipo(texto),
        )

    monkeypatch.setattr(documentos_routes, "procesar", procesar_rhe)

    documentos = [
        subir(client, "rhe-35.pdf", pdf_vacio() + b"35"),
        subir(client, "rhe-34.pdf", pdf_vacio() + b"34"),
        subir(client, "rhe-33.pdf", pdf_vacio() + b"33"),
    ]

    assert all(doc["tipo_documento"] == "RHE" for doc in documentos)
    assert all(doc["estado"] == "RELACIONADO" for doc in documentos)
    expedientes_ids = {doc["expediente_id"] for doc in documentos}
    assert None not in expedientes_ids
    assert len(expedientes_ids) == 3

    detalles = [expediente(client, expediente_id) for expediente_id in expedientes_ids]
    assert {detalle["correlativo"] for detalle in detalles} == {"33", "34", "35"}
    assert all(detalle["requiere_guia"] is False for detalle in detalles)

    resumen = client.get("/api/v1/dashboard/resumen")
    assert resumen.status_code == 200, resumen.text
    datos = resumen.json()
    assert datos["expedientes_total"] == 3
    montos = {m["moneda"]: m for m in datos["montos"]}
    total_pen = Decimal(montos["PEN"]["bancarizable"]) + Decimal(montos["PEN"]["no_bancarizable"])
    assert total_pen == Decimal("4500.00")


def test_empresas_solo_se_eliminan_manual_y_se_reactivan_por_ruc(
    client: TestClient,
    auth_prueba: AuthPrueba,
) -> None:
    usuario_id = auth_prueba.contexto.usuario_id
    assert usuario_id is not None

    subir(client, "empresa-base.xml", factura(numero="F001-00000901"))
    listado = client.get("/api/v1/empresas")
    assert listado.status_code == 200, listado.text
    empresas = listado.json()
    assert len(empresas) == 2
    ids = [empresa["id"] for empresa in empresas]

    auth_prueba.como_superadmin()
    prohibido = client.post(
        "/api/v1/empresas/eliminar-seleccion",
        json={"empresa_ids": ids},
    )
    assert prohibido.status_code == 403, prohibido.text

    auth_prueba.como_admin()
    eliminado = client.post(
        "/api/v1/empresas/eliminar-seleccion",
        json={"empresa_ids": ids},
    )
    assert eliminado.status_code == 200, eliminado.text
    assert eliminado.json() == {"eliminadas": 2}
    assert client.get("/api/v1/empresas").json() == []

    auth_prueba.como_usuario(usuario_id)
    subir(client, "empresa-reaparece.xml", factura(numero="F001-00000902"))
    reactivadas = client.get("/api/v1/empresas")
    assert reactivadas.status_code == 200, reactivadas.text
    assert {empresa["id"] for empresa in reactivadas.json()} == set(ids)


def test_reprocesar_rhe_repara_razon_social_contaminada(
    client: TestClient,
    session: Session,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    auth_prueba: AuthPrueba,
) -> None:
    settings.tenant_ruc = None
    empresa = Empresa(
        tenant_id=auth_prueba.contexto.tenant_id,
        ruc="10753246920",
        razon_social="Nro: E001-33",
    )
    session.add(empresa)
    session.commit()

    texto = """RECIBO POR HONORARIOS ELECTRÓNICO
AYALA AREVALO ELVIS EDUARDO R.U.C. 10753246920
Nro: E001-35
Recibí de MAIK FISHING SOCIEDAD ANONIMA CERRADA
Identificado con RUC Número 20609762030
Fecha de emisión 19 de Agosto del 2026
Total por Honorarios : 1,500.00 SOLES"""

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

    documento = subir(client, "rhe-35.pdf", pdf_vacio())
    assert documento["expediente_id"] is not None

    session.refresh(empresa)
    assert empresa.razon_social == "AYALA AREVALO ELVIS EDUARDO"


def test_admin_edita_ruc_y_razon_social_empresa(
    client: TestClient,
    auth_prueba: AuthPrueba,
) -> None:
    subir(client, "empresa-editar.xml", factura(numero="F001-00000910"))
    empresas = client.get("/api/v1/empresas").json()
    empresa = next(item for item in empresas if item["ruc"] == "20500000002")

    auth_prueba.como_admin()
    respuesta = client.patch(
        f"/api/v1/empresas/{empresa['id']}",
        json={
            "ruc": "20615898599",
            "razon_social": "EMPRESA CORREGIDA E.I.R.L.",
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["ruc"] == "20615898599"
    assert datos["razon_social"] == "EMPRESA CORREGIDA E.I.R.L."


def test_no_permite_duplicar_ruc_al_editar_empresa(
    client: TestClient,
    auth_prueba: AuthPrueba,
) -> None:
    subir(client, "empresa-duplicado.xml", factura(numero="F001-00000911"))
    empresas = client.get("/api/v1/empresas").json()
    assert len(empresas) >= 2
    origen = empresas[0]
    destino = empresas[1]

    auth_prueba.como_admin()
    respuesta = client.patch(
        f"/api/v1/empresas/{origen['id']}",
        json={"ruc": destino["ruc"]},
    )
    assert respuesta.status_code == 409


def test_empresas_clasifican_proveedor_cliente_y_usuario(
    client: TestClient,
    auth_prueba: AuthPrueba,
) -> None:
    subir(client, "clasificacion.xml", factura(numero="F001-00000920"))

    respuesta = client.get("/api/v1/empresas")
    assert respuesta.status_code == 200, respuesta.text
    empresas = respuesta.json()
    proveedor = next(item for item in empresas if item["ruc"] == "20500000002")
    cliente = next(item for item in empresas if item["ruc"] == "20100000001")

    assert proveedor["tipo_relacion"] == "PROVEEDOR"
    assert cliente["tipo_relacion"] == "CLIENTE"
    assert proveedor["clasificacion_proveedor"] is None
    assert cliente["clasificacion_proveedor"] is None
    assert [u["id"] for u in proveedor["usuarios"]] == [str(auth_prueba.contexto.usuario_id)]
    assert [u["id"] for u in cliente["usuarios"]] == [str(auth_prueba.contexto.usuario_id)]

    auth_prueba.como_admin()
    actualizado = client.patch(
        f"/api/v1/empresas/{proveedor['id']}",
        json={"clasificacion_proveedor": "A"},
    )
    assert actualizado.status_code == 200, actualizado.text
    assert actualizado.json()["clasificacion_proveedor"] == "A"

    cliente_actualizado = client.patch(
        f"/api/v1/empresas/{cliente['id']}",
        json={"clasificacion_proveedor": "B"},
    )
    assert cliente_actualizado.status_code == 200, cliente_actualizado.text
    assert cliente_actualizado.json()["clasificacion_proveedor"] is None


def test_impresion_lote_consolida_pdfs_en_orden(
    client: TestClient,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings.tenant_ruc = RECEPTOR
    textos = iter(
        [
            """FACTURA ELECTRÓNICA F001-00000931
RUC EMISOR: 20500000002 CLIENTE RUC: 20100000001
Fecha de emisión: 17/09/2026 Moneda: SOLES TOTAL S/ 100.00""",
            """FACTURA ELECTRÓNICA F001-00000932
RUC EMISOR: 20500000002 CLIENTE RUC: 20100000001
Fecha de emisión: 18/09/2026 Moneda: SOLES TOTAL S/ 200.00""",
        ]
    )

    monkeypatch.setattr(
        documentos_routes,
        "procesar",
        lambda *_: ResultadoProcesamiento(
            texto=next(textos),
            metodo="TEXTO_PDF",
            motor="prueba",
            paginas=1,
            confianza=1.0,
            sugerencia=sugerir_tipo("FACTURA ELECTRÓNICA"),
        ),
    )

    primero = subir(client, "print-1.pdf", pdf_vacio() + b"uno")
    segundo = subir(client, "print-2.pdf", pdf_vacio() + b"dos")
    ids = [segundo["expediente_id"], primero["expediente_id"]]

    respuesta = client.post(
        "/api/v1/expedientes/imprimir-lote",
        json={"expediente_ids": ids},
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["content-type"].startswith("application/pdf")
    assert respuesta.headers["x-expedientes-impresos"] == "2"
    assert respuesta.headers["x-pdfs-impresos"] == "2"
    assert respuesta.headers["x-expedientes-sin-pdf"] == "0"

    pdf = PdfReader(io.BytesIO(respuesta.content))
    assert len(pdf.pages) == 2


def test_tres_rhe_sunat_generan_expedientes_diferentes_aunque_tenant_sea_otro(
    client: TestClient, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.tenant_ruc = RECEPTOR
    textos = iter(
        f"""RECIBO POR HONORARIOS ELECTRONICO
R.U.C. 10753246920
Nro: E001- {correlativo}
AYALA AREVALO ELVIS EDUARDO
Recibí de: {razon}
Identificado con RUC número {ruc}
La suma de: UN MIL QUINIENTOS Y 00/100 SOLES
Por concepto de EL SERVICIO DE ASESORIA Y DOCUMENTACION-PAITA
{dia} de Setiembre del 2026
1,500.00
(0.00)
1,500.00
SOLES
Total por honorarios:
Retención (8 %) IR:
Total Neto Recibido:
Fecha de emisión"""
        for correlativo, razon, ruc, dia in (
            ("37", "MAIK FISHING SOCIEDAD ANONIMA CERRADA", "20609762030", "23"),
            ("38", "INVERSIONES YATAMURI E.I.R.L.", "20492560601", "24"),
            ("39", "FRUTTI DEL PAESE E.I.R.L.", "20611909234", "23"),
        )
    )

    def procesar_rhe(*_: object) -> ResultadoProcesamiento:
        texto = next(textos)
        return ResultadoProcesamiento(
            texto=texto,
            metodo="TEXTO_PDF",
            motor="prueba",
            paginas=1,
            confianza=1.0,
            sugerencia=sugerir_tipo(texto),
        )

    monkeypatch.setattr(documentos_routes, "procesar", procesar_rhe)
    ids: set[str] = set()
    for numero in ("37", "38", "39"):
        documento = subir(client, f"RHE-{numero}.pdf", pdf_vacio() + numero.encode())
        assert documento["estado"] == "RELACIONADO", documento
        assert documento["tipo_documento"] == "RHE"
        assert documento["expediente_id"] is not None
        detalle = expediente(client, documento["expediente_id"])
        assert detalle["correlativo"] == numero
        assert detalle["emisor"]["ruc"] == "10753246920"
        assert detalle["importe_total"] == "1500.00"
        ids.add(str(documento["expediente_id"]))
    assert len(ids) == 3
