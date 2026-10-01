import uuid
from pathlib import Path


class AlmacenLocal:
    """Guarda originales inmutables, direccionados por su SHA-256."""

    def __init__(self, base: Path) -> None:
        self.base = base

    def guardar(self, tenant_id: uuid.UUID, sha256: str, contenido: bytes) -> str:
        relativa = Path(str(tenant_id)) / sha256[:2] / sha256
        destino = self.base / relativa
        if not destino.exists():
            destino.parent.mkdir(parents=True, exist_ok=True)
            temporal = destino.with_suffix(".tmp")
            temporal.write_bytes(contenido)
            temporal.replace(destino)
        return relativa.as_posix()

    def leer(self, ruta: str) -> bytes:
        return (self.base / ruta).read_bytes()
