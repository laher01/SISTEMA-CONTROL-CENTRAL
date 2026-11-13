import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Documento, PagoDocumental
from app.services.expedientes import obtener_tenant
from app.services.extraccion_campos import extraer_campos
from tests.xml import factura


def _subir(client: TestClient, nombre: str, contenido: bytes) -> dict[str, object]:
    respuesta = client.post("/api/v1/documentos", files={"archivo": (nombre, contenido)})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _marcar_voucher(session: Session, documento_id: str, importe: str) -> None:
    documento = session.get(Documento, uuid.UUID(documento_id))
    assert documento is not None
    documento.tipo_documento = "VCHR"
    documento.datos_extraidos = {
        "procesamiento_documental": {
            "extraccion_estructurada": {
                "campos": {
                    "banco": {"valor": "BCP", "confianza": 0.94, "evidencia": "BCP"},
                    "tipo_operacion": {
                        "valor": "DEPOSITO_VENTANILLA",
                        "confianza": 0.9,
                        "evidencia": "Depósito en ventanilla",
                    },
                    "fecha_emision": {
                        "valor": "2026-10-31",
                        "confianza": 0.94,
                        "evidencia": "31/10/2026",
                    },
                    "numero_operacion": {
                        "valor": f"OP-{documento_id[:8]}",
                        "confianza": 0.9,
                        "evidencia": "N.º operación",
                    },
                    "beneficiario": {
                        "valor": "PROVEEDOR SAC",
                        "confianza": 0.9,
                        "evidencia": "Beneficiario: PROVEEDOR SAC",
                    },
                    "cuenta_beneficiario": {
                        "valor": "****1234",
                        "confianza": 0.8,
                        "evidencia": "Cuenta destino ****1234",
                    },
                    "moneda": {"valor": "PEN", "confianza": 0.95, "evidencia": "S/"},
                    "importe_total": {
                        "valor": importe,
                        "confianza": 0.95,
                        "evidencia": f"S/ {importe}",
                    },
                }
            }
        }
    }
    session.commit()


def test_extrae_transferencia_bancaria_y_referencias_con_evidencia() -> None:
    texto = """BCP
TRANSFERENCIA EXITOSA
12 OCTUBRE 2026
HORA: 14:35
Número de operación 03857359
S/ 28,200.00
Enviado a: PROVEEDOR SAC
Cuenta destino: ****4412
Cuenta origen: ****0011
F091-00007270 S/ 9,400.00
F091-00007271 IMPORTE 5,875.00
"""
    resultado = extraer_campos(texto, "OCR", 0.95)
    assert resultado is not None
    campos = resultado["campos"]
    assert campos["banco"]["valor"] == "BCP"
    assert campos["tipo_operacion"]["valor"] == "TRANSFERENCIA"
    assert campos["numero_operacion"]["valor"] == "03857359"
    assert campos["beneficiario"]["evidencia"] == "Enviado a: PROVEEDOR SAC"
    assert campos["cuenta_beneficiario"]["valor"] == "****4412"
    lineas = campos["asignaciones_facturas"]["valor"]
    assert [(fila["serie"], fila["correlativo"], fila["importe_asignado"]) for fila in lineas] == [
        ("F091", "00007270", "9400.00"),
        ("F091", "00007271", "5875.00"),
    ]
    assert all(fila["requiere_confirmacion"] and fila["evidencia"] for fila in lineas)


