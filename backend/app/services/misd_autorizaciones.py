"""Política operativa de eliminación definitiva por jerarquía."""

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
    """Solo el Responsable eleva una solicitud a Administración."""
    return ("ADMINISTRADOR",) if rol_solicitante == "RESPONSABLE" else ()


def politica_retiro(
    expediente: Expediente,
    rol: str,
    instante: datetime,
    bloqueado_por_pago: bool,
) -> dict[str, object]:
    """Describe el flujo actual; pagos y antigüedad no bloquean la eliminación."""
    ventana = dentro_ventana_correccion(expediente, instante)
    aprobadores = roles_aprobadores(rol)
    puede_eliminar = rol in ("ADMINISTRADOR", "USUARIO", "GESTOR")
    return {
        "bloqueado_por_pago": False,
        "dentro_ventana_correccion": ventana,
        "puede_solicitar": rol == "RESPONSABLE",
        "puede_eliminar_directamente": puede_eliminar,
        "requiere_aprobacion": rol == "RESPONSABLE",
        "roles_aprobadores": list(aprobadores),
    }
