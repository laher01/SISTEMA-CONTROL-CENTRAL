"""Nunca exponer borradores CMS ni contenido con landing global inactiva."""

from unittest.mock import MagicMock

from app.api.routes.cms_landing import contenido_cms_publico


def test_cms_publico_falla_cerrado_sin_configuracion() -> None:
    session = MagicMock()
    session.get.return_value = None
    assert contenido_cms_publico(session) == {"disponible": False, "contenido": None}
    session.execute.assert_not_called()


def test_cms_publico_falla_cerrado_si_landing_inactiva() -> None:
    session = MagicMock()
    session.get.return_value.activa = False
    assert contenido_cms_publico(session)["disponible"] is False
    session.execute.assert_not_called()


def test_cms_publico_no_entrega_borradores() -> None:
    session = MagicMock()
    session.get.return_value.activa = True
    session.execute.return_value.mappings.return_value.one_or_none.return_value = None
    assert contenido_cms_publico(session) == {"disponible": False, "contenido": None}


def test_cms_publico_rechaza_contenido_invalido_guardado() -> None:
    session = MagicMock()
    session.get.return_value.activa = True
    session.execute.return_value.mappings.return_value.one_or_none.return_value = {
        "contenido": {"titulo": "<script>invalido</script>"}
    }
    assert contenido_cms_publico(session)["disponible"] is False
