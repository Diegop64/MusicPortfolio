#!/usr/bin/env python3
"""
v2/build.py  ·  Genera la web de DOlmosMusic (EN y ES) en docs/, la carpeta que publica GitHub Pages.

    python v2/build.py                     (desde la carpeta del proyecto)
    python v2/build.py --out v2/preview    (genera en otra carpeta, sin tocar docs/)

Lee:   v2/data/works.json   -> trabajos (orden, títulos, portadas, enlaces, temas)
       v2/data/site.json    -> textos de la página, SEO, contacto
       v2/src/              -> plantilla, CSS y JS
       v2/static/           -> archivos que se copian tal cual (CNAME, robots.txt, verificación de Google)
Crea:  docs/index.html, docs/es/index.html, css/, js/, images/, sitemap.xml, sw.js
       y redirecciones desde las páginas antiguas (about.html, portfolio.html, contact.html).

La versión anterior de la web está guardada en legacy/v1/. Requiere Pillow solo para crear
las versiones WebP (si no está instalado, copia las imágenes tal cual y avisa).
"""

import hashlib
import html
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse, parse_qs

try:
    from PIL import Image
except ImportError:
    Image = None

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
SRC = ROOT / 'src'
STATIC = ROOT / 'static'
OUT = ROOT.parent / 'docs'
if '--out' in sys.argv:
    OUT = Path(sys.argv[sys.argv.index('--out') + 1]).resolve()
LANGS = ('en', 'es')

# ------------------------------------------------------------------ UI copy
I18N = {
    'en': {
        'skip': 'Skip to soundtracks', 'nav': 'Main', 'nav_works': 'Soundtracks', 'nav_about': 'About',
        'nav_catalog': 'Catalog', 'nav_contact': 'Contact',
        'cta_listen': 'Listen to the soundtracks', 'cta_quote': 'Request a quote',
        'works_title': 'Soundtracks', 'about_title': 'About me', 'testimonial_title': 'Testimonial',
        'catalog_title': 'Catalog', 'faq_title': 'Frequently asked questions', 'contact_title': 'Contact',
        'contact_lead': "Tell me about your project and I'll reply with a quote. You can also write to",
        'f_name': 'Name', 'f_email': 'Email', 'f_message': 'Message', 'f_send': 'Send message',
        'toggle_tracks': 'See all {n} tracks', 'toggle_single': 'Listen', 'play': 'Play {title}',
        'list_note': 'Use the playlist menu inside the player to browse every track.',
        'external': 'Open on YouTube', 'for': 'for', 'and': 'and', 'more': 'More on YouTube: {links}.',
        'js': {'player': 'YouTube player', 'formInvalid': 'Fill in your name, a valid email and a message.',
               'formSending': 'Sending…', 'formSent': "Message sent. I'll get back to you soon.",
               'formError': "The message couldn't be sent. Write to me at {email}."},
        'og_locale': 'en_US', 'other_label': 'ES',
    },
    'es': {
        'skip': 'Saltar a las bandas sonoras', 'nav': 'Principal', 'nav_works': 'Bandas sonoras', 'nav_about': 'Sobre mí',
        'nav_catalog': 'Catálogo', 'nav_contact': 'Contacto',
        'cta_listen': 'Escuchar bandas sonoras', 'cta_quote': 'Pedir presupuesto',
        'works_title': 'Bandas sonoras', 'about_title': 'Sobre mí', 'testimonial_title': 'Opiniones',
        'catalog_title': 'Catálogo', 'faq_title': 'Preguntas frecuentes', 'contact_title': 'Contacto',
        'contact_lead': 'Cuéntame tu proyecto y te respondo con un presupuesto. También puedes escribirme a',
        'f_name': 'Nombre', 'f_email': 'Correo electrónico', 'f_message': 'Mensaje', 'f_send': 'Enviar mensaje',
        'toggle_tracks': 'Ver los {n} temas', 'toggle_single': 'Escuchar', 'play': 'Reproducir {title}',
        'list_note': 'Usa el menú de la lista dentro del reproductor para ver todos los temas.',
        'external': 'Abrir en YouTube', 'for': 'para', 'and': 'y', 'more': 'Más en YouTube: {links}.',
        'js': {'player': 'Reproductor de YouTube', 'formInvalid': 'Rellena tu nombre, un correo válido y el mensaje.',
               'formSending': 'Enviando…', 'formSent': 'Mensaje enviado. Te responderé en breve.',
               'formError': 'No se pudo enviar el mensaje. Escríbeme a {email}.'},
        'og_locale': 'es_ES', 'other_label': 'EN',
    },
}

