#!/usr/bin/env python3
"""Descarga las fotos de todas las leyendas de Aura Colombia a fotos/ y
genera fotos/manifest.json para que la página las sirva localmente.

Uso:  python3 descargar_fotos.py
- Lee el roster (PERSONAS) directamente de index.html.
- Resuelve cada foto igual que la página: Wikipedia es -> en -> búsqueda
  por título -> Wikimedia Commons, con miniaturas de 400px.
- No re-descarga fotos que ya existan en fotos/ (borra el archivo para forzar).
- Al final imprime el reporte de quiénes quedaron SIN foto.

Solo usa la librería estándar; necesita salida a internet (wikipedia.org,
wikimedia.org).
"""
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

RAIZ = os.path.dirname(os.path.abspath(__file__))
FOTOS = os.path.join(RAIZ, 'fotos')
UA = {'User-Agent': 'AuraColombia/1.0 (https://github.com/Robertzu43/aura-colombia)'}

# Mantener en sincronía con WIKI_TITULOS / WIKI_EN de index.html
WIKI_TITULOS = {
    'Camilo': ['Camilo (cantante)', 'Camilo Echeverry'],
    'Fonseca': ['Fonseca (cantante)', 'Juan Fernando Fonseca'],
    'Greeicy': ['Greeicy Rendón', 'Greeicy'],
    'Goyo': ['Goyo (cantante)', 'Goyo (rapero)', 'Gloria Martínez Perea'],
    'Farina': ['Farina (cantante)', 'Farina (rapera)'],
    'Joe Arroyo': ['Joe Arroyo', 'Álvaro José Arroyo'],
    'Andrés Cepeda': ['Andrés Cepeda', 'Andrés Cepeda (cantante)'],
    'Luis Díaz': ['Luis Díaz (futbolista colombiano)', 'Luis Díaz (futbolista)'],
    'Radamel Falcao': ['Radamel Falcao García', 'Falcao García', 'Radamel Falcao'],
    'Juan G. Cuadrado': ['Juan Cuadrado', 'Juan Guillermo Cuadrado'],
    'Carlos Valderrama': ['Carlos Valderrama', 'Carlos Valderrama (futbolista)'],
    'Iván R. Córdoba': ['Iván Ramiro Córdoba', 'Iván Córdoba'],
    'Lucho Herrera': ['Lucho Herrera', 'Luis Herrera (ciclista)'],
    'Óscar Figueroa': ['Óscar Figueroa (halterófilo)', 'Óscar Albeiro Figueroa'],
    'Kid Pambelé': ['Antonio Cervantes', 'Kid Pambelé'],
    'Happy Lora': ['Miguel Lora', 'Happy Lora'],
    'Robert Farah': ['Robert Farah (tenista)', 'Robert Farah'],
    'Catalina Sandino': ['Catalina Sandino Moreno'],
    'Carolina Cruz': ['Carolina Cruz Osorio', 'Carolina Cruz (presentadora)'],
    'Suso el Paspi': ['Dany Alejandro Hoyos', 'Suso el Paspi'],
    'Andrés López': ['Andrés López Forero', 'Andrés López (humorista)'],
    'Hassam': ['Hassam (humorista)', 'Gerly Hassam Gómez Parra', 'Hassam'],
    'Iván Marín': ['Iván Marín (humorista)', 'Iván Marín'],
    'Pautips': ['Paula Galindo', 'Pautips'],
    'Epa Colombia': ['Epa Colombia', 'Daneidy Barrera Rojas'],
    'Westcol': ['Westcol', 'WestCOL'],
    'Aida Victoria Merlano': ['Aida Victoria Merlano', 'Aída Victoria Merlano'],
    'Álvaro Uribe': ['Álvaro Uribe Vélez', 'Álvaro Uribe'],
    'David Vélez': ['David Vélez (empresario)', 'David Vélez'],
}
WIKI_EN = {
    'Camilo': ['Camilo (singer)'],
    'Fonseca': ['Fonseca (singer)'],
    'Goyo': ['Goyo (singer)'],
    'Farina': ['Farina (rapper)'],
    'Luis Díaz': ['Luis Díaz (footballer, born 1997)'],
    'Juan G. Cuadrado': ['Juan Cuadrado'],
    'Carlos Valderrama': ['Carlos Valderrama (footballer)'],
    'Óscar Figueroa': ['Óscar Figueroa (weightlifter)'],
    'Robert Farah': ['Robert Farah (tennis)'],
    'David Vélez': ['David Vélez (businessman)'],
}
# Archivos de Commons verificados a mano para gente sin artículo o con
# nombre de archivo que el matching automático no reconoce.
COMMONS_DIRECTO = {
    'Kika Nieto': 'Kika_Nieto_KCA_Colombia_2016.png',
    'Luisa Fernanda W': 'Luisa_Fernanda_W_2017.png',
    'Aida Victoria Merlano': 'Aida_Victoria_Merlano.jpg',
    'Diomedes Díaz': 'Diomedesdiaz2.png',
}


