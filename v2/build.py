#!/usr/bin/env python3
"""
v2/build.py  ·  Genera la web de DolmosMusic (EN y ES) en docs/, la carpeta que publica GitHub Pages.

    python v2/build.py                     (desde la carpeta del proyecto)
    python v2/build.py --out v2/preview    (genera en otra carpeta, sin tocar docs/)

Lee:   v2/data/works.json   -> trabajos (orden, títulos, portadas, enlaces, temas, tienda, cliente, años)
       v2/data/site.json    -> textos de la home, marca, email (un único sitio), SEO, formulario
       v2/data/pages/*.json -> una página (pareja EN/ES) por archivo: ruta, SEO, h1 y secciones
       v2/src/              -> plantillas (page.html = marco, home.html, form.html), CSS y JS
       v2/static/           -> archivos que se copian tal cual (CNAME, robots.txt, verificación de Google)
       v2/data/lastmod.json -> huella de cada página y fecha de su último cambio real (para el sitemap)
Crea:  docs/index.html, docs/es/index.html y una carpeta con index.html por cada página de data/pages/,
       css/, js/, images/, sitemap.xml, sw.js y las páginas puente de las URLs antiguas.
Avisa por consola si queda algún marcador "[REDACTOR" o "[PENDIENTE" en la salida.

La versión anterior de la web está guardada en legacy/v1/. Requiere Pillow solo para crear
las versiones WebP (si no está instalado, copia las imágenes tal cual y avisa).
"""

import hashlib
import html
import json
import posixpath
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
        'skip_main': 'Skip to content', 'footer_nav': 'Site', 'breadcrumb': 'Breadcrumb', 'home': 'Home',
        'all_projects': 'See all projects', 'about_more': 'More about me', 'project_details': 'Project details',
        'view_on': 'View on {store}', 'f_select': 'Select…', 'f_type': 'Project type', 'f_type_game': 'Video game',
        'f_type_film': 'Short film', 'f_type_other': 'Other', 'f_size': 'Approx. minutes or number of tracks',
        'f_deadline': 'Delivery date', 'f_budget': 'Your approximate budget', 'f_budget_unsure': 'Not sure yet',
        'f_refs': 'Link to a build, a cut or references', 'f_found': 'How did you find me?',
        'f_found_opts': ['Search engine', 'YouTube', 'Steam credits', 'A recommendation', 'Social media', 'Other'],
        'by': 'By', 'published': 'Published', 'updated': 'Updated', 'related': 'Related',
        'facts_platform': 'Platform', 'facts_released': 'Released', 'facts_composed': 'Composed',
        'facts_style': 'Music', 'facts_role': 'Role', 'facts_brief': 'The brief',
        'facts_director': 'Director', 'facts_duration': 'Duration', 'facts_music_minutes': 'Minutes of music',
        'facts_festivals': 'Festivals', 'facts_watch': 'Short film', 'watch_film': 'Watch the short film', 'years_both': 'composed in {c} · released in {r}',
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
        'skip_main': 'Saltar al contenido', 'footer_nav': 'Sitio', 'breadcrumb': 'Ruta de navegación', 'home': 'Inicio',
        'all_projects': 'Ver todos los proyectos', 'about_more': 'Más sobre mí', 'project_details': 'Ficha del proyecto',
        'view_on': 'Ver en {store}', 'f_select': 'Elige…', 'f_type': 'Tipo de proyecto', 'f_type_game': 'Videojuego',
        'f_type_film': 'Cortometraje', 'f_type_other': 'Otro', 'f_size': 'Minutos o número de temas aproximado',
        'f_deadline': 'Fecha de entrega', 'f_budget': 'Tu presupuesto aproximado', 'f_budget_unsure': 'Aún no lo sé',
        'f_refs': 'Enlace a una build, un montaje o referencias', 'f_found': '¿Cómo me has encontrado?',
        'f_found_opts': ['Buscador', 'YouTube', 'Créditos en Steam', 'Una recomendación', 'Redes sociales', 'Otro'],
        'by': 'Por', 'published': 'Publicado', 'updated': 'Actualizado', 'related': 'Relacionado',
        'facts_platform': 'Plataforma', 'facts_released': 'Lanzamiento', 'facts_composed': 'Composición',
        'facts_style': 'Música', 'facts_role': 'Papel', 'facts_brief': 'El encargo',
        'facts_director': 'Dirección', 'facts_duration': 'Duración', 'facts_music_minutes': 'Minutos de música',
        'facts_festivals': 'Festivales', 'facts_watch': 'Cortometraje', 'watch_film': 'Ver el cortometraje', 'years_both': 'compuesta en {c} · publicada en {r}',
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
    if lst and lst.startswith('PL') and len(lst) != 34:
        warnings.append(f'{where}: la lista "{lst}" está truncada (las listas PL tienen 34 caracteres); '
                        f'la ignoro. Hay que copiar el enlace completo de la lista desde YouTube')
        lst = None
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
        store = w.get('store')
        if store is not None and not (isinstance(store, dict) and str(store.get('url', '')).startswith('https://')
                                      and store.get('name')):
            errors.append(f'{where}: "store" debe ser {{ "name": "Steam", "url": "https://..." }}')
        if w.get('featured') is not None and not isinstance(w['featured'], int):
            errors.append(f'{where}: "featured" debe ser un número (posición en la home: 1, 2, 3...)')
        slug = slugify(loc(w.get('title'), 'en') or str(i))
        while slug in seen:
            slug += '-2'
        seen.add(slug)
        w['_slug'] = slug
        w['_tracks'] = [t for t in tracks if isinstance(t, dict) and t.get('_video')]
    return works


# ------------------------------------------------------------------ rutas y contexto
def depth(path):
    return len([s for s in path.split('/') if s])


def rel(cur, target):
    """Enlace relativo entre dos rutas de la web (ambas en forma 'carpeta/' o '' para la home)."""
    r = posixpath.relpath(target.strip('/') or '.', cur.strip('/') or '.')
    return './' if r == '.' else r + '/'