# ------------------------------------------------------------------ helpers
errors, warnings = [], []
esc = lambda s: html.escape(str(s), quote=True)


def load_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        sys.exit(f'✗ No encuentro {path.relative_to(ROOT)}')
    except json.JSONDecodeError as e:
        line = path.read_text(encoding='utf-8').splitlines()[e.lineno - 1] if e.lineno else ''
        sys.exit(f'✗ {path.name} tiene un error de formato en la línea {e.lineno}, columna {e.colno}: {e.msg}\n'
                 f'    {line.strip()}\n'
                 f'  Pista: suele ser una coma de más al final de un bloque, una coma que falta entre bloques '
                 f'o unas comillas sin cerrar.')


def loc(value, lang, where=''):
    """A text can be a plain string (same in both languages) or {"en": ..., "es": ...}."""
    if value is None:
        return ''
    if isinstance(value, dict):
        if lang in value:
            return value[lang]
        other = next(iter(value.values()), '')
        warnings.append(f'{where}: falta el texto en "{lang}", uso el otro idioma')
        return other
    return str(value)


YT_ID = re.compile(r'^[A-Za-z0-9_-]{11}$')


def parse_youtube(url, where):
    """Returns (video_id, list_id) from any common YouTube URL format."""
    if not isinstance(url, str) or not url.strip():
        errors.append(f'{where}: falta el enlace de YouTube')
        return None, None
    u = urlparse(url.strip())
    host = (u.hostname or '').lower().removeprefix('www.').removeprefix('m.').removeprefix('music.')
    q = parse_qs(u.query)
    video = None
    if host == 'youtu.be':
        video = u.path.lstrip('/').split('/')[0]
    elif host in ('youtube.com', 'youtube-nocookie.com'):
        if 'v' in q:
            video = q['v'][0]
        else:
            m = re.match(r'^/(?:embed|shorts|live|v)/([^/?#]+)', u.path)
            video = m.group(1) if m else None
    else:
        errors.append(f'{where}: el enlace no es de YouTube ({url})')
        return None, None
    lst = q.get('list', [None])[0]
    if lst and not re.match(r'^[A-Za-z0-9_-]{10,}$', lst):
        warnings.append(f'{where}: la lista "{lst}" no parece válida; la ignoro y uso solo el vídeo')
        lst = None
    if not video and lst:
        warnings.append(f'{where}: es un enlace de lista sin vídeo concreto; pon el de un vídeo de la lista '
                        f'(watch?v=...&list=...) para que la portada y el primer tema funcionen')
        errors.append(f'{where}: no encuentro el identificador del vídeo en {url}')
        return None, lst
    if not video or not YT_ID.match(video):
        errors.append(f'{where}: no encuentro un identificador de vídeo válido en {url}')
        return None, None
    return video, lst


def slugify(text):
    s = re.sub(r'[^a-z0-9]+', '-', text.lower().replace('&', 'and')).strip('-')
    return s or 'work'


# ------------------------------------------------------------------ images
def publish_image(rel, where, max_side=900, force=False):
    """Copies a local image into site/ and creates a WebP next to it.
    Returns (src, webp_or_None). Remote URLs are used as they are."""
    if not rel:
        errors.append(f'{where}: falta la imagen')
        return '', None
    if re.match(r'^https?://', rel):
        return rel, None
    src = ROOT / rel
    if not src.exists():
        errors.append(f'{where}: no encuentro la imagen "{rel}" (debe estar dentro de v2/, p. ej. v2/{rel})')
        return rel, None
    dst = OUT / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    if src.suffix.lower() == '.webp' or Image is None:
        return rel, None
    webp_rel = str(Path(rel).with_suffix('.webp')).replace('\\', '/')
    webp_dst = OUT / webp_rel
    if force or not webp_dst.exists() or webp_dst.stat().st_mtime < src.stat().st_mtime:
        im = Image.open(src)
        im = im.convert('RGBA' if im.mode in ('RGBA', 'LA', 'P') else 'RGB')
        im.thumbnail((max_side, max_side))
        im.save(webp_dst, 'WEBP', quality=82, method=6)
    return rel, webp_rel


