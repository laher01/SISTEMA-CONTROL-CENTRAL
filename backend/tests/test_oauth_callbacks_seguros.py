"""Los callbacks OAuth no deben admitir esquemas falsos ni URLs ambiguas."""

import pytest

from app.services.google_oauth_correo import crear_url_autorizacion
from app.services.microsoft_oauth_correo import crear_url_microsoft


@pytest.mark.parametrize(
    "destino",
    [
        "https://",
        "https://usuario:secreto@factcentral.online/callback",
        "https://factcentral.online/callback#token",
        "https://factcentral.online.ejemplo.test/callback#fragment",
        "javascript:alert(1)",
        "http://factcentral.online/callback",
    ],
)
def test_ambos_proveedores_rechazan_callbacks_ambiguos(destino: str) -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        crear_url_autorizacion(
            client_id="google",
            redirect_uri=destino,
            state="estado",
            code_challenge="pkce",
        )
    with pytest.raises(ValueError, match="HTTPS"):
        crear_url_microsoft(
            client_id="microsoft",
            redirect_uri=destino,
            state="estado",
            code_challenge="pkce",
        )