class Ctx:
    """Idioma y ruta de la página que se está generando."""
    def __init__(self, lang, cur):
        self.lang, self.cur, self.T = lang, cur, I18N[lang]
        self.root = '../' * depth(cur)
        self.home = 'es/' if lang == 'es' else ''  # portada del idioma

    def href(self, target, anchor=''):
        return rel(self.cur, target) + (('#' + anchor) if anchor else '')


MARKER = re.compile(r'\[(?:REDACTOR|PENDIENTE)')
ISO_DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def paras(items, lang, where, cls=''):
    c = f' class="{cls}"' if cls else ''
    return '\n'.join(f'        <p{c}>{esc(loc(p, lang, where))}</p>' for p in (items or []))


def jsonld_script(blocks):
    return '\n  '.join('<script type="application/ld+json">' + json.dumps(b, ensure_ascii=False).replace('</', '<\\/')
                       + '</script>' for b in blocks)


# ------------------------------------------------------------------ rendering: trabajos
def work_links(w, ctx, pages_by_id, with_details):
    """Línea de enlaces de un crédito: tienda (si la hay) y ficha en la página de proyectos."""
    T, lang = ctx.T, ctx.lang
    title = loc(w['title'], lang, w['title'])
    bits = []
    store = w.get('store')
    if store:
        bits.append(f'<a href="{esc(store["url"])}" target="_blank" rel="noopener" '
                    f'aria-label="{esc(title)}: {esc(T["view_on"].format(store=store["name"]))}">'
                    f'{esc(T["view_on"].format(store=store["name"]))}</a>')
    proj = pages_by_id.get('projects')
    if with_details and proj and ctx.cur != proj['path'][lang]:
        bits.append(f'<a href="{esc(ctx.href(proj["path"][lang], w["_slug"]))}">{esc(T["project_details"])}</a>')
    return f'<p class="credit-links">{" · ".join(bits)}</p>' if bits else ''


def work_facts(w, ctx):
    T, lang = ctx.T, ctx.lang
    title = loc(w['title'], lang, w['title'])
    rows = []
    if w.get('store'):
        rows.append((T['facts_platform'], f'<a href="{esc(w["store"]["url"])}" target="_blank" rel="noopener">{esc(w["store"]["name"])}</a>'))
    for key in ('director', 'duration', 'music_minutes', 'festivals'):  # ficha de un cortometraje
        if w.get(key):
            rows.append((T['facts_' + key], esc(loc(w[key], lang, title))))
    if w.get('film_url'):
        rows.append((T['facts_watch'], f'<a href="{esc(w["film_url"])}" target="_blank" rel="noopener">{esc(T["watch_film"])}</a>'))
    if w.get('year_released'):
        rows.append((T['facts_released'], esc(w['year_released'])))
    if w.get('year_composed'):
        rows.append((T['facts_composed'], esc(w['year_composed'])))
    if w.get('style'):
        rows.append((T['facts_style'], esc(loc(w['style'], lang, title))))
    if w.get('role'):
        rows.append((T['facts_role'], esc(loc(w['role'], lang, title))))
    if w.get('brief'):
        rows.append((T['facts_brief'], esc(loc(w['brief'], lang, title))))
    if not rows:
        return ''
    return '<dl class="credit-facts">' + ''.join(f'<div><dt>{esc(k)}</dt><dd>{v}</dd></div>' for k, v in rows) + '</dl>'


def work_url(w):
    """Enlace de YouTube de un trabajo; si su lista se ignoró por truncada, se usa el vídeo sin lista."""
    link = w.get('youtube') or (w['_tracks'][0]['youtube'] if w['_tracks'] else '')
    if link and 'list=' in link and not w['_list']:
        vid = w['_video'] or (w['_tracks'][0]['_video'] if w['_tracks'] else None)
        return f'https://www.youtube.com/watch?v={vid}' if vid else ''
    return link


