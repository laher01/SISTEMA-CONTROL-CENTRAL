import io

from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfReader

from tests.xml import factura


def test_pdf_contiene_factura_original_y_portada(client: TestClient) -> None:
    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("factura.xml", factura(numero="F001-00000701"))},
    )
    assert subida.status_code == 201, subida.text
    expediente_id = subida.json()["expediente_id"]
    respuesta = client.get(f"/api/v1/expedientes/{expediente_id}/descargar-pdf")
    assert respuesta.status_code == 200, respuesta.text
    reader = PdfReader(io.BytesIO(respuesta.content))
    assert len(reader.pages) >= 1
    assert len(reader.attachments) == 1


def test_pdf_convierte_imagen_vinculada(client: TestClient) -> None:
    subida = client.post(
        "/api/v1/documentos",
        files={"archivo": ("factura.xml", factura(numero="F001-00000702"))},
    )
    assert subida.status_code == 201, subida.text
    expediente_id = subida.json()["expediente_id"]
    imagen = Image.new("RGB", (80, 100), "white")
    imagen_bytes = io.BytesIO()
    imagen.save(imagen_bytes, format="PNG")
    respuesta_imagen = client.post(
        "/api/v1/documentos",
        files={"archivo": ("voucher.png", imagen_bytes.getvalue(), "image/png")},
        data={"expediente_id": expediente_id, "tipo_documento": "VCHR"},
    )
    assert respuesta_imagen.status_code == 201, respuesta_imagen.text

    resultado = client.get(f"/api/v1/expedientes/{expediente_id}/descargar-pdf")
    assert resultado.status_code == 200, resultado.text
    lector = PdfReader(io.BytesIO(resultado.content))
    assert len(lector.pages) >= 2
    assert len(lector.attachments) == 2


def test_pdf_ajeno_responde_404(client: TestClient) -> None:
    respuesta = client.get("/api/v1/expedientes/00000000-0000-0000-0000-000000000001/descargar-pdf")
    assert respuesta.status_code == 404
