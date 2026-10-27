"""Política MISD de autorización para eliminación definitiva.

La ventana de corrección no deroga las reglas de pagos, ámbito, ni conservación.
"""

from datetime import UTC, datetime, timedelta

from app.models import Expediente

VENTANA_CORRECCION = timedelta(minutes=30)


def dentro_ventana_correccion(expediente: Expediente, instante: datetime) -> bool:
    """La ventana comienza al constituirse el expediente, no al adjuntar archivos."""
    creado = expediente.created_at
    if creado.tzinfo is None:
        creado = creado.replace(tzinfo=UTC)
    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=UTC)
    transcurrido = instante - creado
    return timedelta(0) <= transcurrido <= VENTANA_CORRECCION


def roles_aprobadores(rol_solicitante: str) -> tuple[str, ...]:
    """Jerarquía de solicitud para retiros fuera de la ventana inicial."""
    if rol_solicitante == "GESTOR":
        return ("USUARIO", "RESPONSABLE", "ADMINISTRADOR")
    if rol_solicitante == "USUARIO":
        return ("RESPONSABLE", "ADMINISTRADOR")
    if rol_solicitante in ("RESPONSABLE", "ADMINISTRADOR"):
        return ()
    return ()


def politica_retiro(
    expediente: Expediente,
    rol: str,
    instante: datetime,
    bloqueado_por_pago: bool,
) -> dict[str, object]:
    """Previsualiza autorizaciones sin conceder permiso de eliminación."""
    ventana = dentro_ventana_correccion(expediente, instante)
    aprobadores = roles_aprobadores(rol)
    rol_permitido = rol in (
        "ADMINISTRADOR",
        "RESPONSABLE",
        "USUARIO",
        "GESTOR",
    )
    return {
        "bloqueado_por_pago": bloqueado_por_pago,
        "dentro_ventana_correccion": ventana,
        "puede_solicitar": rol_permitido and not bloqueado_por_pago,
        "requiere_aprobacion": (
            rol_permitido and not bloqueado_por_pago and not ventana and bool(aprobadores)
        ),
        "roles_aprobadores": list(aprobadores) if not ventana else [],
    }
