"""Aislamiento preventivo de documentación técnica según rol autenticado."""

import pytest

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


@pytest.mark.parametrize(
    "rol",
    [
        "GESTOR",
        "USUARIO",
        "RESPONSABLE",
        "GERENTE",
        "SECRETARIA",
        "DESCONOCIDO",
        "",
        "ADMINISTRADOR_EXTRA",
    ],
)
def test_roles_no_autorizados_no_reciben_archivos_internos(
    settings: Settings, rol: str
) -> None:
    conocimiento, fuentes = recuperar_conocimiento(
        settings, "configuracion permisos secretos arquitectura", "CONFIGURACION", rol=rol
    )
    assert conocimiento == ""
    assert fuentes == []


def test_rol_enum_administrador_mantiene_acceso(settings: Settings) -> None:
    conocimiento, fuentes = recuperar_conocimiento(
        settings, "dashboard", "DASHBOARD", rol="RolMiembro.ADMINISTRADOR"
    )
    assert conocimiento
    assert fuentes


def test_knowledge_inhabilitada_bloquea_tambien_admin(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "nexus_knowledge_enabled", False)
    conocimiento, fuentes = recuperar_conocimiento(
        settings, "dashboard", "DASHBOARD", rol="ADMINISTRADOR"
    )
    assert conocimiento == ""
    assert fuentes == []
