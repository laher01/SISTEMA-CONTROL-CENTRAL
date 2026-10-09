"""Códigos visibles únicos por Administración y rol; UUID conserva identidad real."""

import re
import unicodedata
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CuentaAcceso, Gestor, Miembro

SUFIJOS = {
    "ADMINISTRADOR": "ADM",
    "GERENTE": "GER",
    "SECRETARIA": "SEC",
    "RESPONSABLE": "RES",
    "USUARIO": "US",
    "GESTOR": "GES",
}


def iniciales(nombre: str) -> str:
    texto = unicodedata.normalize("NFKD", nombre.upper())
    letras = "".join(c for c in texto if not unicodedata.combining(c))
    partes = re.findall(r"[A-Z]+", letras)
    if len(partes) >= 3:
        return "".join(parte[0] for parte in partes[:3])
    if len(partes) == 2:
        return (partes[0][:2] + partes[1][:1]).ljust(3, "X")
    return (partes[0][:3] if partes else "XXX").ljust(3, "X")


def codigo_automatico(session: Session, tenant_id: uuid.UUID, nombre: str, rol: str) -> str:
    prefijo = iniciales(nombre)
    sufijo = SUFIJOS[rol]
    # Comparar también cuentas de Gestor para no reutilizar logins dentro del tenant.
    codigos = set(
        session.scalars(select(Miembro.codigo).where(Miembro.tenant_id == tenant_id)).all()
    )
    codigos.update(
        session.scalars(select(Gestor.codigo).where(Gestor.tenant_id == tenant_id)).all()
    )
    codigos.update(
        session.scalars(select(CuentaAcceso.login).where(CuentaAcceso.tenant_id == tenant_id)).all()
    )
    for numero in range(1, 10000):
        candidato = f"{prefijo}-{numero:03d}-{sufijo}"
        if candidato not in codigos:
            return candidato
    raise ValueError("Numeración de códigos agotada")
