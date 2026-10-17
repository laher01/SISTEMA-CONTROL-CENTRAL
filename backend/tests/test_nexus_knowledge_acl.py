"""Pruebas del contrato de aislamiento de futura memoria privada NEXUS."""

import uuid

import pytest

from app.services.nexus_knowledge_acl import (
    ActorConocimiento,
    PermisoConocimiento,
    Visibilidad,
    acceso_conocimiento,
)


@pytest.fixture
def ids() -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    return uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


def test_otro_tenant_nunca_ve_documento_aunque_sea_admin(
    ids: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    tenant, usuario, ajeno = ids
    recurso = PermisoConocimiento(tenant, usuario, Visibilidad.TENANT, aprobado=True)
    actor = ActorConocimiento(ajeno, usuario, "SUPERADMIN")
    assert acceso_conocimiento(actor, recurso) is False


@pytest.mark.parametrize("visibilidad", list(Visibilidad))
def test_revocado_o_no_aprobado_no_se_recupera(
    ids: tuple[uuid.UUID, uuid.UUID, uuid.UUID], visibilidad: Visibilidad
) -> None:
    tenant, usuario, _ = ids
    actor = ActorConocimiento(tenant, usuario, "GESTOR")
    for revocado, aprobado in ((True, True), (False, False)):
        recurso = PermisoConocimiento(
            tenant, usuario, visibilidad, frozenset({"GESTOR"}), revocado, aprobado
        )
        assert acceso_conocimiento(actor, recurso) is False


def test_privado_solo_propietario(ids: tuple[uuid.UUID, uuid.UUID, uuid.UUID]) -> None:
    tenant, usuario, otro = ids
    recurso = PermisoConocimiento(tenant, usuario, Visibilidad.PRIVADA, aprobado=True)
    assert acceso_conocimiento(ActorConocimiento(tenant, usuario, "USUARIO"), recurso)
    assert not acceso_conocimiento(ActorConocimiento(tenant, otro, "ADMINISTRADOR"), recurso)


def test_visibilidad_por_rol(ids: tuple[uuid.UUID, uuid.UUID, uuid.UUID]) -> None:
    tenant, usuario, otro = ids
    recurso = PermisoConocimiento(
        tenant, usuario, Visibilidad.ROL, frozenset({"GESTOR"}), aprobado=True
    )
    assert acceso_conocimiento(ActorConocimiento(tenant, otro, "GESTOR"), recurso)
    assert not acceso_conocimiento(ActorConocimiento(tenant, otro, "USUARIO"), recurso)


def test_visibilidad_tenant_para_usuarios_del_mismo_tenant(
    ids: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    tenant, usuario, otro = ids
    recurso = PermisoConocimiento(tenant, usuario, Visibilidad.TENANT, aprobado=True)
    assert acceso_conocimiento(ActorConocimiento(tenant, otro, "USUARIO"), recurso)