def test_un_voucher_se_distribuye_a_cuatro_facturas_y_se_confirma_humanamente(
    client: TestClient, session: Session
) -> None:
    facturas = [
        ("F091-00007270", "9400.00"),
        ("F091-00007271", "5875.00"),
        ("F091-00007272", "1175.00"),
        ("F091-00007273", "11750.00"),
    ]
    expedientes = []
    for numero, importe in facturas:
        documento = _subir(client, f"{numero}.xml", factura(numero=numero, importe=importe))
        expedientes.append(documento["expediente_id"])
    voucher = _subir(client, "voucher-grupo.pdf", b"%PDF-1.7 voucher sintetico")
    _marcar_voucher(session, str(voucher["id"]), "28200.00")

    for termino in ("voucher-grupo", f"OP-{str(voucher['id'])[:8]}"):
        encontrados = client.get("/api/v1/documentos", params={"buscar_pago": termino})
        assert encontrados.status_code == 200, encontrados.text
        assert [fila["id"] for fila in encontrados.json()] == [voucher["id"]]

    distribucion_inicial = ["9400.00", "5875.00", "1175.00", "11650.00"]
    cuerpo = {
        "documento_id": voucher["id"],
        "asignaciones": [
            {
                "expediente_id": expediente_id,
                "importe_asignado": importe,
                "evidencia": f"Factura seleccionada manualmente: {numero}",
                "confianza": "0.95",
            }
            for (numero, _), expediente_id, importe in zip(
                facturas, expedientes, distribucion_inicial, strict=True
            )
        ],
    }
    creado = client.post("/api/v1/pagos-documentales", json=cuerpo)
    assert creado.status_code == 201, creado.text
    assert creado.json()["total_asignado"] == "28100.00"
    assert creado.json()["diferencia"] == "100.00"
    assert creado.json()["conciliado"] is False

    repetido = client.post("/api/v1/pagos-documentales", json=cuerpo)
    assert repetido.status_code == 201, repetido.text
    assert repetido.json()["id"] == creado.json()["id"]
    assert len(repetido.json()["asignaciones"]) == 4

    pago_id = creado.json()["id"]
    rechazo = client.post(
        f"/api/v1/pagos-documentales/{pago_id}/conciliar",
        json={"confirmar_referencias": True},
    )
    assert rechazo.status_code == 409
    assert "no cuadra" in rechazo.text.lower()

    cuerpo["asignaciones"][-1]["importe_asignado"] = "11750.00"
    actualizado = client.put(
        f"/api/v1/pagos-documentales/{pago_id}/asignaciones",
        json={"asignaciones": cuerpo["asignaciones"]},
    )
    assert actualizado.status_code == 200, actualizado.text
    assert Decimal(actualizado.json()["total_asignado"]) == Decimal("28200.00")
    conciliado = client.post(
        f"/api/v1/pagos-documentales/{pago_id}/conciliar",
        json={"confirmar_referencias": True},
    )
    assert conciliado.status_code == 200, conciliado.text
    assert conciliado.json()["conciliado"] is True
    assert len(conciliado.json()["asignaciones"]) == 4
    assert all(item["referencia_confirmada"] for item in conciliado.json()["asignaciones"])
    desde_factura = client.get(f"/api/v1/pagos-documentales/por-expediente/{expedientes[0]}")
    assert desde_factura.status_code == 200, desde_factura.text
    assert desde_factura.json()[0]["id"] == pago_id
    assert desde_factura.json()[0]["destacado_expediente_id"] == expedientes[0]

    pago_registrado = session.get(PagoDocumental, uuid.UUID(pago_id))
    assert pago_registrado is not None
    pago_registrado.tipo_operacion = "OTRO"
    pago_registrado.numero_operacion = None
    session.commit()
    lista = client.get("/api/v1/expedientes", params={"limit": 500})
    assert lista.status_code == 200, lista.text
    filas_por_id = {fila["id"]: fila for fila in lista.json()}
    for expediente_id in expedientes:
        comprobante = filas_por_id[expediente_id]["comprobantes_pago"][0]
        assert comprobante["tipo_operacion"] == "DEPOSITO_VENTANILLA"
        assert comprobante["numero_operacion"] == f"OP-{voucher['id'][:8]}"
        assert comprobante["estado_vinculo"] == "COMPARTIDO"
        assert comprobante["facturas_vinculadas"] == 4
    pagina = client.get("/api/v1/expedientes", params={"limit": 1})
    assert pagina.status_code == 200, pagina.text
    assert pagina.json()[0]["comprobantes_pago"][0]["facturas_vinculadas"] == 4