def sin_acentos(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower())
                   if unicodedata.category(c) != 'Mn')


def slug(nombre):
    return re.sub(r'[^a-z0-9]+', '-', sin_acentos(nombre)).strip('-')


def leer_roster():
    with open(os.path.join(RAIZ, 'index.html'), encoding='utf-8') as f:
        html = f.read()
    script = html.split('<script>')[1].split('</script>')[0]
    return [n for n, _ in re.findall(r"\['([^']+)','([^']+)'\]", script)]


_ultima_llamada = [0.0]


def api(host, params):
    params = dict(params, format='json')
    url = f'https://{host}/w/api.php?' + urllib.parse.urlencode(params)
    # ritmo suave + reintentos con backoff: Wikipedia limita ráfagas anónimas
    for intento in range(5):
        espera = _ultima_llamada[0] + 0.25 - time.time()
        if espera > 0:
            time.sleep(espera)
        _ultima_llamada[0] = time.time()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.load(r)
        except Exception as e:
            if intento == 4:
                print(f'  API agotó reintentos ({host}): {e}', file=sys.stderr)
                raise
            time.sleep(2 ** intento)


def candidatos(nombre, extra=None):
    vistos, lista = set(), []
    for t in (extra or []) + WIKI_TITULOS.get(nombre, []) + [nombre]:
        if t not in vistos:
            vistos.add(t)
            lista.append(t)
    return lista


def lote_pageimages(host, titulos):
    res = {}
    for i in range(0, len(titulos), 50):
        data = api(host, {'action': 'query', 'redirects': 1, 'prop': 'pageimages',
                          'piprop': 'thumbnail', 'pithumbsize': 400,
                          'titles': '|'.join(titulos[i:i + 50])})
        q = data.get('query', {})
        origen = {}
        for n in q.get('normalized', []):
            origen[n['to']] = n['from']
        for r in q.get('redirects', []):
            origen[r['to']] = origen.get(r['from'], r['from'])
        for pg in q.get('pages', {}).values():
            if 'thumbnail' in pg:
                res[origen.get(pg['title'], pg['title'])] = pg['thumbnail']['source']
        time.sleep(0.3)
    return res


def tokens_de(nombre):
    return [w for w in sin_acentos(nombre).split() if len(w) > 2]


def titulo_coincide(nombre, titulo):
    palabras = re.split(r'[^a-z0-9]+', sin_acentos(titulo))
    return all(t in palabras for t in tokens_de(nombre))


def buscar_intitle(nombre):
    for host in ('es.wikipedia.org', 'en.wikipedia.org'):
        try:
            s = api(host, {'action': 'query', 'list': 'search',
                           'srsearch': f'intitle:"{nombre}"', 'srlimit': 3})
            for hit in s.get('query', {}).get('search', []):
                if not titulo_coincide(nombre, hit['title']):
                    continue
                urls = lote_pageimages(host, [hit['title']])
                if urls:
                    return next(iter(urls.values()))
        except Exception as e:
            print(f'  intitle {nombre} ({host}): {e}', file=sys.stderr)
    return None


