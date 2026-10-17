"""Aislamiento preventivo de documentación técnica según rol autenticado."""

import pytest

from app.core.config import Settings
from app.services.nexus_knowledge import knowledge_disponible, recuperar_conocimiento


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
def test_roles_no_autorizados_no_reciben_archivos_internos(settings: Settings, rol: str) -> None:
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


@pytest.mark.parametrize("rol", ["GESTOR", "USUARIO", "RESPONSABLE", "GERENTE"])
def test_estado_kb_no_anuncia_acceso_a_roles_restringidos(settings: Settings, rol: str) -> None:
    assert knowledge_disponible(settings, rol=rol) is False


def test_estado_kb_administrador_con_acceso(settings: Settings) -> None:
    assert knowledge_disponible(settings, rol="ADMINISTRADOR") is True


def test_conocimiento_de_otro_tenant_no_esta_publicado_en_biblioteca_compartida(
    settings: Settings,
) -> None:
    # La biblioteca compartida solo es documentacion del repositorio.
    # No acepta tenant_id ni tiene fuentes privadas importadas: la consulta
    # operativa debe seguir cerrada a roles no administrativos.
    for rol in ("GESTOR", "USUARIO", "RESPONSABLE", "GERENTE"):
        conocimiento, fuentes = recuperar_conocimiento(
            settings,
            "documentos privados datos empresa cliente",
            "DOCUMENTOS",
            rol=rol,
        )
        assert conocimiento == ""
        assert fuentes == []


def test_el_indicador_kb_no_habilita_acceso_por_su_cuenta(
    settings: Settings,
) -> None:
    assert knowledge_disponible(settings, rol="GESTOR") is False
    conocimiento, fuentes = recuperar_conocimiento(
        settings, "dashboard", "DASHBOARD", rol="GESTOR"
    )
    assert conocimiento == ""
    assert fuentes == []