def test_pago_puede_asignarse_a_mas_de_cuatro_facturas_y_factura_recibir_pagos_parciales(
    client: TestClient, session: Session
) -> None:
    facturas = [
        ("F101-00000001", "5000.00"),
        ("F101-00000002", "1000.00"),
        ("F101-00000003", "1000.00"),
        ("F101-00000004", "1000.00"),
        ("F101-00000005", "1000.00"),
    ]
    expedientes = [
        _subir(client, f"{numero}.xml", factura(numero=numero, importe=importe))["expediente_id"]
        for numero, importe in facturas
    ]
    voucher_1 = _subir(client, "primer-pago.pdf", b"%PDF-1.7 voucher parcial 1")
    _marcar_voucher(session, str(voucher_1["id"]), "6000.00")
    grupos = [
        {
            "expediente_id": expediente_id,
            "importe_asignado": importe,
            "evidencia": f"Referencia {numero}",
        }
        for (numero, _), expediente_id, importe in zip(
            facturas,
            expedientes,
            ["2000.00", "1000.00", "1000.00", "1000.00", "1000.00"],
            strict=True,
        )
    ]
    creado = client.post(
        "/api/v1/pagos-documentales",
        json={"documento_id": voucher_1["id"], "asignaciones": grupos},
    )
    assert creado.status_code == 201, creado.text
    assert len(creado.json()["asignaciones"]) == 5
    assert creado.json()["diferencia"] == "0.00"
    assert Decimal(creado.json()["asignaciones"][0]["importe_asignado"]) == Decimal("2000.00")

    voucher_2 = _subir(client, "segundo-pago.pdf", b"%PDF-1.7 voucher parcial 2")
    _marcar_voucher(session, str(voucher_2["id"]), "3000.00")
    segundo = client.post(
        "/api/v1/pagos-documentales",
        json={
            "documento_id": voucher_2["id"],
            "asignaciones": [
                {
                    "expediente_id": expedientes[0],
                    "importe_asignado": "3000.00",
                    "evidencia": "Segundo pago parcial",
                }
            ],
        },
    )
    assert segundo.status_code == 201, segundo.text
    pagos_factura = client.get(f"/api/v1/pagos-documentales/por-expediente/{expedientes[0]}")
    assert pagos_factura.status_code == 200
    assert len(pagos_factura.json()) == 2
    lista = client.get("/api/v1/expedientes", params={"limit": 500})
    assert lista.status_code == 200, lista.text
    factura_con_pagos = next(fila for fila in lista.json() if fila["id"] == expedientes[0])
    assert len(factura_con_pagos["comprobantes_pago"]) == 2
    assert {fila["estado_vinculo"] for fila in factura_con_pagos["comprobantes_pago"]} == {
        "COMPARTIDO",
        "INDIVIDUAL",
    }


def test_monto_total_se_trata_como_decimal_sin_float() -> None:
    assert Decimal("9400.00") + Decimal("5875.00") + Decimal("1175.00") + Decimal(
        "11750.00"
    ) == Decimal("28200.00")


def test_voucher_de_otro_tenant_no_se_puede_consultar_ni_asignar(
    client: TestClient, session: Session
) -> None:
    voucher = _subir(client, "voucher-otro-tenant.pdf", b"%PDF-1.7 voucher")
    documento = session.get(Documento, uuid.UUID(str(voucher["id"])))
    assert documento is not None
    otro_tenant = obtener_tenant(session, "otro-tenant")
    documento.tenant_id = otro_tenant.id
    documento.tipo_documento = "VCHR"
    session.commit()

    respuesta = client.get(f"/api/v1/pagos-documentales/por-documento/{voucher['id']}")
    assert respuesta.status_code == 404
    asignacion = client.post(
        "/api/v1/pagos-documentales",
        json={
            "documento_id": voucher["id"],
            "asignaciones": [
                {
                    "expediente_id": str(uuid.uuid4()),
                    "importe_asignado": "1.00",
                    "evidencia": "Prueba de aislamiento",
                }
            ],
        },
    )
    assert asignacion.status_code == 404
