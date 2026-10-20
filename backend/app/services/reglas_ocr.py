"""Reglas declarativas OCR: nunca ejecuta código, comandos ni consultas arbitrarias."""

import re

CAMPOS = frozenset({"serie", "correlativo", "ruc_emisor", "ruc_receptor"})
FORMATO = re.compile(r"^[A-Z0-9_-]{2,80}$")


def validar_definicion(definicion: dict[str, object]) -> dict[str, str]:
    """Un subconjunto seguro de reglas: coincidencia exacta de texto; solo vista previa."""
    if set(definicion) != {"campo", "patron", "valor"}:
        raise ValueError("La regla solo admite campo, patron y valor")
    campo, patron, valor = (definicion[k] for k in ("campo", "patron", "valor"))
    if not isinstance(campo, str) or campo not in CAMPOS:
        raise ValueError("Campo no permitido")
    if not isinstance(patron, str) or not 2 <= len(patron) <= 80:
        raise ValueError("Patrón inválido")
    if not isinstance(valor, str) or not FORMATO.fullmatch(valor):
        raise ValueError("Valor inválido")
    if campo == "serie" and len(valor) != 4:
        raise ValueError("Serie de cuatro caracteres requerida")
    if campo == "correlativo" and (not valor.isdigit() or len(valor) > 32):
        raise ValueError("Correlativo inválido")
    if campo.startswith("ruc_") and (not valor.isdigit() or len(valor) != 11):
        raise ValueError("RUC inválido")
    return {"campo": campo, "patron": patron, "valor": valor}


def vista_previa_regla(definicion: dict[str, object], texto: str) -> dict[str, str] | None:
    """Solo una sugerencia; nunca modifica extracción ni documento."""
    regla = validar_definicion(definicion)
    if regla["patron"] not in texto:
        return None
    return {"campo": regla["campo"], "valor_propuesto": regla["valor"]}