def picture(rel, webp, alt, root, cls, size, lazy=True):
    load = ' loading="lazy"' if lazy else ''
    img = (f'<img class="{cls}" src="{esc(root + rel if not rel.startswith("http") else rel)}" alt="{esc(alt)}" '
           f'width="{size}" height="{size}"{load} decoding="async">')
    if webp:
        return f'<picture><source srcset="{esc(root + webp)}" type="image/webp">{img}</picture>'
    return img


# ------------------------------------------------------------------ validation
def validate_works(data):
    works = data.get('works') if isinstance(data, dict) else None
    if not isinstance(works, list) or not works:
        sys.exit('✗ works.json debe tener la forma { "works": [ {...}, {...} ] } con al menos un trabajo')
    seen = set()
    for i, w in enumerate(works, 1):
        where = f'Trabajo {i} ({loc(w.get("title"), "es") or "sin título"})' if isinstance(w, dict) else f'Trabajo {i}'
        if not isinstance(w, dict):
            errors.append(f'{where}: debe ser un bloque {{ ... }}')
            continue
        for key in ('title', 'cover', 'type', 'year'):
            if not w.get(key):
                errors.append(f'{where}: falta el campo "{key}"')
        tracks = w.get('tracks') or []
        if not isinstance(tracks, list):
            errors.append(f'{where}: "tracks" debe ser una lista [ ... ]')
            tracks = []
        if not tracks and not w.get('youtube'):
            errors.append(f'{where}: necesita "youtube" (un vídeo o lista) o una lista de "tracks"')
        w['_video'], w['_list'] = (None, None)
        if w.get('youtube'):
            w['_video'], w['_list'] = parse_youtube(w['youtube'], where)
        for j, t in enumerate(tracks, 1):
            tw = f'{where}, tema {j}'
            if not isinstance(t, dict) or not t.get('title'):
                errors.append(f'{tw}: falta "title"')
                continue
            t['_video'], _ = parse_youtube(t.get('youtube'), tw)
        if tracks and not w['_video']:
            w['_video'] = tracks[0].get('_video') if isinstance(tracks[0], dict) else None
        slug = slugify(loc(w.get('title'), 'en') or str(i))
        while slug in seen:
            slug += '-2'
        seen.add(slug)
        w['_slug'] = slug
        w['_tracks'] = [t for t in tracks if isinstance(t, dict) and t.get('_video')]
    return works


