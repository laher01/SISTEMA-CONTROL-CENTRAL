"""El portal estático respeta la activación sin cambiar el dominio reservado."""

from pathlib import Path


def test_gate_portal_solo_en_dominio_nexomar() -> None:
    raiz = Path(__file__).resolve().parents[2]
    html = (raiz / "website" / "index.html").read_text(encoding="utf-8")
    assert 'host!=="nexomarnegocioseirl.online"' in html
    assert 'host!=="www.nexomarnegocioseirl.online"' in html
    assert 'fetch("/api/v1/plataforma/landing/publico"' in html
    assert 'd.activa===true?"fc-web-gate-on":"fc-web-gate-off"' in html


def test_portal_inactivo_conserva_login_y_legales() -> None:
    raiz = Path(__file__).resolve().parents[2]
    html = (raiz / "website" / "index.html").read_text(encoding="utf-8")
    assert 'id="fc-web-inactiva"' in html
    assert "https://app.nexomarnegocioseirl.online/ingresar" in html
    assert "https://app.nexomarnegocioseirl.online/privacidad" in html
    assert "https://app.nexomarnegocioseirl.online/terminos" in html
    assert "fc-web-gate-off" in html
