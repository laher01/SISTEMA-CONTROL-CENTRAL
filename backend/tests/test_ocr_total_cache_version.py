"""Regresiones para el total fiscal y la versión de la caché OCR."""

import hashlib
import json

from app.services.cache_ocr import VERSION_CACHE, procesar_con_cache
from app.services.extraccion_campos import extraer_campos


def test_san_jose_bizlinks_usa_importe_total_y_no_subtotal() -> None:
    texto = (
        "ESTACION DE SERVICIOS SAN JOSE SAC\n"
        "R.U.C. 20175642341\n"
        "FACTURA ELECTRONICA F091-00007229\n"
        "Cliente: EMPRESA DE PRUEBA E.I.R.L. RUC: 20999999991\n"
        "Fecha Emision: 02/10/2026\n"
        "Sub Total 6101.69S/\n"
        "Importe Total 7,200.00S/\n"
        "Powered by Bizlinks\n"
    )
    resultado = extraer_campos(texto, "TEXTO_PDF", 0.99)

    assert resultado is not None
    importe = resultado["campos"]["importe_total"]
    assert importe["valor"] == "7200.00"
    assert "Importe Total" in importe["evidencia"]


def test_cambio_de_version_ignora_cache_ocr_que_guardaba_subtotal(tmp_path) -> None:
    version_antigua = "ocr-core-v1"
    contenido = b"%PDF-1.4 synthetic invoice"
    tenant_id = "tenant-prueba"
    limite_caracteres = 10_000
    max_paginas_ocr = 50
    huella = hashlib.sha256(contenido).hexdigest()
    clave_antigua = hashlib.sha256(
        f"{version_antigua}:{huella}:{limite_caracteres}:{max_paginas_ocr}".encode()
    ).hexdigest()
    cache_antigua = tmp_path / tenant_id / clave_antigua[:2] / f"{clave_antigua}.json"
    cache_antigua.parent.mkdir(parents=True)
    cache_antigua.write_text(
        json.dumps(
            {
                "_cache_version": version_antigua,
                "extraccion_estructurada": {"campos": {"importe_total": {"valor": "6101.69"}}},
            }
        ),
        encoding="utf-8",
    )

    llamadas = 0

    def extraer_total_actualizado() -> dict[str, object]:
        nonlocal llamadas
        llamadas += 1
        return {"extraccion_estructurada": {"campos": {"importe_total": {"valor": "7200.00"}}}}

    resultado = procesar_con_cache(
        contenido,
        tenant_id,
        tmp_path,
        limite_caracteres,
        max_paginas_ocr,
        extraer_total_actualizado,
    )

    assert version_antigua != VERSION_CACHE
    assert llamadas == 1
    assert resultado["extraccion_estructurada"]["campos"]["importe_total"]["valor"] == "7200.00"
