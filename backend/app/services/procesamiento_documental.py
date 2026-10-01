import csv
import io
import shutil
import subprocess
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.enums import TipoDocumento


class DocumentoNoProcesable(Exception):
    pass


@dataclass(frozen=True)
class SugerenciaClasificacion:
    tipo: TipoDocumento
    confianza: float
    indicadores: tuple[str, ...]

    def a_dict(self) -> dict[str, object]:
        return {
            "tipo": self.tipo,
            "confianza": self.confianza,
            "indicadores": list(self.indicadores),
            "requiere_confirmacion": True,
        }


@dataclass(frozen=True)
class ResultadoProcesamiento:
    texto: str
    metodo: str
    motor: str
    paginas: int
    confianza: float | None = None
    idioma: str | None = None
    requiere_ocr: bool = False
    sugerencia: SugerenciaClasificacion | None = None

    def a_dict(self) -> dict[str, object]:
        resultado: dict[str, object] = {
            "texto": self.texto,
            "metodo": self.metodo,
            "motor": self.motor,
            "paginas": self.paginas,
            "requiere_ocr": self.requiere_ocr,
        }
        if self.confianza is not None:
            resultado["confianza"] = self.confianza
        if self.idioma is not None:
            resultado["idioma"] = self.idioma
        if self.sugerencia is not None:
            resultado["clasificacion_sugerida"] = self.sugerencia.a_dict()
        return resultado


def procesar(contenido: bytes, limite_caracteres: int) -> ResultadoProcesamiento:
    if contenido.startswith(b"%PDF-"):
        return _procesar_pdf(contenido, limite_caracteres)
    extension = _extension_imagen(contenido)
    if extension is not None:
        return _procesar_imagen(contenido, extension, limite_caracteres)
    raise DocumentoNoProcesable("Solo se admite procesamiento de PDF, JPEG, PNG, TIFF o WEBP")


def _procesar_pdf(contenido: bytes, limite: int) -> ResultadoProcesamiento:
    try:
        lector = PdfReader(io.BytesIO(contenido), strict=False)
        if lector.is_encrypted and lector.decrypt("") == 0:
            raise DocumentoNoProcesable("El PDF está protegido con contraseña")
        partes = [(pagina.extract_text() or "").strip() for pagina in lector.pages]
    except (PdfReadError, OSError, ValueError) as exc:
        raise DocumentoNoProcesable("El PDF está dañado o no tiene una estructura válida") from exc
    texto = _limitar("\n\n".join(parte for parte in partes if parte), limite)
    return ResultadoProcesamiento(
        texto=texto,
        metodo="TEXTO_PDF",
        motor="pypdf",
        paginas=len(lector.pages),
        confianza=1.0 if texto else None,
        requiere_ocr=not bool(texto),
        sugerencia=sugerir_tipo(texto),
    )


def _procesar_imagen(contenido: bytes, extension: str, limite: int) -> ResultadoProcesamiento:
    ejecutable = shutil.which("tesseract")
    if ejecutable is None:
        raise DocumentoNoProcesable(
            "Tesseract OCR no está instalado; el original permanece guardado para reprocesarlo"
        )
    idioma = _idioma_disponible(ejecutable)
    with tempfile.TemporaryDirectory(prefix="fact-central-ocr-") as temporal:
        entrada = Path(temporal) / f"entrada{extension}"
        entrada.write_bytes(contenido)
        try:
            proceso = subprocess.run(
                [ejecutable, str(entrada), "stdout", "-l", idioma, "tsv"],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise DocumentoNoProcesable("El OCR excedió el tiempo máximo de procesamiento") from exc
    if proceso.returncode != 0:
        detalle = proceso.stderr.strip().splitlines()
        mensaje = detalle[-1][:300] if detalle else "error desconocido"
        raise DocumentoNoProcesable(f"Tesseract no pudo procesar la imagen: {mensaje}")
    texto, confianza = _leer_tsv(proceso.stdout, limite)
    return ResultadoProcesamiento(
        texto=texto,
        metodo="OCR_IMAGEN",
        motor="tesseract",
        paginas=1,
        confianza=confianza,
        idioma=idioma,
        sugerencia=sugerir_tipo(texto),
    )


def _idioma_disponible(ejecutable: str) -> str:
    resultado = subprocess.run(
        [ejecutable, "--list-langs"], capture_output=True, text=True, timeout=15, check=False
    )
    idiomas = set(resultado.stdout.split())
    if "spa" in idiomas and "eng" in idiomas:
        return "spa+eng"
    if "spa" in idiomas:
        return "spa"
    if "eng" in idiomas:
        return "eng"
    raise DocumentoNoProcesable("Tesseract no tiene instalado un idioma compatible")


def _leer_tsv(tsv: str, limite: int) -> tuple[str, float | None]:
    palabras: list[str] = []
    confianzas: list[float] = []
    for fila in csv.DictReader(io.StringIO(tsv), delimiter="\t"):
        palabra = (fila.get("text") or "").strip()
        if not palabra:
            continue
        palabras.append(palabra)
        try:
            confianza = float(fila.get("conf", "-1"))
        except ValueError:
            continue
        if confianza >= 0:
            confianzas.append(confianza)
    texto = _limitar(" ".join(palabras), limite)
    promedio = round(sum(confianzas) / len(confianzas) / 100, 4) if confianzas else None
    return texto, promedio


def sugerir_tipo(texto: str) -> SugerenciaClasificacion | None:
    normalizado = _normalizar(texto)
    reglas: tuple[tuple[TipoDocumento, tuple[str, ...]], ...] = (
        (TipoDocumento.RET, ("COMPROBANTE DE RETENCION", "CONSTANCIA DE RETENCION")),
        (TipoDocumento.GRR, ("GUIA DE REMISION REMITENTE", "GUIA DE REMISION ELECTRONICA")),
        (TipoDocumento.RHE, ("RECIBO POR HONORARIOS",)),
        (TipoDocumento.FACT, ("FACTURA ELECTRONICA", "FACTURA DE VENTA")),
        (TipoDocumento.OC, ("ORDEN DE COMPRA",)),
        (TipoDocumento.COT, ("COTIZACION",)),
        (TipoDocumento.VCHR, ("CONSTANCIA DE PAGO", "TRANSFERENCIA", "OPERACION EXITOSA")),
    )
    for tipo, indicadores in reglas:
        encontrados = tuple(indicador for indicador in indicadores if indicador in normalizado)
        if encontrados:
            confianza = min(0.95, 0.65 + 0.15 * len(encontrados))
            return SugerenciaClasificacion(tipo, confianza, encontrados)
    return None


def _extension_imagen(contenido: bytes) -> str | None:
    if contenido.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if contenido.startswith((b"II*\x00", b"MM\x00*")):
        return ".tiff"
    if contenido.startswith(b"RIFF") and contenido[8:12] == b"WEBP":
        return ".webp"
    return None


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto)
    return " ".join("".join(c for c in sin_tildes if not unicodedata.combining(c)).upper().split())


def _limitar(texto: str, limite: int) -> str:
    return texto[:limite]
