"""Detección conservadora de vouchers físicos en una foto compuesta."""

from __future__ import annotations

import re
import shutil
import statistics
import subprocess
import tempfile
import unicodedata
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_PIXELES_IMAGEN = 40_000_000
MAX_LADO_ANALISIS = 1_200
MIN_AREA_VOUCHER = 0.025


@dataclass(frozen=True)
class SegmentacionVouchers:
    estado: str
    cajas: tuple[tuple[int, int, int, int], ...] = ()
    confianza: float | None = None
    motivo: str | None = None


@dataclass(frozen=True)
class _Componente:
    caja: tuple[int, int, int, int]
    pixeles: int


def detectar_vouchers(contenido: bytes) -> SegmentacionVouchers:
    """Devuelve recortes solo cuando aparecen varias hojas separadas con claridad.

    La segmentación se basa en el soporte físico de las hojas y sus separaciones,
    nunca en importes ni en el nombre del archivo. Los fondos claros, las hojas
    solapadas o los límites débiles quedan para revisión sin generar recortes.
    """
    try:
        with Image.open(BytesIO(contenido)) as original:
            imagen_original = ImageOps.exif_transpose(original).convert("RGB")
            ancho, alto = imagen_original.size
            if ancho <= 0 or alto <= 0 or ancho * alto > MAX_PIXELES_IMAGEN:
                return SegmentacionVouchers("REVISION", motivo="Tamaño de imagen no seguro")
            escala = min(1.0, MAX_LADO_ANALISIS / max(ancho, alto))
            if escala < 1.0:
                reducido = imagen_original.resize(
                    (max(1, round(ancho * escala)), max(1, round(alto * escala))),
                    Image.Resampling.LANCZOS,
                )
            else:
                reducido = imagen_original.copy()
            gris = ImageOps.grayscale(reducido)
            umbral = min(205, max(150, _umbral_otsu(gris) + 40))
            mascara = gris.point(lambda pixel: 255 if pixel >= umbral else 0, mode="1")
            componentes = _componentes(mascara)
            area = mascara.width * mascara.height
            grandes = [c for c in componentes if c.pixeles >= area * MIN_AREA_VOUCHER]
            hojas: list[tuple[tuple[int, int, int, int], float]] = []
            for componente in grandes:
                hojas.extend(_dividir_componente(mascara, componente, area))
            hojas = _quitar_duplicados(hojas)
            if len(hojas) < 2:
                hojas = _detectar_por_texto(gris)
            if len(hojas) == 1:
                caja_unica, confianza_unica = hojas[0]
                x0, y0, x1, y1 = caja_unica
                if (x1 - x0) * (y1 - y0) >= area * 0.68:
                    return SegmentacionVouchers(
                        "REVISION",
                        motivo="El fondo no permite confirmar si hay uno o varios vouchers",
                    )
                return SegmentacionVouchers(
                    "UNA_IMAGEN", (caja_unica,), round(confianza_unica, 4)
                )
            if not 2 <= len(hojas) <= 30:
                return SegmentacionVouchers(
                    "REVISION",
                    motivo=(
                        "No se pudieron confirmar al menos dos límites de voucher; "
                        "se conserva la foto completa"
                    ),
                )
            hojas.sort(key=lambda elemento: (elemento[0][1], elemento[0][0]))
            if min(confianza for _, confianza in hojas) < 0.72:
                return SegmentacionVouchers(
                    "REVISION",
                    motivo="Uno o más límites tienen poca confianza; se conserva la foto completa",
                )
            cajas: list[tuple[int, int, int, int]] = []
            factor_x = ancho / mascara.width
            factor_y = alto / mascara.height
            for (x0, y0, x1, y1), _ in hojas:
                margen_x = max(3, round((x1 - x0) * 0.025))
                margen_y = max(3, round((y1 - y0) * 0.025))
                caja = (
                    max(0, x0 - margen_x),
                    max(0, y0 - margen_y),
                    min(mascara.width, x1 + margen_x),
                    min(mascara.height, y1 + margen_y),
                )
                cajas.append(
                    (
                        max(0, round(caja[0] * factor_x)),
                        max(0, round(caja[1] * factor_y)),
                        min(ancho, round(caja[2] * factor_x)),
                        min(alto, round(caja[3] * factor_y)),
                    )
                )
            confianza = round(min(confianza for _, confianza in hojas), 4)
            return SegmentacionVouchers("SEPARAR", tuple(cajas), confianza)
    except (OSError, ValueError, UnidentifiedImageError):
        return SegmentacionVouchers("REVISION", motivo="No se pudo analizar la imagen")