def render_works(works, ctx, pages_by_id, mode='full'):
    """mode: 'compact' (home: sin lista de temas, el reproductor abre la lista de YouTube),
    'summary' (páginas de servicio: lista de temas y enlace a la ficha) o 'full' (página de proyectos: ficha completa)."""
    T, lang, root = ctx.T, ctx.lang, ctx.root
    out = []
    for w in works:
        title = loc(w['title'], lang, w['title'])
        rel_img, webp = w['_cover']
        type_ = loc(w.get('type'), lang, title)
        if w.get('year_composed') and w.get('year_released'):
            years = T['years_both'].format(c=w['year_composed'], r=w['year_released'])
        else:
            years = str(w['year'])
        meta = f'{type_} {T["for"]} {w["client"]}, {years}' if w.get('client') else f'{type_}, {years}'
        genre = loc(w.get('genre'), lang, title)
        tracks = w['_tracks'] if mode != 'compact' else []
        video = w['_video'] or (w['_tracks'][0]['_video'] if w['_tracks'] else '')
        label = T['toggle_tracks'].format(n=len(tracks)) if tracks else T['toggle_single']
        sid = w['_slug']
        facade = (f'<button class="screen-start" type="button" aria-label="{esc(T["play"].format(title=title))}">'
                  f'{picture(rel_img, webp, "", root, "screen-img", 640)}'
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
        link = work_url(w)
        external = (f'<p class="credit-external"><a href="{esc(link)}" target="_blank" rel="noopener">{esc(T["external"])}</a></p>'
                    if link else '')
        desc = loc(w.get('description'), lang, title)
        cover = ''
        if mode == 'full' and not w.get('personal'):
            cover = (f'<span class="credit-cover">{picture(rel_img, webp, loc(w.get("cover_alt"), lang, title), root, "credit-cover-img", 320)}</span>')
        out.append(f'''        <li class="credit" id="{sid}" data-title="{esc(title)}" data-video="{esc(video)}" data-list="{esc(w["_list"] or "")}">
          <span class="credit-backdrop" aria-hidden="true">{picture(rel_img, webp, "", root, "credit-backdrop-img", 900)}</span>
          {cover}<h3 class="credit-title">{esc(title)}</h3>
          <p class="credit-meta">{esc(meta)}</p>
          {f'<p class="credit-genre">{esc(genre)}</p>' if genre else ''}
          {f'<p class="credit-desc">{esc(desc)}</p>' if desc else ''}
          {work_facts(w, ctx) if mode == 'full' else ''}
          {work_links(w, ctx, pages_by_id, with_details=(mode != 'full'))}
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


# ------------------------------------------------------------------ datos estructurados
def person_ld(site, lang):
    same_as = []
    for s in [s['url'] for s in site.get('social', [])] + [m['url'] for m in site.get('works_more', [])]:
        if s not in same_as:  # el canal de YouTube estaba en "social" y en "works_more"
            same_as.append(s)
    return {
        '@context': 'https://schema.org', '@type': 'Person', '@id': site['site_url'] + '#person',
        'name': site['name'], 'alternateName': site['brand'], 'url': site['site_url'],
        'image': site['site_url'] + site['about']['photo'],
        'jobTitle': loc(site['job_title'], lang, 'job_title'),
        'address': {'@type': 'PostalAddress', 'addressLocality': 'Murcia', 'addressCountry': 'ES'},
        'email': 'mailto:' + site['email'],
        'sameAs': same_as,
    }


def website_ld(site):
    return {
        '@context': 'https://schema.org', '@type': 'WebSite', '@id': site['site_url'] + '#website',
        'url': site['site_url'], 'name': site['brand'], 'alternateName': site.get('brand_alt', []),
        'publisher': {'@id': site['site_url'] + '#person'},
    }


def itemlist_ld(site, works, lang, url, name):
    items = []
    for n, w in enumerate(works, 1):
        rel_img = w['_cover'][0]
        item = {'@type': 'MusicComposition', 'name': loc(w['title'], lang),
                'composer': {'@id': site['site_url'] + '#person'},
                'genre': loc(w.get('genre'), lang),
                'image': rel_img if rel_img.startswith('http') else site['site_url'] + rel_img,
                'url': work_url(w) or url}
        if re.match(r'^\d{4}$', str(w['year'])):  # "2021–2022" no es una fecha válida de schema.org
            item['datePublished'] = str(w['year'])
        if w.get('description'):
            item['description'] = loc(w['description'], lang)
        if w.get('store'):  # el juego al que pertenece la música; cliente y tienda están visibles en la ficha
            part = {'@type': 'VideoGame', 'name': loc(w['title'], lang), 'url': w['store']['url']}
            if w.get('client'):
                part['publisher'] = {'@type': 'Organization', 'name': w['client']}
            item['isPartOf'] = part
        items.append({'@type': 'ListItem', 'position': n, 'item': item})
    return {'@context': 'https://schema.org', '@type': 'ItemList', 'name': name, 'itemListElement': items}


def breadcrumb_ld(site, ctx_trail):
    return {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': n, 'name': name, 'item': site['site_url'] + path}
        for n, (name, path) in enumerate(ctx_trail, 1)]}


# ------------------------------------------------------------------ plantillas
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


def options_html(options, selected=''):
    return ''.join(f'<option value="{esc(v)}"{" selected" if v == selected and v else ""}>{esc(t)}</option>' for v, t in options)


def render_form(site, ctx, tpl, page_origin, form_type=''):
    T, lang = ctx.T, ctx.lang
    kinds = {'game': T['f_type_game'], 'film': T['f_type_film'], 'other': T['f_type_other']}
    types = [('', T['f_select'])] + [(t, t) for t in kinds.values()]
    budget = [('', T['f_select'])] + [(loc(o, lang, 'form.budget_options'),) * 2 for o in site['form']['budget_options']] \
        + [(T['f_budget_unsure'],) * 2]
    found = [('', T['f_select'])] + [(t, t) for t in T['f_found_opts']]
    values = {
        'formspree': site['formspree'], 'page_origin': page_origin,
        'type_options': options_html(types, kinds.get(form_type, '')), 'budget_options': options_html(budget),
        'found_options': options_html(found), 'response_time': loc(site['form']['response_time'], lang, 'form.response_time'),
    }
    values.update({'t_' + k: v for k, v in T.items() if isinstance(v, str)})
    return fill(tpl, values)


def render_nav(ctx, pages):
    """Navegación con enlaces reales. Las páginas de la cabecera son las que llevan "in_nav"."""
    T, lang = ctx.T, ctx.lang
    items = []
    nav_pages = [p for p in pages if p.get('in_nav')]
    for n, p in enumerate(nav_pages):
        cls = '' if n == 0 else ('opt-sm' if n <= 2 else 'opt')
        cur = ' aria-current="page"' if p['path'][lang] == ctx.cur else ''
        li_cls = f' class="{cls}"' if cls else ''
        items.append(f'        <li{li_cls}><a href="{esc(ctx.href(p["path"][lang]))}"{cur}>'
                     f'{esc(loc(p["nav"], lang))}</a></li>')
    items.append(f'        <li><a href="#contact">{esc(T["nav_contact"])}</a></li>')
    return '\n'.join(items)


def render_footer_nav(ctx, pages):
    T, lang = ctx.T, ctx.lang
    items = [f'      <li><a href="{esc(ctx.href(ctx.home))}">{esc(T["home"])}</a></li>']
    for p in pages:
        items.append(f'      <li><a href="{esc(ctx.href(p["path"][lang]))}">{esc(loc(p["nav"], lang))}</a></li>')
    return '\n'.join(items)


def page_values(site, ctx, pages, seo_title, seo_description, keywords, canonical, en_path, es_path, og_image=None):
    T, lang, base = ctx.T, ctx.lang, site['site_url']
    other_lang = 'es' if lang == 'en' else 'en'
    other_path = es_path if lang == 'en' else en_path
    url_en, url_es = base + en_path, base + es_path
    analytics = ''
    if site.get('google_ads_id'):
        gid = esc(site['google_ads_id'])
        analytics = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={gid}"></script>\n  <script>'
                     f"window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}"
                     f"gtag('js',new Date());gtag('config','{gid}');</script>")
    js = dict(T['js'])
    js['formError'] = js['formError'].format(email=site['email'])
    social = ' '.join(f'<a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["label"])}</a>'
                      for s in site.get('social', []))
    values = {
        'lang': lang, 'root': ctx.root, 'home_href': ctx.href(ctx.home),
        'seo_title': seo_title, 'seo_description': seo_description,
        'meta_keywords': f'\n  <meta name="keywords" content="{esc(keywords)}">' if keywords else '',
        'name': site['name'], 'brand': site['brand'], 'canonical': canonical,
        'hreflang_links': (f'  <link rel="alternate" hreflang="en" href="{url_en}">\n'
                           f'  <link rel="alternate" hreflang="es" href="{url_es}">\n'
                           f'  <link rel="alternate" hreflang="x-default" href="{url_en}">'),
        'og_locale': T['og_locale'], 'og_image': base + (og_image or site['seo']['og_image']),
        'nav_items': render_nav(ctx, pages), 'footer_nav': render_footer_nav(ctx, pages),
        'other_url': ctx.href(other_path), 'other_lang': other_lang, 'other_lang_label': T['other_label'],
        'email': site['email'], 'location': loc(site['location'], lang), 'social_links': social,
        'year': str(date.today().year), 'analytics': analytics,
        'js_i18n': json.dumps(js, ensure_ascii=False).replace('</', '<\\/'),
        'asset_v': ASSET_V,
    }
    values.update({'t_' + k: v for k, v in T.items() if isinstance(v, str)})
    return values


def lang_switch(ctx, values):
    """El selector de idioma va en la lista de navegación y enlaza a la página equivalente."""
    li = (f'        <li><a href="{esc(values["other_url"])}" lang="{values["other_lang"]}" '
          f'hreflang="{values["other_lang"]}">{esc(values["other_lang_label"])}</a></li>')
    values['nav_items'] += '\n' + li


# ------------------------------------------------------------------ home
def build_home(site, works, pages, pages_by_id, lang, tpls):
    ctx = Ctx(lang, '' if lang == 'en' else 'es/')
    T, base = ctx.T, site['site_url']
    url = base + ctx.cur
    featured = sorted((w for w in works if w.get('featured')), key=lambda w: w['featured'])
    values = page_values(site, ctx, pages, loc(site['seo']['title'], lang), loc(site['seo']['description'], lang),
                         loc(site['seo']['keywords'], lang), url, '', 'es/')
    lang_switch(ctx, values)
    links_more = [f'<a href="{esc(m["url"])}" target="_blank" rel="noopener">{esc(loc(m["label"], lang))}</a>'
                  for m in site.get('works_more', [])]
    more = T['more'].format(links=f' {T["and"]} '.join(links_more)) if links_more else ''
    role = loc(site['hero'].get('role'), lang) if site['hero'].get('role') else ''
    services = ''
    hs = site.get('home', {}).get('services')
    if hs:
        lis = []
        for it in hs['items']:
            p = pages_by_id[it['page']]
            lis.append(f'        <li><h3>{esc(loc(it["title"], lang))}</h3><p>{esc(loc(it["text"], lang))}</p>'
                       f'<a class="service-link" href="{esc(ctx.href(p["path"][lang]))}">{esc(loc(it["link"], lang))}</a></li>')
        services = ('    <section class="services" id="services" aria-labelledby="services-title">\n'
                    f'      <h2 class="section-title" id="services-title">{esc(loc(hs["heading"], lang))}</h2>\n'
                    '      <ul class="service-list">\n' + '\n'.join(lis) + '\n      </ul>\n    </section>\n')
    cat = site.get('catalog')
    catalog = ''
    if cat:
        catalog = f'''    <section class="catalog" id="catalog" aria-labelledby="catalog-title">
      <h2 class="section-title" id="catalog-title">{esc(T['catalog_title'])}</h2>
      <p class="catalog-lead">{esc(loc(cat['lead'], lang))}</p>
{chr(10).join(f'      <p>{esc(loc(p, lang))}</p>' for p in cat['intro'])}
      <ul class="tiers">
{chr(10).join(f'        <li><h3>{esc(loc(t["name"], lang))}</h3><p>{esc(loc(t["text"], lang))}</p></li>' for t in cat['tiers'])}
      </ul>
      <p class="catalog-outro">{esc(loc(cat['outro'], lang))}</p>
      <a class="btn btn-primary" href="#contact">{esc(T['cta_quote'])}</a>
    </section>
'''
    faq = ''
    if site.get('faq'):
        faq = (f'    <section class="faq" id="faq" aria-labelledby="faq-title">\n'
               f'      <h2 class="section-title" id="faq-title">{esc(T["faq_title"])}</h2>\n'
               + '\n'.join(f'      <details><summary>{esc(loc(f["q"], lang))}</summary><p>{esc(loc(f["a"], lang))}</p></details>'
                           for f in site['faq']) + '\n    </section>\n')
    form = render_form(site, ctx, tpls['form'], url)
    home_vals = {
        'hero_role': f' <span class="hero-role">{esc(role.strip())}</span>' if role.strip() else '',
        'hero_subtitle': loc(site['hero']['subtitle'], lang),
        'services_block': services, 'works': render_works(featured, ctx, pages_by_id, 'compact'),
        'projects_href': ctx.href(pages_by_id['projects']['path'][lang]), 'works_more': more,
        'about_href': ctx.href(pages_by_id['about']['path'][lang]),
        'about_picture': picture(*site['_about_photo'], loc(site['about']['photo_alt'], lang), ctx.root, 'about-photo', 360),
        'about_paragraphs': '\n'.join(f'        <p>{esc(loc(p, lang))}</p>' for p in site['about']['paragraphs']),
        'no_ai_hero_link': loc(site['no_ai']['hero_link'], lang), 'no_ai_title': loc(site['no_ai']['title'], lang),
        'no_ai_text': loc(site['no_ai']['text'], lang), 'no_ai_cta': loc(site['no_ai']['cta'], lang),
        'no_ai_prefill': loc(site['no_ai']['prefill'], lang),
        'testimonial_quote': loc(site['testimonial']['quote'], lang),
        'testimonial_author': site['testimonial']['author'], 'testimonial_logo': site['testimonial']['logo'],
        'catalog_block': catalog, 'faq_block': faq, 'form': form,
        'social_links': values['social_links'], 'email': site['email'], 'root': ctx.root, 'name': site['name'],
    }
    home_vals.update({'t_' + k: v for k, v in T.items() if isinstance(v, str)})
    content = fill(tpls['home'], home_vals)
    blocks = [person_ld(site, lang), website_ld(site), itemlist_ld(site, featured, lang, url, T['works_title'])]
    if site.get('faq'):
        blocks.append({'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [
            {'@type': 'Question', 'name': loc(f['q'], lang),
             'acceptedAnswer': {'@type': 'Answer', 'text': loc(f['a'], lang)}} for f in site['faq']]})
    values.update({'content': content, 'jsonld': jsonld_script(blocks), 'skip_target': '#soundtracks',
                   'skip_text': T['skip']})
    return ctx.cur, fill(tpls['layout'], values)


# ------------------------------------------------------------------ páginas interiores
def link_html(link, ctx, pages_by_id, where):
    lang = ctx.lang
    if 'page' in link:
        p = pages_by_id[link['page']]
        label = loc(link['label'], lang, where) if link.get('label') else loc(p['nav'], lang)
        return f'<a href="{esc(ctx.href(p["path"][lang], link.get("anchor", "")))}">{esc(label)}</a>'
    return (f'<a href="{esc(link["url"])}" target="_blank" rel="noopener">{esc(loc(link["label"], lang, where))}</a>')


def render_section(sec, ctx, site, works_by_slug, works, pages_by_id, where):
    T, lang, root = ctx.T, ctx.lang, ctx.root
    kind = sec['kind']
    sid = sec.get('id', '')
    idattr = f' id="{esc(sid)}"' if sid else ''
    head = ''
    if sec.get('heading'):
        h_id = f' id="{esc(sid)}-title"' if sid else ''
        head = f'      <h2 class="page-h2"{h_id}>{esc(loc(sec["heading"], lang, where))}</h2>\n'
    labelled = f' aria-labelledby="{esc(sid)}-title"' if sid and sec.get('heading') else ''
    w = f'{where}/{sid or kind}'

    if kind == 'text':
        parts = [paras(sec.get('body'), lang, w)]
        if sec.get('items'):
            parts.append('      <ul class="tiers">\n' + '\n'.join(
                f'        <li><h3>{esc(loc(i["title"], lang, w))}</h3><p>{esc(loc(i["text"], lang, w))}</p></li>' for i in sec['items'])
                + '\n      </ul>')
        for fig in sec.get('figures', []):
            parts.append(f'      <figure class="page-figure"><img src="{esc(root + fig["src"])}" alt="{esc(loc(fig["alt"], lang, w))}" '
                         f'loading="lazy" decoding="async">'
                         + (f'<figcaption>{esc(loc(fig["caption"], lang, w))}</figcaption>' if fig.get('caption') else '') + '</figure>')
        if sec.get('links'):
            parts.append('      <p class="page-links">' + ' · '.join(link_html(l, ctx, pages_by_id, w) for l in sec['links']) + '</p>')
        return f'    <section class="page-section"{idattr}{labelled}>\n{head}' + '\n'.join(x for x in parts if x) + '\n    </section>'

    if kind == 'works':
        sel = [works_by_slug[s] for s in sec['works']]
        mode = 'summary' if sec.get('tracklist', True) else 'compact'
        return (f'    <section class="page-section page-works"{idattr}{labelled}>\n{head}'
                + paras(sec.get('intro'), lang, w)
                + f'\n      <ol class="credits">\n{render_works(sel, ctx, pages_by_id, mode)}\n      </ol>\n    </section>')

    if kind == 'projects':
        sel = [x for x in works if bool(x.get('personal')) == (sec['group'] == 'personal')]
        return (f'    <section class="page-section page-works"{idattr}{labelled}>\n{head}'
                + paras(sec.get('intro'), lang, w)
                + f'\n      <ol class="credits">\n{render_works(sel, ctx, pages_by_id, "full")}\n      </ol>\n    </section>')

    if kind == 'testimonial':
        t = site['testimonial']
        return (f'    <section class="quote page-quote"{idattr} aria-labelledby="{esc(sid)}-title">\n'
                + f'      <h2 class="visually-hidden" id="{esc(sid)}-title">{esc(loc(sec["heading"], lang, w) if sec.get("heading") else T["testimonial_title"])}</h2>\n'
                + f'      <figure>\n        <blockquote><p>{esc(loc(t["quote"], lang))}</p></blockquote>\n'
                f'        <figcaption><img src="{esc(root + t["logo"])}" alt="" width="40" height="40" loading="lazy">{esc(t["author"])}</figcaption>\n'
                '      </figure>\n    </section>')

    if kind == 'catalog':
        return (f'    <section class="page-section catalog-block"{idattr}{labelled}>\n{head}'
                + (f'      <p class="catalog-lead">{esc(loc(sec["lead"], lang, w))}</p>\n' if sec.get('lead') else '')
                + paras(sec.get('intro'), lang, w)
                + '\n      <ul class="tiers">\n' + '\n'.join(
                    f'        <li><h3>{esc(loc(i["name"], lang, w))}</h3>'
                    + (f'<p class="tier-price">{esc(loc(i["price"], lang, w))}</p>' if i.get('price') else '')
                    + f'<p>{esc(loc(i["text"], lang, w))}</p></li>' for i in sec['tiers'])
                + '\n      </ul>\n'
                + (f'      <p class="catalog-outro">{esc(loc(sec["outro"], lang, w))}</p>\n' if sec.get('outro') else '')
                + '    </section>')

    if kind == 'faq':
        return (f'    <section class="faq page-faq"{idattr}{labelled}>\n{head}' + '\n'.join(
            f'      <details><summary>{esc(loc(f["q"], lang, w))}</summary><p>{esc(loc(f["a"], lang, w))}</p></details>'
            for f in sec['items']) + '\n    </section>')

    if kind == 'seal':
        link = link_html(sec['link'], ctx, pages_by_id, w) if sec.get('link') else ''
        return (f'    <aside class="page-seal"{idattr}>\n      <p>{esc(loc(sec["text"], lang, w))} {link}</p>\n    </aside>')

    if kind == 'links':
        return (f'    <nav class="page-section page-related"{idattr}{labelled}>\n{head}'
                '      <ul>\n' + '\n'.join(f'        <li>{link_html(l, ctx, pages_by_id, w)}</li>' for l in sec['links'])
                + '\n      </ul>\n    </nav>')
    raise AssertionError(kind)


def build_inner(site, works, works_by_slug, pages, pages_by_id, page, lang, tpls):
    ctx = Ctx(lang, page['path'][lang])
    T, base = ctx.T, site['site_url']
    url = base + ctx.cur
    where = f'pages/{page["_file"]}'
    seo_t, seo_d = loc(page['seo']['title'], lang, where), loc(page['seo']['description'], lang, where)
    values = page_values(site, ctx, pages, seo_t, seo_d, '', url, page['path']['en'], page['path']['es'])
    lang_switch(ctx, values)
    h1, intro = loc(page['h1'], lang, where), loc(page.get('intro'), lang, where)
    nav_label = loc(page['nav'], lang)
    crumbs = (f'      <nav class="crumbs" aria-label="{esc(T["breadcrumb"])}"><ol>'
              f'<li><a href="{esc(ctx.href(ctx.home))}">{esc(T["home"])}</a></li>'
              f'<li aria-current="page">{esc(nav_label)}</li></ol></nav>')
    byline, published, modified = '', None, None
    if page['type'] == 'guide':
        published = loc(page.get('published'), lang, where) or None
        modified = loc(page.get('modified'), lang, where) or None
        bits = [f'{esc(T["by"])} {esc(loc(page.get("author"), lang) or site["name"])}']
        if published:
            bits.append(f'{esc(T["published"])} <time datetime="{esc(published)}">{esc(published)}</time>'
                        if ISO_DATE.match(published) else f'{esc(T["published"])} {esc(published)}')
        if modified:
            bits.append(f'{esc(T["updated"])} <time datetime="{esc(modified)}">{esc(modified)}</time>'
                        if ISO_DATE.match(modified) else f'{esc(T["updated"])} {esc(modified)}')
        byline = f'      <p class="byline">{" · ".join(bits)}</p>\n'
    body = '\n'.join(render_section(s, ctx, site, works_by_slug, works, pages_by_id, where) for s in page['sections'])
    contact = page.get('contact', {})
    c_title = loc(contact.get('heading'), lang, where) if contact.get('heading') else T['contact_title']
    c_lead = loc(contact.get('lead'), lang, where) if contact.get('lead') else None
    lead = (f'<p class="contact-lead">{esc(c_lead)} <a href="mailto:{esc(site["email"])}">{esc(site["email"])}</a></p>' if c_lead
            else f'<p class="contact-lead">{esc(T["contact_lead"])} <a href="mailto:{esc(site["email"])}">{esc(site["email"])}</a></p>')
    form = render_form(site, ctx, tpls['form'], url, page.get('form_type', ''))
    content = (f'    <article class="page page-{esc(page["type"])}">\n    <header class="page-head">\n{crumbs}\n'
               f'      <h1 class="page-title">{esc(h1)}</h1>\n'
               + (f'      <p class="page-intro">{esc(intro)}</p>\n' if intro else '') + byline
               + f'    </header>\n{body}\n    </article>\n'
               f'    <section class="contact" id="contact" aria-labelledby="contact-title">\n'
               f'      <h2 class="section-title" id="contact-title">{esc(c_title)}</h2>\n      {lead}\n{form}\n    </section>')
    # datos estructurados: solo lo que la página muestra
    trail = [(T['home'], ctx.home), (nav_label, ctx.cur)]
    person_ref = {'@id': base + '#person'}
    if page['type'] == 'service':
        main = {'@context': 'https://schema.org', '@type': 'Service', 'name': h1, 'description': intro, 'url': url,
                'inLanguage': lang, 'provider': person_ref}
    elif page['type'] == 'about':
        main = {'@context': 'https://schema.org', '@type': 'AboutPage', 'name': h1, 'description': intro, 'url': url,
                'inLanguage': lang, 'mainEntity': person_ref}
    elif page['type'] == 'projects':
        main = {'@context': 'https://schema.org', '@type': 'CollectionPage', 'name': h1, 'description': intro, 'url': url,
                'inLanguage': lang}
    elif published and ISO_DATE.match(published):
        main = {'@context': 'https://schema.org', '@type': 'Article', 'headline': h1, 'description': intro, 'url': url,
                'inLanguage': lang, 'author': person_ref, 'datePublished': published,
                'dateModified': modified if modified and ISO_DATE.match(modified) else published,
                'mainEntityOfPage': url}
    else:  # guía sin fecha de publicación confirmada: WebPage (Article exige fecha visible)
        main = {'@context': 'https://schema.org', '@type': 'WebPage', 'name': h1, 'description': intro, 'url': url,
                'inLanguage': lang}
    blocks = [main, breadcrumb_ld(site, trail)]
    if page['type'] == 'projects':
        shown = [w for s in page['sections'] if s['kind'] == 'projects' for w in works
                 if bool(w.get('personal')) == (s['group'] == 'personal')]
        blocks.append(itemlist_ld(site, shown, lang, url, h1))
    values.update({'content': content, 'jsonld': jsonld_script(blocks), 'skip_target': '#main', 'skip_text': T['skip_main']})
    return ctx.cur, fill(tpls['layout'], values)


# ------------------------------------------------------------------ páginas puente, sitemap y extras
# Páginas antiguas que los buscadores ya conocen. GitHub Pages no permite 301: se deja un meta refresh de 0 s y
# una canónica al mismo destino (sin ancla), sin noindex, para que las dos señales apunten al mismo sitio (T-01).
# Destino: id de la página sucesora o None (home). El ancla solo se usa en el enlace y el refresh.
LEGACY = {
    'about.html': ('en', 'about', '', 'DolmosMusic: About me'),
    'portfolio.html': ('en', 'projects', '', 'DolmosMusic: Projects'),
    'contact.html': ('en', None, '#contact', 'DolmosMusic: Contact'),
    'es/about.html': ('es', 'about', '', 'DolmosMusic: Sobre mí'),
    'es/portfolio.html': ('es', 'projects', '', 'DolmosMusic: Proyectos'),
    'es/contact.html': ('es', None, '#contact', 'DolmosMusic: Contacto'),
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


def write_legacy(site, pages_by_id):
    base = site['site_url']
    for old, (lang, pid, anchor, title) in LEGACY.items():
        prefix = ('es/' if lang == 'es' else '') if pid is None else pages_by_id[pid]['path'][lang]
        target = '/' + prefix + anchor
        page = (f'<!DOCTYPE html><html lang="{lang}"><head><meta charset="utf-8"><title>{esc(title)}</title>'
                f'<link rel="canonical" href="{base + prefix}">'
                f'<meta http-equiv="refresh" content="0; url={target}"></head>'
                f'<body><a href="{target}">{esc(title)}</a></body></html>')
        dst = OUT / old
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(page, encoding='utf-8', newline='\n')


def content_hash(html_text):
    """Huella del contenido de una página sin lo que cambia solo (versión de CSS/JS, año del copyright)."""
    t = re.sub(r'\?v=[0-9a-f]{8}', '?v=X', html_text)
    t = re.sub(r'© \d{4}', '© Y', t)
    return hashlib.sha256(t.encode('utf-8')).hexdigest()[:16]


def write_sitemap(site, built):
    """built: lista de (ruta_en, ruta_es, html_en, html_es). lastmod = fecha del último cambio real del contenido."""
    base = site['site_url']
    state_file = DATA / 'lastmod.json'
    try:
        state = json.loads(state_file.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}
    today = date.today().isoformat()
    new_state, urls = {}, []
    for en_path, es_path, h_en, h_es in built:
        for path, h in ((en_path, h_en), (es_path, h_es)):
            digest = content_hash(h)
            old = state.get(path, {})
            new_state[path] = {'hash': digest, 'lastmod': old['lastmod'] if old.get('hash') == digest else today}
            urls.append(f'''  <url>
    <loc>{base}{path}</loc>
    <lastmod>{new_state[path]['lastmod']}</lastmod>
    <xhtml:link rel="alternate" hreflang="en" href="{base}{en_path}" />
    <xhtml:link rel="alternate" hreflang="es" href="{base}{es_path}" />
    <xhtml:link rel="alternate" hreflang="x-default" href="{base}{en_path}" />
  </url>''')
    (OUT / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + '\n'.join(urls) + '\n</urlset>\n', encoding='utf-8', newline='\n')
    if OUT == ROOT.parent / 'docs' and new_state != state:  # una vista previa (--out) no toca el estado
        state_file.write_text(json.dumps(new_state, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')


def write_extras(site, pages_by_id, built):
    if STATIC.exists():
        for f in STATIC.rglob('*'):
            if f.is_file():
                dst = OUT / f.relative_to(STATIC)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst)
    (OUT / 'sw.js').write_text(SW_CLEANUP, encoding='utf-8', newline='\n')
    write_legacy(site, pages_by_id)
    write_sitemap(site, built)


# ------------------------------------------------------------------ páginas: carga y validación
SECTION_KINDS = {'text', 'works', 'projects', 'testimonial', 'catalog', 'faq', 'seal', 'links'}
PAGE_TYPES = {'service', 'projects', 'guide', 'about'}


def load_pages():
    pages = []
    folder = DATA / 'pages'
    for f in sorted(folder.glob('*.json')):
        p = load_json(f)
        p['_file'] = f.name
        pages.append(p)
    pages.sort(key=lambda p: (p.get('order', 100), p.get('id', '')))
    return pages


def validate_pages(pages, works_by_slug):
    ids, paths = {}, {'': 'home', 'es/': 'home (es)'}
    by_id = {}
    for p in pages:
        wh = f'pages/{p["_file"]}'
        pid = p.get('id')
        if not pid or pid in by_id:
            errors.append(f'{wh}: falta "id" o está repetido')
            continue
        by_id[pid] = p
        if p.get('type') not in PAGE_TYPES:
            errors.append(f'{wh}: "type" debe ser uno de {sorted(PAGE_TYPES)}')
        for lang in LANGS:
            path = (p.get('path') or {}).get(lang)
            if not path or not path.endswith('/') or path.startswith('/') or 'index.html' in path:
                errors.append(f'{wh}: falta la ruta "{lang}" en "path", o no es del tipo "carpeta/" (sin barra inicial ni index.html). '
                              f'Falta la pareja hreflang {lang.upper()}')
                continue
            if lang == 'es' and not path.startswith('es/'):
                errors.append(f'{wh}: la ruta ES debe empezar por "es/" ({path})')
            if path in paths:
                errors.append(f'{wh}: la ruta "{path}" ya la usa {paths[path]}')
            paths[path] = pid
        for key in ('nav', 'h1'):
            if not p.get(key):
                errors.append(f'{wh}: falta "{key}"')
        if not (p.get('seo') or {}).get('title') or not (p.get('seo') or {}).get('description'):
            errors.append(f'{wh}: faltan "seo.title" o "seo.description"')
        if not isinstance(p.get('sections'), list):
            errors.append(f'{wh}: "sections" debe ser una lista')
            p['sections'] = []
        for n, s in enumerate(p['sections'], 1):
            sw = f'{wh}, sección {n}'
            if s.get('kind') not in SECTION_KINDS:
                errors.append(f'{sw}: "kind" debe ser uno de {sorted(SECTION_KINDS)}')
            for slug in s.get('works', []):
                if slug not in works_by_slug:
                    errors.append(f'{sw}: el trabajo "{slug}" no existe en works.json')
            if s.get('kind') == 'projects' and s.get('group') not in ('commissions', 'personal'):
                errors.append(f'{sw}: "group" debe ser "commissions" o "personal"')
    for p in pages:  # referencias entre páginas
        for s in p.get('sections', []):
            for l in s.get('links', []) + ([s['link']] if s.get('link') else []):
                if 'page' in l and l['page'] not in by_id:
                    errors.append(f'pages/{p["_file"]}: enlace a una página que no existe ("{l["page"]}")')
    # title / h1 / meta description únicos por idioma (incluida la home)
    return by_id


def check_unique(site, pages):
    for lang in LANGS:
        seen = {'title': {}, 'h1': {}, 'description': {}}
        seen['title'][loc(site['seo']['title'], lang)] = 'home'
        seen['description'][loc(site['seo']['description'], lang)] = 'home'
        seen['h1'][site['name']] = 'home'
        for p in pages:
            vals = {'title': loc(p['seo']['title'], lang), 'description': loc(p['seo']['description'], lang),
                    'h1': loc(p['h1'], lang)}
            for k, v in vals.items():
                if v in seen[k]:
                    errors.append(f'pages/{p["_file"]} ({lang}): el {k} es igual que el de {seen[k][v]}; cada página necesita el suyo')
                seen[k][v] = p['id']


def check_markers(outputs):
    """Avisa de los marcadores pendientes que quedan en la salida."""
    total = 0
    for path, text in outputs:
        n = len(MARKER.findall(text))
        if n:
            total += n
            print(f'! marcadores pendientes en {path}: {n}')
    if total:
        print(f'! AVISO: quedan {total} marcadores "[REDACTOR" / "[PENDIENTE" en la salida. No publicar hasta sustituirlos.')


def main():
    global ASSET_V
    site = load_json(DATA / 'site.json')
    works = validate_works(load_json(DATA / 'works.json'))
    works_by_slug = {w['_slug']: w for w in works if isinstance(w, dict)}
    pages = load_pages()
    pages_by_id = validate_pages(pages, works_by_slug)
    for need in ('projects', 'about', 'game-music'):
        if need not in pages_by_id:
            errors.append(f'pages/: falta la página con id "{need}" (la home enlaza a ella)')
    if not errors:
        check_unique(site, pages)

    OUT.mkdir(parents=True, exist_ok=True)
    # Changes whenever CSS or JS change, so browsers never mix an old stylesheet with a new page.
    ASSET_V = hashlib.md5(b''.join(p.read_bytes() for p in sorted((SRC / 'css').glob('*')) + sorted((SRC / 'js').glob('*')))).hexdigest()[:8]
    for w in works:
        if isinstance(w, dict):
            w['_cover'] = publish_image(w.get('cover'), f'Trabajo "{loc(w.get("title"), "es")}"')
    site['_about_photo'] = publish_image(site['about']['photo'], 'Foto de "Sobre mí"', max_side=720, force=True)
    for p in pages:  # imágenes de las páginas (pruebas del proceso, etc.)
        for s in p.get('sections', []):
            for fig in s.get('figures', []):
                publish_image(fig.get('src'), f'pages/{p["_file"]}, figura')
    for rel_ in [site['testimonial']['logo'], 'images/favicon-32x32.png',
                 'images/apple-touch-icon.png', 'favicon.ico']:
        if (ROOT / rel_).exists():
            (OUT / rel_).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel_, OUT / rel_)
        else:
            warnings.append(f'no encuentro {rel_}')

    for w in warnings:
        print('! ' + w)
    if errors:
        print('\n✗ No he generado la web porque hay que corregir esto:')
        for e in errors:
            print('  - ' + e)
        sys.exit(1)

    for sub in ('css', 'js'):
        shutil.copytree(SRC / sub, OUT / sub, dirs_exist_ok=True)
    tpls = {k: (SRC / f'{n}.html').read_text(encoding='utf-8') for k, n in (('layout', 'page'), ('home', 'home'), ('form', 'form'))}

    built, outputs = [], []

    def write(path, html_text):
        dest = OUT / path / 'index.html' if path else OUT / 'index.html'
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html_text, encoding='utf-8', newline='\n')
        outputs.append((str(dest.relative_to(OUT)), html_text))
        print(f'✓ {dest}')
    home = {lang: build_home(site, works, pages, pages_by_id, lang, tpls) for lang in LANGS}
    for lang in LANGS:
        write(*home[lang])
    built.append(('', 'es/', home['en'][1], home['es'][1]))
    for p in pages:
        res = {lang: build_inner(site, works, works_by_slug, pages, pages_by_id, p, lang, tpls) for lang in LANGS}
        for lang in LANGS:
            write(*res[lang])
        built.append((p['path']['en'], p['path']['es'], res['en'][1], res['es'][1]))
    write_extras(site, pages_by_id, built)
    check_markers(outputs)
    if Image is None:
        print('! Pillow no está instalado: no he creado versiones WebP (pip install pillow)')
    print(f'Listo: {len(works)} trabajos y {len(pages) + 1} páginas por idioma en {OUT}')
    print(f'Vista previa: python -m http.server 8124 --directory "{OUT}"')


if __name__ == '__main__':
    main()
