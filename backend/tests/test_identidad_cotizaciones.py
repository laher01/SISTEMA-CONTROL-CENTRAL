from app.services.identidad_cotizaciones import identidad_cotizacion


def test_emisor_explicito_identifica_misma_cotizacion() -> None:
    a = identidad_cotizacion(
        "PROVEEDOR RUC: 20615898598\\nCLIENTE RUC: 20538821374",
        "00275 - 2026",
    )
    b = identidad_cotizacion(
        "RUC DEL EMISOR: 20615898598\\nRUC CLIENTE: 20538821374",
        "00275-2026",
    )
    assert a["estado"] == "IDENTIFICADO"
    assert a["huella"] == b["huella"]


def test_cliente_no_es_emisor() -> None:
    resultado = identidad_cotizacion("CLIENTE RUC 20538821374", "074")
    assert resultado["emisor_ruc"] is None
    assert resultado["huella"] is None
    assert resultado["estado"] == "REVISION"


def test_numeracion_repetida_proveedores_diferentes() -> None:
    a = identidad_cotizacion("PROVEEDOR RUC 20615898598", "074")
    b = identidad_cotizacion("PROVEEDOR RUC 20538821374", "074")
    assert a["huella"] != b["huella"]


def test_no_confundir_mismo_ruc_como_emisor_y_cliente() -> None:
    resultado = identidad_cotizacion("PROVEEDOR RUC 20615898598 CLIENTE RUC 20615898598", "074")
    assert resultado["estado"] == "REVISION"
