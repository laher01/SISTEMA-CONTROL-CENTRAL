"""La autorización administrativa gobierna ingresos y liquidaciones, no archivos."""

from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import AuthPrueba
from tests.test_api import autorizar_receptor, subir
from tests.xml import factura


def test_cliente_sin_validar_no_cuenta_y_se_muestra_no_valido(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    doc = subir(client, "factura.xml", factura())
    assert doc["expediente_id"] is not None

    resumen = client.get("/api/v1/produccion/resumen")
    assert resumen.status_code == 200, resumen.text
    assert resumen.json()["filas"] == []

    compras = client.get("/api/v1/produccion/compras")
    assert compras.status_code == 200, compras.text
    assert len(compras.json()) == 1
    assert compras.json()[0]["cliente_autorizado"] is False
    assert Decimal(compras.json()[0]["importe_total"]) == Decimal("0")

    autorizar_receptor(client, auth_prueba)
    resumen_validado = client.get("/api/v1/produccion/resumen")
    assert resumen_validado.status_code == 200, resumen_validado.text
    assert len(resumen_validado.json()["filas"]) == 1
    assert float(resumen_validado.json()["filas"][0]["importe_total"]) > 0

    compras_validado = client.get("/api/v1/produccion/compras")
    assert compras_validado.json()[0]["cliente_autorizado"] is True
    assert float(compras_validado.json()[0]["importe_total"]) > 0


def test_cliente_eliminado_no_se_reactiva_con_otra_factura(
    client: TestClient, auth_prueba: AuthPrueba
) -> None:
    subir(client, "factura1.xml", factura())
    autorizar_receptor(client, auth_prueba)
    receptor = next(e for e in client.get("/api/v1/empresas").json() if e["autorizada"])
    auth_anterior = auth_prueba.contexto
    auth_prueba.como_admin()
    try:
        eliminado = client.post(
            "/api/v1/empresas/eliminar-seleccion",
            json={"empresa_ids": [receptor["id"]]},
        )
        assert eliminado.status_code == 200, eliminado.text
        assert eliminado.json()["eliminadas"] == 1
    finally:
        auth_prueba.contexto = auth_anterior

    subir(client, "factura2.xml", factura(numero="F001-00000125"))
    resumen = client.get("/api/v1/produccion/resumen")
    assert resumen.status_code == 200, resumen.text
    assert resumen.json()["filas"] == []
    assert receptor["id"] not in {e["id"] for e in client.get("/api/v1/empresas").json()}