# ------------------------------------------------------------------ rendering
def render_works(works, lang, root):
    T = I18N[lang]
    out = []
    for w in works:
        title = loc(w['title'], lang, w['title'])
        rel, webp = w['_cover']
        type_ = loc(w.get('type'), lang, title)
        meta = f'{type_} {T["for"]} {w["client"]}, {w["year"]}' if w.get('client') else f'{type_}, {w["year"]}'
        genre = loc(w.get('genre'), lang, title)
        tracks = w['_tracks']
        label = T['toggle_tracks'].format(n=len(tracks)) if tracks else T['toggle_single']
        sid = w['_slug']
        facade = (f'<button class="screen-start" type="button" aria-label="{esc(T["play"].format(title=title))}">'
                  f'{picture(rel, webp, "", root, "screen-img", 640)}'
                  f'<span class="screen-play" aria-hidden="true"><svg viewBox="0 0 10 10"><path d="M1.5 0l8.5 5-8.5 5z"/></svg></span>'
                  + (f'<span class="screen-note">{esc(T["list_note"])}</span>' if (w['_list'] and not tracks) else '')
                  + '</button>')
        tracklist = ''
        if tracks:
            def cols(t):
                # two aligned columns: section (map, world, main theme...) and detail (battle, boss...).
                # A track with only one of them shows it in the first column so labels line up.
                sec, det = loc(t.get('section'), lang, title), loc(t.get('detail'), lang, title)
                if det and not sec:
                    sec, det = det, ''
                return sec, det
            rows = []
            for n, t in enumerate(tracks, 1):
                sec, det = cols(t)
                rows.append(f'<li><button class="track" type="button" data-video="{esc(t["_video"])}">'
                            f'<span class="track-n">{n}</span><span class="track-title">{esc(loc(t["title"], lang, title))}</span>'
                            f'<span class="track-section">{esc(sec)}</span><span class="track-detail">{esc(det)}</span>'
                            '</button></li>')
            tracklist = f'<ol class="tracklist">{"".join(rows)}</ol>'
        link = w.get('youtube') or (tracks[0].get('youtube') if tracks else '')
        external = (f'<p class="credit-external"><a href="{esc(link)}" target="_blank" rel="noopener">{esc(T["external"])}</a></p>'
                    if link else '')
        out.append(f'''        <li class="credit" id="{sid}" data-title="{esc(title)}" data-video="{esc(w["_video"] or "")}" data-list="{esc(w["_list"] or "")}">
          <span class="credit-backdrop" aria-hidden="true">{picture(rel, webp, "", root, "credit-backdrop-img", 900)}</span>
          <h3 class="credit-title">{esc(title)}</h3>
          <p class="credit-meta">{esc(meta)}</p>
          {f'<p class="credit-genre">{esc(genre)}</p>' if genre else ''}
          <button class="credit-toggle" type="button" aria-expanded="false" aria-controls="panel-{sid}">{esc(label)}<span class="chev" aria-hidden="true"></span></button>
          <div class="credit-panel" id="panel-{sid}" inert>
            <div class="credit-panel-in">
              <div class="screen">{facade}</div>
              <template class="screen-facade">{facade}</template>
              {tracklist}
              {external}
            </div>
          </div>
        </li>''')
    return '\n'.join(out)


def jsonld(site, works, lang, url):
    person = {
        '@context': 'https://schema.org', '@type': 'Person', '@id': site['site_url'] + '#person',
        'name': site['name'], 'alternateName': 'DolmosMusic', 'url': site['site_url'],
        'image': site['site_url'] + site['about']['photo'],
        'jobTitle': 'Video game music composer' if lang == 'en' else 'Compositor de música para videojuegos',
        'address': {'@type': 'PostalAddress', 'addressLocality': 'Murcia', 'addressCountry': 'ES'},
        'email': 'mailto:' + site['email'],
        'sameAs': [s['url'] for s in site.get('social', [])] + [m['url'] for m in site.get('works_more', [])],
    }
    items = []
    for n, w in enumerate(works, 1):
        rel = w['_cover'][0]
        item = {'@type': 'MusicComposition', 'name': loc(w['title'], lang),
                'composer': {'@id': site['site_url'] + '#person'},
                'genre': loc(w.get('genre'), lang), 'datePublished': str(w['year']),
                'image': rel if rel.startswith('http') else site['site_url'] + rel,
                'url': w.get('youtube') or (w['_tracks'][0]['youtube'] if w['_tracks'] else url)}
        if w.get('description'):
            item['description'] = loc(w['description'], lang)
        items.append({'@type': 'ListItem', 'position': n, 'item': item})
    item_list = {'@context': 'https://schema.org', '@type': 'ItemList',
                 'name': I18N[lang]['works_title'], 'itemListElement': items}
    faq = {'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [
        {'@type': 'Question', 'name': loc(f['q'], lang),
         'acceptedAnswer': {'@type': 'Answer', 'text': loc(f['a'], lang)}} for f in site.get('faq', [])]}
    blocks = [person, item_list, faq]
    return '\n  '.join('<script type="application/ld+json">' + json.dumps(b, ensure_ascii=False).replace('</', '<\\/')
                       + '</script>' for b in blocks)


def fill(template, values):
    def raw(m):
        return values[m.group(1)]

    def safe(m):
        return esc(values[m.group(1)])
    missing = {k for k in re.findall(r'\{\{\{?(\w+)\}?\}\}', template) if k not in values}
    if missing:
        sys.exit(f'✗ La plantilla usa valores que no existen: {", ".join(sorted(missing))}')
    out = re.sub(r'\{\{\{(\w+)\}\}\}', raw, template)
    return re.sub(r'\{\{(\w+)\}\}', safe, out)


