from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings
from app.schemas import NexusFuente

DOCUMENTOS_CONOCIMIENTO = (
    "MASTER_PLAN.md",
    "README.md",
    "docs/BUSINESS_RULES.md",
    "docs/DATA_MODEL.md",
    "docs/CORE_ARCHITECTURE.md",
    "docs/futuro/nexus/MULTI_AGENT_SYSTEM.md",
)

PALABRAS_RUTA: dict[str, tuple[str, ...]] = {
    "DASHBOARD": ("dashboard", "indicadores", "alertas", "resumen"),
    "REGISTROS": ("registros", "compras", "filtros", "emisor", "receptor"),
    "DOCUMENTOS": ("documentos", "extraccion", "pdf", "xml", "rhe", "factura"),
    "EXPEDIENTES": ("expediente", "faltantes", "evidencia", "documentos"),
    "EMPRESAS": ("empresa", "proveedor", "cliente", "ruc", "retencion"),
    "ORGANIZACION": ("usuario", "gestor", "gerente", "responsable", "rol"),
    "PRODUCCION": ("produccion", "usuario", "gestor", "compras"),
    "PAGOS": ("pago", "liquidacion", "pedido", "gerencia", "cobro", "saldo"),
    "CONFIGURACION": ("configuracion", "acceso", "permiso", "seguridad"),
}


@dataclass(frozen=True)
class FragmentoConocimiento:
    titulo: str
    texto: str
    archivo: str
    puntaje: int


def knowledge_disponible(settings: Settings) -> bool:
    if not settings.nexus_knowledge_enabled:
        return False
    return any(_resolver_ruta(path) is not None for path in DOCUMENTOS_CONOCIMIENTO)


def recuperar_conocimiento(
    settings: Settings,
    consulta: str,
    seccion: str,
    *,
    max_fragmentos: int = 6,
) -> tuple[str, list[NexusFuente]]:
    if not settings.nexus_knowledge_enabled:
        return "", []

    terminos = _terminos(consulta)
    terminos.update(PALABRAS_RUTA.get(seccion, ()))
    candidatos: list[FragmentoConocimiento] = []

    for relativo in DOCUMENTOS_CONOCIMIENTO:
        ruta = _resolver_ruta(relativo)
        if ruta is None:
            continue
        try:
            contenido = ruta.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for titulo, texto in _secciones(contenido):
            normal = _normalizar(f"{titulo} {texto}")
            puntaje = sum(
                3 if termino in _normalizar(titulo) else 1
                for termino in terminos
                if termino in normal
            )
            if puntaje <= 0:
                continue
            candidatos.append(
                FragmentoConocimiento(
                    titulo=titulo or ruta.name,
                    texto=texto.strip(),
                    archivo=relativo,
                    puntaje=puntaje,
                )
            )

    candidatos.sort(key=lambda item: (item.puntaje, len(item.texto)), reverse=True)
    elegidos = candidatos[:max_fragmentos]
    partes: list[str] = []
    fuentes: list[NexusFuente] = []
    for fragmento in elegidos:
        texto = fragmento.texto
        if len(texto) > 1800:
            texto = texto[:1800].rsplit(" ", 1)[0] + "…"
        partes.append(f"[{fragmento.archivo} · {fragmento.titulo}]\n{texto}")
        fuentes.append(
            NexusFuente(
                titulo=f"{fragmento.archivo} · {fragmento.titulo}",
                tipo="KNOWLEDGE_BASE",
            )
        )
    return "\n\n".join(partes), fuentes


def _resolver_ruta(relativo: str) -> Path | None:
    relativo_path = Path(relativo)
    raices = (
        Path.cwd(),
        Path.cwd().parent,
        Path("/app"),
    )
    for raiz in raices:
        candidato = raiz / relativo_path
        if candidato.is_file():
            return candidato
    return None


def _secciones(contenido: str) -> list[tuple[str, str]]:
    lineas = contenido.splitlines()
    secciones: list[tuple[str, str]] = []
    titulo = "Documento"
    bloque: list[str] = []
    for linea in lineas:
        if re.match(r"^#{1,4}\s+", linea):
            if bloque:
                secciones.append((titulo, "\n".join(bloque).strip()))
            titulo = re.sub(r"^#{1,4}\s+", "", linea).strip()
            bloque = []
        else:
            bloque.append(linea)
    if bloque:
        secciones.append((titulo, "\n".join(bloque).strip()))
    return [(t, b) for t, b in secciones if b]


def _terminos(texto: str) -> set[str]:
    stop = {
        "para", "como", "desde", "donde", "cuando", "porque", "por", "que",
        "una", "uno", "unos", "unas", "del", "las", "los", "con", "sin",
        "esta", "este", "esto", "quiero", "puede", "puedes", "nexus",
    }
    return {
        palabra
        for palabra in re.findall(r"[a-z0-9áéíóúñ]{3,}", _normalizar(texto))
        if palabra not in stop
    }


def _normalizar(texto: str) -> str:
    return (
        texto.lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )
