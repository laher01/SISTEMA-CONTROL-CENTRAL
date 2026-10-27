"""Política MISD de autorización: diagnóstico, sin ejecutar borrados.

La ventana de corrección no deroga las reglas de pagos, ámbito, ni conservación.
"""

from datetime import UTC, datetime, timedelta

from app.models import Documento, Expediente

VENTANA_CORRECCION = timedelta(minutes=30)


def dentro_ventana_correccion(expediente: Expediente, instante: datetime) -> bool:
    """La ventana comienza al constituirse el expediente, no al adjuntar archivos."""
    transcurrido = _en_utc(instante) - _en_utc(expediente.created_at)
    return timedelta(0) <= transcurrido <= VENTANA_CORRECCION


def dentro_ventana_documento(documento: Documento, instante: datetime) -> bool:
    """Repite la misma regla de retirada para documentos sin expediente."""
    origen = (
        documento.expediente.created_at
        if documento.expediente is not None
        else documento.created_at
    )
    transcurrido = _en_utc(instante) - _en_utc(origen)
    return timedelta(0) <= transcurrido <= VENTANA_CORRECCION


def _en_utc(valor: datetime) -> datetime:
    """SQLite devuelve timestamps naive aunque el modelo sea timezone-aware."""
    if valor.tzinfo is None:
        return valor.replace(tzinfo=UTC)
    return valor.astimezone(UTC)


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
