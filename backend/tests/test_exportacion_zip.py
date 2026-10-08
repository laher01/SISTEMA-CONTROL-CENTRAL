import io
import json
import zipfile

from fastapi.testclient import TestClient

from tests.xml import factura


def test_zip_incluye_originales_y_manifiesto(client: TestClient) -> None:
    documento = client.post(
        "/api/v1/documentos",
        files={"archivo": ("F001-00000456.xml", factura(numero="F001-00000456"))},
    )
    assert documento.status_code == 201, documento.text
    expediente_id = documento.json()["expediente_id"]
    respuesta = client.get(f"/api/v1/expedientes/{expediente_id}/descargar-zip")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(respuesta.content)) as archivo:
        nombres = archivo.namelist()
        assert len(nombres) == 2
        documento_xml = next(n for n in nombres if n.endswith(".xml"))
        manifiesto = next(n for n in nombres if n.endswith("manifiesto.json"))
        assert archivo.read(documento_xml)
        metadatos = json.loads(archivo.read(manifiesto))
        assert metadatos["expediente"] == expediente_id
        assert len(metadatos["documentos"]) == 1
        assert len(metadatos["documentos"][0]["sha256"]) == 64


def test_zip_no_permita_acceder_a_expediente_ajeno(client: TestClient) -> None:
    respuesta = client.get("/api/v1/expedientes/00000000-0000-0000-0000-000000000001/descargar-zip")
    assert respuesta.status_code == 404
