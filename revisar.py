"""Revisa la landing antes de subirla. Sale con 0 si todo pasa, 1 si algo falla.

python revisar.py [--usuario USUARIO_DE_GITHUB]
"""
import json
import os
import re
import sys
import unicodedata
from html.parser import HTMLParser

WEB = os.path.dirname(os.path.abspath(__file__))
REPO = 'recuerdosdeuntomate'
REDES = {
    'https://www.youtube.com/@recuerdosdeuntomate': 'YouTube',
    'https://www.instagram.com/recuerdosdeuntomate': 'Instagram',
    'https://www.tiktok.com/@recuerdosdeuntomate': 'TikTok',
    'https://www.facebook.com/profile.php?id=61596528816147': 'Facebook',
}
LIMITE_KB = 400
# Inicios de palabra prohibidos: los de CANAL/censura.json (si está a la mano) + otras groserías comunes.
EXTRA = ['ching', 'cabron', 'culer', 'mamad', 'puto', 'puta', 'verg', 'pinch', 'pendej']


class Lector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.etiquetas = []          # (tag, attrs)
        self.texto = []
        self.pila_a = None           # href del <a> abierto
        self.texto_a = {}            # href -> texto visible
        self.en_title = False
        self.title = ''
        self.css = ''
        self.en_style = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.etiquetas.append((tag, a))
        if tag == 'a':
            self.pila_a = a.get('href')
            self.texto_a.setdefault(self.pila_a, '')
        elif tag == 'title':
            self.en_title = True
        elif tag == 'style':
            self.en_style = True

    def handle_endtag(self, tag):
        if tag == 'a':
            self.pila_a = None
        elif tag == 'title':
            self.en_title = False
        elif tag == 'style':
            self.en_style = False

    def handle_data(self, data):
        if self.en_style:
            self.css += data
            return
        self.texto.append(data)
        if self.en_title:
            self.title += data
        if self.pila_a is not None:
            self.texto_a[self.pila_a] += data


def sin_acentos(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')


def prohibidas():
    lista = list(EXTRA)
    p = os.path.join(os.path.dirname(WEB), 'CANAL', 'censura.json')
    if os.path.exists(p):
        lista += [x['palabra'] for x in json.load(open(p, encoding='utf-8'))['palabras']]
    return sorted(set(sin_acentos(x) for x in lista))


def revisar(usuario=None):
    fallas, avisos, oks = [], [], []
    ok = oks.append
    falla = fallas.append

    ruta = os.path.join(WEB, 'index.html')
    if not os.path.exists(ruta):
        return ['falta index.html'], [], []
    html = open(ruta, encoding='utf-8').read()
    L = Lector()
    L.feed(html)
    tags = L.etiquetas

    # Básicos
    html_tag = next((a for t, a in tags if t == 'html'), {})
    (ok if html_tag.get('lang') == 'es-MX' else falla)('lang="es-MX"')
    (ok if any(t == 'meta' and a.get('name') == 'viewport' for t, a in tags) else falla)('meta viewport')
    (ok if 'Recuerdos de un Tomate' in L.title else falla)('<title> con "Recuerdos de un Tomate"')

    # Enlaces a redes
    hrefs = [a.get('href') for t, a in tags if t == 'a']
    redes = [h for h in hrefs if h and h.startswith('http')]
    if sorted(redes) == sorted(REDES):
        ok('los 4 enlaces de redes, exactos y sin repetir')
    else:
        falla(f'enlaces de redes distintos a lo esperado: {redes}')
    for t, a in tags:
        if t == 'a' and a.get('href') in REDES:
            nombre = REDES[a['href']]
            visible = L.texto_a.get(a['href'], '') + ' ' + (a.get('aria-label') or '')
            (ok if nombre.lower() in visible.lower() else falla)(f'el botón de {nombre} dice "{nombre}"')
            if a.get('target') == '_blank':
                falla(f'{nombre} abre en pestaña nueva (debe ser la misma)')

    # Recursos locales
    locales = []
    for t, a in tags:
        for attr in ('src', 'srcset', 'href'):
            v = a.get(attr)
            if not v or (t == 'a' and v in REDES):
                continue
            if t == 'meta':
                continue
            locales.append(v.split()[0])
        if t == 'meta' and (a.get('property') or '').startswith('og:'):
            continue
    locales += re.findall(r"url\(['\"]?([^'\")]+)['\"]?\)", L.css)
    locales = [v for v in locales if not v.startswith(('data:', '#'))]
    malos = [v for v in locales if v.startswith(('/', 'http'))]
    (falla(f'rutas absolutas o externas: {malos}') if malos else ok('rutas locales relativas'))
    faltan = [v for v in locales if not v.startswith(('/', 'http')) and not os.path.exists(os.path.join(WEB, v))]
    (falla(f'archivos que no existen: {faltan}') if faltan else ok(f'{len(locales)} recursos locales existen'))

    # Imágenes
    imgs = [a for t, a in tags if t == 'img']
    (ok if imgs and all('alt' in a for a in imgs) else falla)('todas las <img> llevan alt')
    tomate = [a for a in imgs if 'toma-tito' in (a.get('src') or '')]
    (ok if tomate and tomate[0].get('width') and tomate[0].get('height') else falla)('Toma-tito con width y height')

    # Peso (lo que baja un celular con webp: html + webp + woff + icono)
    usados = set(v for v in locales if not v.startswith(('/', 'http')))
    usados = [v for v in usados if not v.endswith('.png') or 'icono' in v]
    peso = os.path.getsize(ruta) + sum(os.path.getsize(os.path.join(WEB, v)) for v in usados
                                         if os.path.exists(os.path.join(WEB, v)))
    (ok if peso < LIMITE_KB * 1024 else falla)(f'peso total {peso / 1024:.0f} KB (< {LIMITE_KB} KB)')

    # Groserías
    texto = sin_acentos(' '.join(L.texto) + ' ' + ' '.join(a.get('content', '') for t, a in tags if t == 'meta'))
    palabras = re.findall(r'[a-zñ]+', texto)
    sucias = sorted({p for p in palabras for g in prohibidas() if p.startswith(g)})
    (falla(f'groserías en el texto: {sucias}') if sucias else ok('texto limpio'))

    # Movimiento reducido
    (ok if re.search(r'@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)', L.css) else falla)(
        'respeta prefers-reduced-motion')

    # Open Graph
    og = {a.get('property'): a.get('content', '') for t, a in tags if t == 'meta' and a.get('property')}
    for clave in ('og:title', 'og:description', 'og:image'):
        (ok if og.get(clave) else falla)(clave)
    if usuario:
        base = f'https://{usuario.lower()}.github.io/{REPO}/'
        for clave in ('og:image', 'og:url'):
            (ok if og.get(clave, '').startswith(base) else falla)(f'{clave} empieza con {base}')
    else:
        avisos.append('sin --usuario: og:image y og:url no se revisan (la vista previa al compartir necesita URL absoluta)')

    return fallas, avisos, oks


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
    usuario = None
    if '--usuario' in sys.argv:
        usuario = sys.argv[sys.argv.index('--usuario') + 1]
    fallas, avisos, oks = revisar(usuario)
    for x in oks:
        print('  ok    ', x)
    for x in avisos:
        print('  aviso ', x)
    for x in fallas:
        print('  FALLA ', x)
    print(f'\n{len(oks)} ok, {len(avisos)} avisos, {len(fallas)} fallas')
    sys.exit(1 if fallas else 0)


if __name__ == '__main__':
    main()