def recortar_voucher(contenido: bytes, caja: tuple[int, int, int, int]) -> bytes:
    """Genera una copia JPEG del recorte sin modificar el original."""
    with Image.open(BytesIO(contenido)) as original:
        imagen = ImageOps.exif_transpose(original).convert("RGB")
        recorte = imagen.crop(caja)
        salida = BytesIO()
        recorte.save(salida, format="JPEG", quality=94, optimize=True)
        return salida.getvalue()


def _umbral_otsu(gris: Image.Image) -> int:
    histograma = gris.histogram()
    total = sum(histograma)
    suma_total = sum(indice * cantidad for indice, cantidad in enumerate(histograma))
    peso_fondo = 0
    suma_fondo = 0
    mejor_varianza = -1.0
    mejor_umbral = 128
    for umbral, cantidad in enumerate(histograma):
        peso_fondo += cantidad
        suma_fondo += umbral * cantidad
        peso_objeto = total - peso_fondo
        if not peso_fondo or not peso_objeto:
            continue
        media_fondo = suma_fondo / peso_fondo
        media_objeto = (suma_total - suma_fondo) / peso_objeto
        varianza = peso_fondo * peso_objeto * (media_fondo - media_objeto) ** 2
        if varianza > mejor_varianza:
            mejor_varianza = varianza
            mejor_umbral = umbral
    return mejor_umbral


def _detectar_por_texto(
    gris: Image.Image,
) -> list[tuple[tuple[int, int, int, int], float]]:
    """Respaldo OCR para comprobantes apilados sobre fondo claro de bajo contraste."""
    if gris.height < gris.width * 1.15:
        return []
    ejecutable = shutil.which("tesseract")
    if ejecutable is None:
        return []
    mejorada = ImageOps.autocontrast(gris, cutoff=1)
    ancho, alto = mejorada.size
    conteos: list[int] = []
    lineas = _datos(mejorada)
    for y in range(alto):
        fila = lineas[y * ancho : (y + 1) * ancho]
        conteos.append(sum(1 for pixel in fila if pixel < 70))
    minimo = max(4, round(ancho * 0.003))
    activas = [y for y, cuenta in enumerate(conteos) if cuenta >= minimo]
    grupos: list[list[int]] = []
    for y in activas:
        if not grupos or y - grupos[-1][-1] > 55:
            grupos.append([y])
        else:
            grupos[-1].append(y)
    candidatos = [
        (grupo[0], grupo[-1] + 1)
        for grupo in grupos
        if len(grupo) >= 8
        and grupo[-1] - grupo[0] >= 50
        and sum(conteos[y] for y in grupo) >= ancho * 0.012
    ]
    if not 2 <= len(candidatos) <= 8:
        return []

    idiomas_proceso = subprocess.run(
        [ejecutable, "--list-langs"], capture_output=True, text=True, timeout=10, check=False
    )
    idiomas = set(idiomas_proceso.stdout.split())
    idioma = "spa+eng" if {"spa", "eng"} <= idiomas else "spa" if "spa" in idiomas else "eng"

    # No se decide por proximidad ni por nombre: cada banda debe contener OCR
    # independiente de operación y fecha antes de autorizar sus propios recortes.
    validos: list[tuple[int, int, tuple[int, int, int, int], float]] = []
    for inicio, fin in candidatos:
        alto_grupo = fin - inicio
        margen_y = max(50, round(alto_grupo * 0.85))
        y0 = max(0, inicio - margen_y)
        y1 = min(alto, fin + margen_y)
        if y1 - y0 < 100:
            continue
        x0, x1 = _bordes_ink(mejorada, inicio, fin)
        margen_x = max(25, round((x1 - x0) * 0.35))
        caja = (max(0, x0 - margen_x), y0, min(ancho, x1 + margen_x), y1)
        texto, confianza_ocr = _leer_banda_ocr(ejecutable, idioma, mejorada.crop(caja))
        if _es_voucher_identificable(texto):
            validos.append((inicio, fin, caja, confianza_ocr))
    if len(validos) < 2:
        return []

    resultado: list[tuple[tuple[int, int, int, int], float]] = []
    for indice, (inicio, fin, caja, confianza) in enumerate(validos):
        x0, _, x1, _ = caja
        margen_grupo = max(25, round((fin - inicio) * 0.2))
        if indice:
            corte_anterior = (validos[indice - 1][1] + inicio) // 2
            y0 = corte_anterior + margen_grupo
        else:
            y0 = max(0, inicio - margen_grupo)
        if indice + 1 < len(validos):
            corte_siguiente = (fin + validos[indice + 1][0]) // 2
            y1 = corte_siguiente + margen_grupo
        else:
            y1 = alto
        caja_final = (x0, max(0, y0), x1, min(alto, y1))
        if caja_final[3] - caja_final[1] >= 100:
            resultado.append((caja_final, round(min(0.86, 0.72 + confianza * 0.14), 4)))
    return resultado if len(resultado) == len(validos) else []


