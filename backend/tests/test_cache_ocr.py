from app.services.cache_ocr import procesar_con_cache


def test_cache_reutiliza_resultado_en_mismo_tenant(tmp_path):
    llamadas = []

    def extractor():
        llamadas.append(1)
        return {"texto": "FACTURA", "requiere_ocr": False}

    uno = procesar_con_cache(b"imagen", "tenant-a", tmp_path, 1000, 50, extractor)
    dos = procesar_con_cache(b"imagen", "tenant-a", tmp_path, 1000, 50, extractor)
    assert uno == dos
    assert len(llamadas) == 1


def test_cache_aislada_por_tenant_y_parametros(tmp_path):
    llamadas = []

    def extractor():
        llamadas.append(1)
        return {"texto": "OK", "requiere_ocr": False}

    for tenant, limite in [("a", 1000), ("b", 1000), ("a", 2000)]:
        procesar_con_cache(b"mismos bytes", tenant, tmp_path, limite, 50, extractor)
    assert len(llamadas) == 3


def test_resultados_pendientes_ocr_no_quedan_congelados(tmp_path):
    llamadas = []

    def extractor():
        llamadas.append(1)
        return {"requiere_ocr": True, "texto": ""}

    for _ in range(2):
        procesar_con_cache(b"pdf", "tenant", tmp_path, 1000, 50, extractor)
    assert len(llamadas) == 2

def test_reprocesamiento_forzado_omite_cache(tmp_path):
    llamadas = []

    def extractor():
        llamadas.append(1)
        return {"texto": f"version {len(llamadas)}", "requiere_ocr": False}

    original = procesar_con_cache(b"factura", "tenant-a", tmp_path, 1000, 50, extractor)
    actualizado = procesar_con_cache(
        b"factura", "tenant-a", tmp_path, 1000, 50, extractor, forzar=True
    )
    assert original["texto"] == "version 1"
    assert actualizado["texto"] == "version 2"
    assert len(llamadas) == 2
