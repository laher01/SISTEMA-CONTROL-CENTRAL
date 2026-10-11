"""Reglas puras de admisión documental; ninguna operación de base de datos.

El acceso a una entidad se autoriza adicionalmente por tenant y ámbito en el
servicio llamador. Esta política NO habilita expedientes por sí sola.
"""

from dataclasses import dataclass
from enum import StrEnum


class DecisionCorreo(StrEnum):
    RECHAZAR_REMITENTE = "RECHAZAR_REMITENTE"
    PENDIENTE_GESTOR = "PENDIENTE_GESTOR"
    PENDIENTE_RECEPTOR = "PENDIENTE_RECEPTOR"
    ACEPTAR_PARA_INGESTA = "ACEPTAR_PARA_INGESTA"


@dataclass(frozen=True)
class AutorizacionCorreo:
    remitente_autorizado: bool
    gestor_ids_validos: frozenset[str]
    ruc_receptor: str | None
    receptores_autorizados: frozenset[str]


def decidir_recepcion(datos: AutorizacionCorreo) -> DecisionCorreo:
    """Fail closed: require registered sender, unique manager and known receiver.

    IDs and RUCs here MUST already be filtered by tenant and authorized scope.
    No extraction of untrusted attachments should run before sender admission.
    """
    if not datos.remitente_autorizado:
        return DecisionCorreo.RECHAZAR_REMITENTE
    if len(datos.gestor_ids_validos) != 1:
        return DecisionCorreo.PENDIENTE_GESTOR
    if not datos.ruc_receptor or datos.ruc_receptor not in datos.receptores_autorizados:
        return DecisionCorreo.PENDIENTE_RECEPTOR
    return DecisionCorreo.ACEPTAR_PARA_INGESTA


def puede_administrar_buzon(rol: str) -> bool:
    return rol == "ADMINISTRADOR"


def puede_registrar_remitente(rol: str) -> bool:
    return rol == "ADMINISTRADOR"


def puede_habilitar_empresa(rol: str) -> bool:
    return rol in {"SUPERADMIN", "ADMINISTRADOR", "GERENTE", "RESPONSABLE"}
