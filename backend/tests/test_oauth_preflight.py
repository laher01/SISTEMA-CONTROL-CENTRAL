"""Pruebas de preflight OAuth sin llamadas externas."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "oauth_preflight", Path(__file__).resolve().parents[2] / "scripts" / "oauth_preflight.py"
)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_callback_https_valido():
    assert module.is_https_callback("https://factcentral.online/api/v1/correo/google/callback")


def test_callback_inseguro():
    assert not module.is_https_callback("http://factcentral.online/callback")
    assert not module.is_https_callback("https://user:pass@factcentral.online/callback")
    assert not module.is_https_callback("https://factcentral.online/callback#fragmento")
    assert not module.is_https_callback("https://factcentral.online/callback?code=secreto")


def test_google_sin_secretos_no_pasa(monkeypatch, capsys):
    for variable in (
        "FC_GOOGLE_OAUTH_CLIENT_ID",
        "FC_GOOGLE_OAUTH_CLIENT_SECRET",
        "FC_GOOGLE_OAUTH_REDIRECT_URI",
        "FC_CORREO_TOKEN_ENCRYPTION_KEY",
    ):
        monkeypatch.delenv(variable, raising=False)
    assert not module.check_provider(
        "GOOGLE",
        (
            "GOOGLE_OAUTH_CLIENT_ID",
            "GOOGLE_OAUTH_CLIENT_SECRET",
            "GOOGLE_OAUTH_REDIRECT_URI",
            "CORREO_TOKEN_ENCRYPTION_KEY",
        ),
    )
    assert "INCOMPLETO" in capsys.readouterr().out