def buscar_commons(nombre):
    try:
        d = api('commons.wikimedia.org', {
            'action': 'query', 'generator': 'search', 'gsrnamespace': 6,
            'gsrlimit': 10, 'gsrsearch': f'intitle:"{nombre}" filetype:bitmap',
            'prop': 'imageinfo', 'iiprop': 'url', 'iiurlwidth': 400})
        paginas = sorted(d.get('query', {}).get('pages', {}).values(),
                         key=lambda p: p.get('index', 99))
        for pg in paginas:
            if not titulo_coincide(nombre, re.sub(r'^file:', '', pg['title'], flags=re.I)):
                continue
            info = (pg.get('imageinfo') or [{}])[0]
            if info.get('thumburl'):
                return info['thumburl']
    except Exception as e:
        print(f'  commons {nombre}: {e}', file=sys.stderr)
    return None


def descargar(url, nombre):
    ext = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
        ext = '.jpg'
    destino = f'{slug(nombre)}{ext}'
    # mismo ritmo suave + reintentos que api(): upload.wikimedia también limita ráfagas
    for intento in range(5):
        espera = _ultima_llamada[0] + 0.25 - time.time()
        if espera > 0:
            time.sleep(espera)
        _ultima_llamada[0] = time.time()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                datos = r.read()
            break
        except Exception as e:
            if intento == 4:
                raise
            time.sleep(2 ** intento)
    with open(os.path.join(FOTOS, destino), 'wb') as f:
        f.write(datos)
    return destino


def archivo_existente(nombre):
    for ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
        if os.path.exists(os.path.join(FOTOS, slug(nombre) + ext)):
            return slug(nombre) + ext
    return None


def main():
    os.makedirs(FOTOS, exist_ok=True)
    nombres = leer_roster()
    print(f'{len(nombres)} leyendas en el roster')
    manifest, faltan = {}, []

    pendientes = []
    for n in nombres:
        ya = archivo_existente(n)
        if ya:
            manifest[n] = f'fotos/{ya}'
        else:
            pendientes.append(n)
    print(f'{len(manifest)} ya descargadas, {len(pendientes)} por resolver')

    # 0) archivos de Commons verificados a mano
    for n in list(pendientes):
        if n in COMMONS_DIRECTO:
            url = ('https://commons.wikimedia.org/wiki/Special:FilePath/'
                   + urllib.parse.quote(COMMONS_DIRECTO[n]) + '?width=400')
            try:
                manifest[n] = 'fotos/' + descargar(url, n)
                pendientes.remove(n)
                print(f'  fija     {n}')
            except Exception as e:
                print(f'  ERROR fija {n}: {e}', file=sys.stderr)

    # 1) y 2) lotes de pageimages en es y en
    for host, extra in (('es.wikipedia.org', None), ('en.wikipedia.org', WIKI_EN)):
        if not pendientes:
            break
        titulos = []
        for n in pendientes:
            titulos += candidatos(n, (extra or {}).get(n))
        urls = lote_pageimages(host, sorted(set(titulos)))
        for n in list(pendientes):
            for t in candidatos(n, (extra or {}).get(n)):
                if t in urls:
                    try:
                        manifest[n] = 'fotos/' + descargar(urls[t], n)
                        pendientes.remove(n)
                        print(f'  {host.split(".")[0]:8} {n}')
                    except Exception as e:
                        print(f'  ERROR {n}: {e}', file=sys.stderr)
                    break

    # 3) búsqueda por título y 4) Commons
    for n in list(pendientes):
        url = buscar_intitle(n) or buscar_commons(n)
        if url:
            try:
                manifest[n] = 'fotos/' + descargar(url, n)
                pendientes.remove(n)
                print(f'  búsqueda {n}')
            except Exception as e:
                print(f'  ERROR {n}: {e}', file=sys.stderr)
        time.sleep(0.3)

    faltan = pendientes
    with open(os.path.join(FOTOS, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1, sort_keys=True)

    print(f'\n✅ {len(manifest)} fotos en fotos/ (manifest.json actualizado)')
    if faltan:
        print(f'🚫 SIN FOTO ({len(faltan)}): ' + ', '.join(faltan))
    else:
        print('🎉 Todas las leyendas tienen foto.')


if __name__ == '__main__':
    main()