def build_page(site, works, lang, template):
    T = I18N[lang]
    root = '' if lang == 'en' else '../'
    base = site['site_url']
    url_en, url_es = base, base + 'es/'
    url = url_en if lang == 'en' else url_es
    links_more = [f'<a href="{esc(m["url"])}" target="_blank" rel="noopener">{esc(loc(m["label"], lang))}</a>'
                  for m in site.get('works_more', [])]
    more = T['more'].format(links=f' {T["and"]} '.join(links_more)) if links_more else ''
    social = ' '.join(f'<a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["label"])}</a>'
                      for s in site.get('social', []))
    analytics = ''
    if site.get('google_ads_id'):
        gid = esc(site['google_ads_id'])
        analytics = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={gid}"></script>\n  <script>'
                     f"window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}"
                     f"gtag('js',new Date());gtag('config','{gid}');</script>")
    js = dict(T['js'])
    js['formError'] = js['formError'].format(email=site['email'])
    values = {
        'lang': lang, 'root': root, 'home': './' if lang == 'en' else './',
        'seo_title': loc(site['seo']['title'], lang), 'seo_description': loc(site['seo']['description'], lang),
        'seo_keywords': loc(site['seo']['keywords'], lang), 'name': site['name'], 'brand': site['brand'],
        'canonical': url, 'url_en': url_en, 'url_es': url_es, 'og_locale': T['og_locale'],
        'og_image': base + site['seo']['og_image'],
        'other_url': ('es/' if lang == 'en' else '../'), 'other_lang': 'es' if lang == 'en' else 'en',
        'other_lang_label': T['other_label'],
        'hero_subtitle': loc(site['hero']['subtitle'], lang),
        'works': render_works(works, lang, root), 'works_more': more,
        'about_picture': picture(*site['_about_photo'], loc(site['about']['photo_alt'], lang), root, 'about-photo', 360),
        'about_paragraphs': '\n'.join(f'        <p>{esc(loc(p, lang))}</p>' for p in site['about']['paragraphs']),
        'social_links': social,
        'no_ai_hero_link': loc(site['no_ai']['hero_link'], lang), 'no_ai_title': loc(site['no_ai']['title'], lang),
        'no_ai_text': loc(site['no_ai']['text'], lang), 'no_ai_cta': loc(site['no_ai']['cta'], lang),
        'no_ai_prefill': loc(site['no_ai']['prefill'], lang),
        'testimonial_quote': loc(site['testimonial']['quote'], lang),
        'testimonial_author': site['testimonial']['author'], 'testimonial_logo': site['testimonial']['logo'],
        'catalog_lead': loc(site['catalog']['lead'], lang),
        'catalog_intro': '\n'.join(f'      <p>{esc(loc(p, lang))}</p>' for p in site['catalog']['intro']),
        'catalog_tiers': '\n'.join(f'        <li><h3>{esc(loc(t["name"], lang))}</h3><p>{esc(loc(t["text"], lang))}</p></li>'
                                   for t in site['catalog']['tiers']),
        'catalog_outro': loc(site['catalog']['outro'], lang),
        'faq_items': '\n'.join(f'      <details><summary>{esc(loc(f["q"], lang))}</summary><p>{esc(loc(f["a"], lang))}</p></details>'
                               for f in site.get('faq', [])),
        'email': site['email'], 'formspree': site['formspree'], 'location': loc(site['location'], lang),
        'year': str(date.today().year), 'analytics': analytics, 'jsonld': jsonld(site, works, lang, url),
        'js_i18n': json.dumps(js, ensure_ascii=False).replace('</', '<\\/'),
        'asset_v': ASSET_V,
    }
    values.update({'t_' + k: v for k, v in T.items() if isinstance(v, str)})
    page = fill(template, values)
    dest = OUT / ('index.html' if lang == 'en' else 'es/index.html')
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(page, encoding='utf-8', newline='\n')
    return dest


