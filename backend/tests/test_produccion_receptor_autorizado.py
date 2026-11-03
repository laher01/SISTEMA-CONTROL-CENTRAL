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
    assert resumen_validado.json()["filas"] == []

    # La autorización vigente solo aplica a expedientes ingresados desde ahora.
    subir(client, "factura-autorizada.xml", factura(numero="F001-00000124"))
    resumen_validado = client.get("/api/v1/produccion/resumen")
    assert resumen_validado.status_code == 200, resumen_validado.text
    assert len(resumen_validado.json()["filas"]) == 1
    assert float(resumen_validado.json()["filas"][0]["importe_total"]) > 0

    compras_validado = client.get("/api/v1/produccion/compras")
    autorizado = next(f for f in compras_validado.json() if f["cliente_autorizado"])
    anterior = next(f for f in compras_validado.json() if not f["cliente_autorizado"])
    assert float(autorizado["importe_total"]) > 0
    assert Decimal(anterior["importe_total"]) == Decimal("0")

    empresa = next(e for e in client.get("/api/v1/empresas").json() if e["ruc"] == "20100000001")
    contexto_anterior = auth_prueba.contexto
    auth_prueba.como_admin()
    try:
        desactivar = client.patch(f"/api/v1/empresas/{empresa['id']}", json={"autorizada": False})
        assert desactivar.status_code == 200, desactivar.text
    finally:
        auth_prueba.contexto = contexto_anterior

    # Desactivar no reescribe los expedientes ya ingresados y sí afecta los nuevos.
    despues_de_desactivar = client.get("/api/v1/produccion/resumen")
    assert despues_de_desactivar.status_code == 200, despues_de_desactivar.text
    assert len(despues_de_desactivar.json()["filas"]) == 1
    subir(client, "factura-desautorizada.xml", factura(numero="F001-00000125"))
    final = client.get("/api/v1/produccion/resumen")
    assert final.status_code == 200, final.text
    assert len(final.json()["filas"]) == 1


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