def _bordes_ink(gris: Image.Image, inicio: int, fin: int) -> tuple[int, int]:
    ancho, _ = gris.size
    conteos = [0] * ancho
    recorte = gris.crop((0, inicio, ancho, fin))
    for indice, pixel in enumerate(_datos(recorte)):
        if pixel < 70:
            conteos[indice % ancho] += 1
    columnas = [x for x, cuenta in enumerate(conteos) if cuenta >= 2]
    if not columnas:
        return 0, ancho
    return columnas[0], columnas[-1] + 1


def _leer_banda_ocr(ejecutable: str, idioma: str, banda: Image.Image) -> tuple[str, float]:
    escala = min(2.0, 1_800 / max(1, banda.width))
    preparada = ImageOps.autocontrast(banda, cutoff=1).resize(
        (max(1, round(banda.width * escala)), max(1, round(banda.height * escala))),
        Image.Resampling.LANCZOS,
    )
    directorio = Path(tempfile.mkdtemp(prefix="voucher-ocr-"))
    ruta = directorio / "banda.png"
    try:
        preparada.save(ruta, format="PNG")
        proceso = subprocess.run(
            [ejecutable, str(ruta), "stdout", "-l", idioma, "--psm", "6"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        texto = proceso.stdout[:12_000] if proceso.returncode == 0 else ""
        palabras = [palabra for palabra in texto.split() if len(palabra) > 1]
        return texto, min(1.0, len(palabras) / 35)
    except (OSError, subprocess.SubprocessError):
        return "", 0.0
    finally:
        ruta.unlink(missing_ok=True)
        directorio.rmdir()


def _es_voucher_identificable(texto: str) -> bool:
    normalizado = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().upper()
    operacion = re.search(r"\bOP\s*[-.:/]?\s*\d{5,}\b", normalizado)
    fecha = re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b", normalizado)
    tipo = any(palabra in normalizado for palabra in ("DEPOSITO", "TRANSFERENCIA", "ABONO"))
    return operacion is not None and fecha is not None and tipo


def _componentes(mascara: Image.Image) -> list[_Componente]:
    """Etiqueta componentes con escaneo de tramos 4-conexos, sin librerías externas."""
    padres: list[int] = []
    tramos: list[tuple[int, int, int]] = []
    previos: list[tuple[int, int, int]] = []
    pixeles = _datos(mascara)
    for y in range(mascara.height):
        fila = pixeles[y * mascara.width : (y + 1) * mascara.width]
        actuales: list[tuple[int, int, int]] = []
        x = 0
        indice_previo = 0
        while x < mascara.width:
            while x < mascara.width and not fila[x]:
                x += 1
            inicio = x
            while x < mascara.width and fila[x]:
                x += 1
            if inicio == x:
                continue
            nodo = len(padres)
            padres.append(nodo)
            tramos.append((inicio, x, y))
            while indice_previo < len(previos) and previos[indice_previo][1] <= inicio:
                indice_previo += 1
            indice = indice_previo
            while indice < len(previos) and previos[indice][0] < x:
                _unir(padres, nodo, previos[indice][2])
                indice += 1
            actuales.append((inicio, x, nodo))
        previos = actuales

    limites: dict[int, list[int]] = {}
    for (x0, x1, y), nodo in zip(tramos, range(len(tramos)), strict=True):
        raiz = _raiz(padres, nodo)
        dato = limites.get(raiz)
        if dato is None:
            limites[raiz] = [x0, y, x1, y + 1, x1 - x0]
        else:
            dato[0] = min(dato[0], x0)
            dato[1] = min(dato[1], y)
            dato[2] = max(dato[2], x1)
            dato[3] = max(dato[3], y + 1)
            dato[4] += x1 - x0
    return [
        _Componente((dato[0], dato[1], dato[2], dato[3]), dato[4]) for dato in limites.values()
    ]


def _dividir_componente(
    mascara: Image.Image,
    componente: _Componente,
    area_total: int,
    profundidad: int = 0,
) -> list[tuple[tuple[int, int, int, int], float]]:
    caja = componente.caja
    if profundidad < 4:
        candidato = _mejor_corte(mascara, caja)
        if candidato is not None:
            eje, posicion, confianza = candidato
            x0, y0, x1, y1 = caja
            if eje == "x":
                cajas_hijas = ((x0, y0, posicion, y1), (posicion, y0, x1, y1))
            else:
                cajas_hijas = ((x0, y0, x1, posicion), (x0, posicion, x1, y1))
            hijas: list[_Componente] = []
            for hija in cajas_hijas:
                pixeles = _contar(mascara, hija)
                if pixeles < area_total * MIN_AREA_VOUCHER:
                    break
                hijas.append(_Componente(hija, pixeles))
            if len(hijas) == 2:
                resultado: list[tuple[tuple[int, int, int, int], float]] = []
                for caja_hija in hijas:
                    resultado.extend(
                        _dividir_componente(mascara, caja_hija, area_total, profundidad + 1)
                    )
                if len(resultado) >= 2:
                    return [
                        (caja_hija, min(confianza, conf_hija))
                        for caja_hija, conf_hija in resultado
                    ]
    ajustada = _caja_ajustada(mascara, caja)
    if ajustada is None:
        return []
    x0, y0, x1, y1 = ajustada
    ancho = x1 - x0
    alto = y1 - y0
    densidad = _contar(mascara, ajustada) / max(1, ancho * alto)
    proporcion = ancho / max(1, alto)
    if ancho * alto < area_total * MIN_AREA_VOUCHER or not 0.35 <= proporcion <= 2.6:
        return []
    if densidad < 0.62:
        return []
    confianza = min(0.96, 0.72 + (densidad - 0.62) * 0.5)
    return [(ajustada, confianza)]


def _mejor_corte(
    mascara: Image.Image, caja: tuple[int, int, int, int]
) -> tuple[str, int, float] | None:
    x0, y0, x1, y1 = caja
    ancho = x1 - x0
    alto = y1 - y0
    candidatos: list[tuple[float, str, int]] = []
    for eje, longitud, area_ortogonal in (("x", ancho, alto), ("y", alto, ancho)):
        if longitud < 150:
            continue
        pixeles = [0] * longitud
        if eje == "x":
            recorte = mascara.crop(caja)
            valores = _datos(recorte)
            for indice, encendido in enumerate(valores):
                if encendido:
                    pixeles[indice % ancho] += 1
        else:
            recorte = mascara.crop(caja)
            valores = _datos(recorte)
            for indice, encendido in enumerate(valores):
                if encendido:
                    pixeles[indice // ancho] += 1
        perfil = [valor / max(1, area_ortogonal) for valor in pixeles]
        ventana = max(3, round(longitud * 0.008))
        inicio = max(1, round(longitud * 0.08))
        fin = min(longitud - ventana - 1, round(longitud * 0.92))
        if fin <= inicio:
            continue
        prefijo: list[float] = [0.0]
        for valor in perfil:
            prefijo.append(prefijo[-1] + valor)
        mejor_posicion = inicio
        mejor_media = 1.0
        for indice in range(inicio, fin):
            media = (prefijo[indice + ventana] - prefijo[indice]) / ventana
            if media < mejor_media:
                mejor_media = media
                mejor_posicion = indice + ventana // 2
        base = statistics.median(perfil)
        proporcion_valle = mejor_media / max(base, 0.01)
        if proporcion_valle < 0.42:
            candidatos.append((proporcion_valle, eje, mejor_posicion))
    if not candidatos:
        return None
    proporcion_valle, eje, posicion = min(candidatos)
    return eje, (x0 if eje == "x" else y0) + posicion, round(0.96 - proporcion_valle * 0.45, 4)


def _caja_ajustada(
    mascara: Image.Image, caja: tuple[int, int, int, int]
) -> tuple[int, int, int, int] | None:
    x0, y0, x1, y1 = caja
    recorte = mascara.crop(caja)
    caja_local = recorte.getbbox()
    if caja_local is None:
        return None
    lx0, ly0, lx1, ly1 = caja_local
    return x0 + lx0, y0 + ly0, x0 + lx1, y0 + ly1


def _contar(mascara: Image.Image, caja: tuple[int, int, int, int]) -> int:
    return sum(1 for pixel in _datos(mascara.crop(caja)) if pixel)


def _datos(imagen: Image.Image) -> list[int]:
    obtener = getattr(imagen, "get_flattened_data", None)
    return list(obtener() if obtener is not None else imagen.getdata())


def _raiz(padres: list[int], nodo: int) -> int:
    while padres[nodo] != nodo:
        padres[nodo] = padres[padres[nodo]]
        nodo = padres[nodo]
    return nodo


def _unir(padres: list[int], primero: int, segundo: int) -> None:
    raiz_primero = _raiz(padres, primero)
    raiz_segundo = _raiz(padres, segundo)
    if raiz_primero != raiz_segundo:
        padres[raiz_segundo] = raiz_primero


def _quitar_duplicados(
    hojas: list[tuple[tuple[int, int, int, int], float]]
) -> list[tuple[tuple[int, int, int, int], float]]:
    resultado: list[tuple[tuple[int, int, int, int], float]] = []
    for caja, confianza in sorted(hojas, key=lambda elemento: elemento[0]):
        x0, y0, x1, y1 = caja
        duplicada = False
        for indice, (otra, confianza_otra) in enumerate(resultado):
            ox0, oy0, ox1, oy1 = otra
            interseccion = max(0, min(x1, ox1) - max(x0, ox0)) * max(
                0, min(y1, oy1) - max(y0, oy0)
            )
            menor = min((x1 - x0) * (y1 - y0), (ox1 - ox0) * (oy1 - oy0))
            if menor and interseccion / menor > 0.8:
                resultado[indice] = (otra, max(confianza, confianza_otra))
                duplicada = True
                break
        if not duplicada:
            resultado.append((caja, confianza))
    return resultado
