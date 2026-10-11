"""Los ZIP de correo nunca se extraen a rutas del servidor."""

import io
import zipfile
from email.message import EmailMessage

import pytest

from app.services.paquetes_correo import PaqueteNoSeguro, extraer_xml_zip
from app.services.recepcion_correo_imap import _adjuntos_xml


def _zip(nombre: str, contenido: bytes) -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as paquete:
        paquete.writestr(nombre, contenido)
    return memoria.getvalue()


def test_correo_extrae_xml_de_zip() -> None:
    mensaje = EmailMessage()
    mensaje["From"] = "Prueba <proveedor@example.test>"
    mensaje.set_content("Comprobante")
    mensaje.add_attachment(
        _zip("facturas/factura.xml", b"<Invoice/>"),
        maintype="application",
        subtype="zip",
        filename="documentos.zip",
    )
    remitente, adjuntos = _adjuntos_xml(mensaje.as_bytes())
    assert remitente == "proveedor@example.test"
    assert len(adjuntos) == 1
    assert adjuntos[0].nombre == "factura.xml"
    assert adjuntos[0].contenido == b"<Invoice/>"


def test_zip_rechaza_ruta_ajena() -> None:
    with pytest.raises(PaqueteNoSeguro):
        extraer_xml_zip(_zip("../escape.xml", b"<Invoice/>"))


def test_zip_rechaza_xml_demasiado_grande() -> None:
    with pytest.raises(PaqueteNoSeguro):
        extraer_xml_zip(_zip("gigante.xml", b"x" * (5 * 1024 * 1024 + 1)))


def test_zip_ignora_otros_formatos() -> None:
    assert extraer_xml_zip(_zip("documento.pdf", b"%PDF")) == []