# Old pages that search engines already know: they now point to the right part of the home.
REDIRECTS = {
    'about.html': ('', '#about'), 'portfolio.html': ('', '#soundtracks'), 'contact.html': ('', '#contact'),
    'es/about.html': ('es/', '#about'), 'es/portfolio.html': ('es/', '#soundtracks'), 'es/contact.html': ('es/', '#contact'),
}

# The previous site registered a service worker that cached CSS/JS/images. This one replaces it,
# empties those caches and unregisters itself, so returning visitors get the new design.
SW_CLEANUP = """// Limpieza del service worker de la versión anterior: borra su caché y se desinstala.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.map((k) => caches.delete(k))))
      .then(() => self.registration.unregister())
      .then(() => self.clients.matchAll({ type: 'window' }))
      .then((clients) => clients.forEach((c) => c.navigate(c.url)))
  );
});
"""


def write_extras(site):
    base = site['site_url']
    if STATIC.exists():
        for f in STATIC.rglob('*'):
            if f.is_file():
                dst = OUT / f.relative_to(STATIC)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst)
    (OUT / 'sw.js').write_text(SW_CLEANUP, encoding='utf-8', newline='\n')
    for old, (prefix, anchor) in REDIRECTS.items():
        target = base + prefix + anchor
        rel = ('./' if '/' not in old else './') + anchor
        page = (f'<!DOCTYPE html><html><head><meta charset="utf-8"><title>DolmosMusic</title>'
                f'<link rel="canonical" href="{base + prefix}"><meta name="robots" content="noindex">'
                f'<meta http-equiv="refresh" content="0; url={rel}"></head>'
                f'<body><a href="{rel}">{target}</a></body></html>')
        dst = OUT / old
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(page, encoding='utf-8', newline='\n')
    today = date.today().isoformat()
    urls = []
    for path in ('', 'es/'):
        urls.append(f'''  <url>
    <loc>{base}{path}</loc>
    <lastmod>{today}</lastmod>
    <xhtml:link rel="alternate" hreflang="en" href="{base}" />
    <xhtml:link rel="alternate" hreflang="es" href="{base}es/" />
    <xhtml:link rel="alternate" hreflang="x-default" href="{base}" />
  </url>''')
    (OUT / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + '\n'.join(urls) + '\n</urlset>\n', encoding='utf-8', newline='\n')


def main():
    global ASSET_V
    site = load_json(DATA / 'site.json')
    works = validate_works(load_json(DATA / 'works.json'))

    OUT.mkdir(parents=True, exist_ok=True)
    # Changes whenever CSS or JS change, so browsers never mix an old stylesheet with a new page.
    ASSET_V = hashlib.md5(b''.join(p.read_bytes() for p in sorted((SRC / 'css').glob('*')) + sorted((SRC / 'js').glob('*')))).hexdigest()[:8]
    for w in works:
        if isinstance(w, dict):
            w['_cover'] = publish_image(w.get('cover'), f'Trabajo "{loc(w.get("title"), "es")}"')
    site['_about_photo'] = publish_image(site['about']['photo'], 'Foto de "Sobre mí"', max_side=720, force=True)
    for rel in [site['testimonial']['logo'], 'images/favicon-32x32.png',
                'images/apple-touch-icon.png', 'favicon.ico']:
        if (ROOT / rel).exists():
            (OUT / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, OUT / rel)
        else:
            warnings.append(f'no encuentro {rel}')

    for w in warnings:
        print('! ' + w)
    if errors:
        print('\n✗ No he generado la web porque hay que corregir esto en data/works.json:')
        for e in errors:
            print('  - ' + e)
        sys.exit(1)

    for sub in ('css', 'js'):
        shutil.copytree(SRC / sub, OUT / sub, dirs_exist_ok=True)
    template = (SRC / 'page.html').read_text(encoding='utf-8')
    for lang in LANGS:
        dest = build_page(site, works, lang, template)
        print(f'✓ {dest}')
    write_extras(site)
    if Image is None:
        print('! Pillow no está instalado: no he creado versiones WebP (pip install pillow)')
    print(f'Listo: {len(works)} trabajos en {OUT}')
    print(f'Vista previa: python -m http.server 8124 --directory "{OUT}"')


if __name__ == '__main__':
    main()
