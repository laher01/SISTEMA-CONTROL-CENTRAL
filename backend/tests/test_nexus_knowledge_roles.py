"""Aislamiento preventivo de documentación técnica según rol autenticado."""

from app.core.config import Settings
from app.services.nexus_knowledge import recuperar_conocimiento


def test_gestor_no_recibe_biblioteca_tecnica(settings: Settings) -> None:
    conocimiento, fuentes = recuperar_conocimiento(
        settings, "arquitectura dashboard permisos", "DASHBOARD", rol="GESTOR"
    )
    assert conocimiento == ""
    assert fuentes == []


def test_usuario_no_recibe_biblioteca_tecnica(settings: Settings) -> None:
    conocimiento, fuentes = recuperar_conocimiento(
        settings, "arquitectura dashboard permisos", "DASHBOARD", rol="USUARIO"
    )
    assert conocimiento == ""
    assert fuentes == []


def test_administrador_conserva_biblioteca(settings: Settings) -> None:
    conocimiento, fuentes = recuperar_conocimiento(
        settings, "dashboard", "DASHBOARD", rol="ADMINISTRADOR"
    )
    assert conocimiento
    assert fuentes
