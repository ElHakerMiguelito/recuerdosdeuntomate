"""Prepara imágenes y fuentes de la landing (se corre una vez desde la raíz del laboratorio o desde web/).

python web/preparar.py
"""
import math
import os
import shutil

from PIL import Image, ImageDraw, ImageFont

WEB = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(WEB)
RECORTE = os.path.join(LAB, 'CANAL', 'marca', 'recortes', 'toma-tito.png')
FUENTES_LAB = os.path.join(LAB, 'biblioteca', 'fuentes')
IMG = os.path.join(WEB, 'img')
FUENTES = os.path.join(WEB, 'fuentes')

AMARILLO, RAYO, LINEA, GUINDA = (233, 196, 106), (240, 212, 140), (43, 26, 20), (138, 31, 45)


def rayos(img, centro, n=24):
    """Rayos alternados desde `centro`, como el banner de YouTube."""
    d = ImageDraw.Draw(img)
    w, h = img.size
    r = math.hypot(w, h) * 2
    cx, cy = centro
    for i in range(n):
        if i % 2:
            continue
        a0 = 2 * math.pi * i / n
        a1 = 2 * math.pi * (i + 1) / n
        d.polygon([(cx, cy), (cx + r * math.cos(a0), cy + r * math.sin(a0)),
                   (cx + r * math.cos(a1), cy + r * math.sin(a1))], fill=RAYO)


def texto_con_borde(d, xy, txt, fuente, borde=6):
    x, y = xy
    d.text((x, y), txt, font=fuente, fill='white', stroke_width=borde, stroke_fill=LINEA)


def main():
    os.makedirs(IMG, exist_ok=True)
    os.makedirs(FUENTES, exist_ok=True)

    tomate = Image.open(RECORTE).convert('RGBA')
    tomate = tomate.crop(tomate.getbbox())

    # Toma-tito 600×600 (cuadrado, centrado)
    lado = max(tomate.size)
    cuadro = Image.new('RGBA', (lado, lado), (0, 0, 0, 0))
    cuadro.paste(tomate, ((lado - tomate.width) // 2, lado - tomate.height), tomate)
    t600 = cuadro.resize((600, 600), Image.LANCZOS)
    t600.save(os.path.join(IMG, 'toma-tito.webp'), 'WEBP', quality=82, method=6)
    t600.save(os.path.join(IMG, 'toma-tito.png'), optimize=True)

    anton = os.path.join(FUENTES_LAB, 'anton', 'Anton-Regular.ttf')
    caveat = os.path.join(FUENTES_LAB, 'caveat', 'Caveat-Bold.ttf')

    # Vista previa 1200×630
    vp = Image.new('RGB', (1200, 630), AMARILLO)
    rayos(vp, (330, 330))
    t = cuadro.resize((560, 560), Image.LANCZOS)
    vp.paste(t, (50, 50), t)
    d = ImageDraw.Draw(vp)
    f1 = ImageFont.truetype(anton, 120)
    texto_con_borde(d, (620, 120), 'RECUERDOS', f1, 7)
    texto_con_borde(d, (620, 260), 'DE UN TOMATE', ImageFont.truetype(anton, 88), 6)
    d.text((630, 400), 'Yo estuve ahí, compa', font=ImageFont.truetype(caveat, 64), fill=GUINDA)
    vp.save(os.path.join(IMG, 'vista-previa.png'), optimize=True)

    # Icono 180×180: la cara (parte de arriba del recorte) sobre amarillo
    ic = Image.new('RGB', (180, 180), AMARILLO)
    cara = tomate.crop((0, 0, tomate.width, int(tomate.width * 0.95)))
    cara.thumbnail((170, 170), Image.LANCZOS)
    ic.paste(cara, ((180 - cara.width) // 2, (180 - cara.height) // 2 + 6), cara)
    ic.save(os.path.join(IMG, 'icono.png'), optimize=True)

    # Fuentes: solo los caracteres del español (woff; sin brotli no hay woff2)
    from fontTools import subset
    letras = ''.join(chr(c) for c in range(0x20, 0x7f)) + 'áéíóúüñÁÉÍÓÚÜÑ¿¡·…“”‘’–—'
    for origen, destino in ((anton, 'Anton.woff'), (caveat, 'Caveat-Bold.woff')):
        subset.main([origen, f'--text={letras}', '--flavor=woff', '--layout-features=*',
                     f'--output-file={os.path.join(FUENTES, destino)}'])
    for viejo in ('Anton-Regular.ttf', 'Caveat-Bold.ttf'):
        p = os.path.join(FUENTES, viejo)
        if os.path.exists(p):
            os.remove(p)
    shutil.copy(os.path.join(FUENTES_LAB, 'anton', 'OFL.txt'), os.path.join(FUENTES, 'OFL-Anton.txt'))
    shutil.copy(os.path.join(FUENTES_LAB, 'caveat', 'OFL.txt'), os.path.join(FUENTES, 'OFL-Caveat.txt'))

    for carpeta in (IMG, FUENTES):
        for f in sorted(os.listdir(carpeta)):
            p = os.path.join(carpeta, f)
            print(f'{os.path.relpath(p, WEB):30s} {os.path.getsize(p) / 1024:7.1f} KB')


if __name__ == '__main__':
    main()
