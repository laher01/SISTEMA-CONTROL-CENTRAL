"""Pruebas del contrato editorial aislado; no prueban endpoints productivos."""
import pytest

from app.services.cms_landing_core import (
    EstadoEditorial,
    RevisionEditorial,
    transicionar,
)


def inicial() -> RevisionEditorial:
    return RevisionEditorial(1, EstadoEditorial.BORRADOR, {"titulo": "Prueba"})


def test_ciclo_editorial_requiere_aprobacion() -> None:
    actual = inicial()
    for esperado in (
        EstadoEditorial.VISTA_PREVIA,
        EstadoEditorial.APROBADO,
        EstadoEditorial.PUBLICADO,
    ):
        anterior = actual
        actual, evento = transicionar(
            actual, destino=esperado, version_esperada=actual.version,
            rol="SUPERADMIN", actor_id="auditor",
        )
        assert actual.version == anterior.version + 1
        assert evento.anterior == anterior.estado
        assert evento.nuevo == esperado
        assert evento.actor_id == "auditor"


def test_no_se_puede_publicar_directamente_un_borrador() -> None:
    with pytest.raises(ValueError, match="Transición"):
        transicionar(
            inicial(), destino=EstadoEditorial.PUBLICADO,
            version_esperada=1, rol="SUPERADMIN", actor_id="auditor",
        )


def test_otro_rol_no_puede_aprobar() -> None:
    with pytest.raises(PermissionError):
        transicionar(
            inicial(), destino=EstadoEditorial.VISTA_PREVIA,
            version_esperada=1, rol="ADMINISTRADOR", actor_id="usuario",
        )


def test_version_obsoleta_no_modifica_la_revision() -> None:
    revision = inicial()
    with pytest.raises(ValueError, match="versión"):
        transicionar(
            revision, destino=EstadoEditorial.VISTA_PREVIA,
            version_esperada=0, rol="SUPERADMIN", actor_id="auditor",
        )
    assert revision.version == 1
    assert revision.estado == EstadoEditorial.BORRADOR
