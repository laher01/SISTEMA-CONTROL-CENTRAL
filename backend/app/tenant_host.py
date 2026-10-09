"""Identificación del tenant por host público (nunca por cabeceras X-Forwarded-Host)."""

import re

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Tenant

SUBDOMINIO_RE = re.compile(r"^[a-z][a-z0-9-]{1,61}[a-z0-9]$")
RESERVADOS = frozenset({"www", "api", "app", "admin", "mail", "smtp", "localhost"})


def validar_subdominio(valor: str) -> str:
    subdominio = valor.strip().lower()
    if subdominio in RESERVADOS or not SUBDOMINIO_RE.fullmatch(subdominio):
        raise ValueError("Subdominio inválido o reservado")
    return subdominio


def nombre_host(request: Request) -> str:
    host = (request.headers.get("host") or "").split(":", 1)[0].strip().lower().rstrip(".")
    return host


def tenant_de_host(request: Request, session: Session, settings: Settings) -> Tenant | None:
    """Solo activa esta ruta para subdominios del dominio explícitamente configurado."""
    raiz = settings.tenant_domain.strip().lower().rstrip(".")
    host = nombre_host(request)
    if not raiz or not host.endswith("." + raiz):
        return None
    subdominio = host[: -len(raiz) - 1]
    if "." in subdominio:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Administración no encontrada")
    tenant = session.scalar(select(Tenant).where(Tenant.subdominio == subdominio))
    if tenant is None or tenant.estado != "ACTIVO":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Administración no encontrada")
    return tenant


def validar_sesion_host(
    request: Request, session: Session, settings: Settings, tenant_id: object
) -> None:
    tenant = tenant_de_host(request, session, settings)
    if tenant is not None and tenant.id != tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sesión de otra Administración")
