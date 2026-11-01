from io import BytesIO

from PIL import Image, ImageDraw

from app.services.separador_vouchers_imagen import detectar_vouchers, recortar_voucher


def _foto_con_vouchers(cantidad: int = 6) -> bytes:
    ancho, alto = 1200, 850
    imagen = Image.new("RGB", (ancho, alto), (38, 42, 45))
    dibujo = ImageDraw.Draw(imagen)
    cajas = [
        (35, 25, 385, 390),
        (425, 20, 775, 385),
        (815, 30, 1165, 395),
        (40, 440, 390, 815),
        (425, 435, 775, 810),
        (810, 445, 1160, 820),
    ]
    for indice, caja in enumerate(cajas[:cantidad]):
        dibujo.rectangle(caja, fill=(232, 232, 225), outline=(205, 205, 198), width=3)
        x0, y0, x1, _ = caja
        dibujo.text((x0 + 20, y0 + 40), f"DEPOSITO OP-{6400000 + indice}", fill=(35, 35, 35))
        dibujo.text((x0 + 20, y0 + 100), "IMPORTE S/ 1,250.00", fill=(35, 35, 35))
    salida = BytesIO()
    imagen.save(salida, format="JPEG", quality=92)
    return salida.getvalue()


def test_separa_seis_vouchers_y_guarda_cada_recorte() -> None:
    original = _foto_con_vouchers()
    segmentacion = detectar_vouchers(original)

    assert segmentacion.estado == "SEPARAR"
    assert len(segmentacion.cajas) == 6
    assert segmentacion.confianza is not None and segmentacion.confianza >= 0.72
    for caja in segmentacion.cajas:
        with Image.open(BytesIO(recortar_voucher(original, caja))) as recorte:
            assert recorte.width > 250
            assert recorte.height > 250


def test_fondo_claro_ambiguo_se_conserva_para_revision() -> None:
    imagen = Image.new("RGB", (900, 1400), (246, 246, 246))
    dibujo = ImageDraw.Draw(imagen)
    dibujo.rectangle((80, 180, 820, 620), fill=(238, 238, 238))
    dibujo.rectangle((80, 730, 820, 1180), fill=(236, 236, 236))
    salida = BytesIO()
    imagen.save(salida, format="JPEG", quality=90)

    segmentacion = detectar_vouchers(salida.getvalue())

    assert segmentacion.estado == "REVISION"
    assert not segmentacion.cajas
