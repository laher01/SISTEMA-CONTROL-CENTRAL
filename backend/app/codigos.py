"""Códigos visibles únicos por Administración y rol; UUID conserva identidad real."""

import re
import unicodedata
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Gestor, Miembro

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
    prefijo = "".join(p[0] for p in partes[:3])
    return (prefijo + "XXX")[:3]


def codigo_automatico(
    session: Session, tenant_id: uuid.UUID, nombre: str, rol: str
) -> str:
    prefijo = iniciales(nombre)
    sufijo = SUFIJOS[rol]
    # Comparar también cuentas de Gestor para no reutilizar logins dentro del tenant.
    codigos = set(
        session.scalars(select(Miembro.codigo).where(Miembro.tenant_id == tenant_id)).all()
    )
    codigos.update(
        session.scalars(select(Gestor.codigo).where(Gestor.tenant_id == tenant_id)).all()
    )
    for numero in range(1, 10000):
        candidato = f"{prefijo}-{numero:03d}-{sufijo}"
        if candidato not in codigos:
            return candidato
    raise ValueError("Numeración de códigos agotada")
