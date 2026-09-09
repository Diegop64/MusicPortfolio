#!/usr/bin/env python3
"""
build_and_sync.py
Synchronizes portfolio tracks from docs/js/tracks.js into static HTML files:
  - docs/portfolio.html
  - docs/es/portfolio.html
  - docs/index.html
  - docs/es/index.html
  - docs/about.html, docs/es/about.html
  - docs/contact.html, docs/es/contact.html
Optimizes images to WebP and ensures all SEO meta tags, OpenGraph, JSON-LD schema,
and correct H1-H3 hierarchies are baked into the static HTML.
"""

import os
import re
import json
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, 'docs')
IMG_DIR = os.path.join(DOCS_DIR, 'images')

def parse_tracks():
    tracks_path = os.path.join(DOCS_DIR, 'js', 'tracks.js')
    content = open(tracks_path, encoding='utf-8').read()
    match = re.search(r'window\.TRACKS\s*=\s*(\[[\s\S]*?\]);', content)
    if not match:
        raise ValueError("Could not find window.TRACKS in tracks.js")
    raw = match.group(1)
    raw_fixed = re.sub(r'([{\s,])([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', raw)
    raw_fixed = re.sub(r',\s*([\]}])', r'\1', raw_fixed)
    return json.loads(raw_fixed)

def optimize_images():
    print("Checking and optimizing images...")
    for root, _, files in os.walk(IMG_DIR):
        for f in files:
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                src = os.path.join(root, f)
                base, ext = os.path.splitext(f)
                webp_path = os.path.join(root, base + '.webp')
                if not os.path.exists(webp_path):
                    try:
                        im = Image.open(src)
                        im.save(webp_path, 'WEBP', quality=85, optimize=True)
                        print(f"Generated {base}.webp")
                    except Exception as e:
                        print(f"Error converting {f}: {e}")

def replace_balanced_div(content, open_tag, replacement):
    """
    Replaces a <div ...>...</div> block, matching the CORRECT closing tag by
    tracking nesting depth, instead of a naive non-greedy regex (which stops
    at the first nested </div> and corrupts the file, e.g. duplicating boxes).
    `open_tag` must be the exact opening tag string, e.g.
    '<div class="portfolio_container slick-carousel">'.
    """
    start = content.find(open_tag)
    if start == -1:
        raise ValueError(f"Could not find opening tag: {open_tag}")
    pos = start + len(open_tag)
    depth = 1
    for m in re.finditer(r'<div\b|</div>', content[pos:]):
        depth += -1 if m.group(0) == '</div>' else 1
        if depth == 0:
            end = pos + m.end()
            return content[:start] + replacement + content[end:]
    raise ValueError(f"Could not find matching closing </div> for: {open_tag}")

def render_box(track, lang='en', prefix=''):
    # No loading="lazy" here on purpose: these images sit inside a Slick
    # carousel that positions slides with `transform`, which can place them
    # far outside the viewport before Slick repositions them. Native lazy
    # loading then defers fetching them indefinitely on first visit (only a
    # cached reload "fixes" it). There are just 6 small images, so eager
    # loading costs nothing.
    title = track['title'][lang]
    alt = track['alt'][lang]
    url = track['url']
    img_rel = track['image'] # e.g. "images/duelite.jpg"
    base_no_ext, _ = os.path.splitext(img_rel)
    webp_rel = prefix + base_no_ext + '.webp'
    fallback_rel = prefix + img_rel
    link_icon = prefix + "images/link.png"

    return f'''      <div class="box">
        <picture>
          <source srcset="{webp_rel}" type="image/webp">
          <img src="{fallback_rel}" alt="{alt}" width="300" height="300" decoding="async">
        </picture>
        <div class="link-box">
          <a href="{url}" target="_blank" rel="noopener" aria-label="Listen to {title}">
            <img src="{link_icon}" alt="" width="20" height="20">
          </a>
          <h3>{title}</h3>
        </div>
      </div>'''

def render_hero_thumb(track, lang='en', prefix=''):
    alt = track['alt'][lang]
    img_rel = track['image']
    base_no_ext, _ = os.path.splitext(img_rel)
    webp_rel = prefix + base_no_ext + '.webp'
    fallback_rel = prefix + img_rel

    return f'''                  <div class="img-box" style="max-width: 150px; max-height: 150px;">
                    <picture>
                      <source srcset="{webp_rel}" type="image/webp">
                      <img src="{fallback_rel}" alt="{alt}" width="150" height="150" decoding="async">
                    </picture>
                  </div>'''

def build_schema(tracks, lang='en'):
    items = []
    for i, t in enumerate(tracks):
        items.append({
            "@type": "ListItem",
            "position": i + 1,
            "item": {
                "@type": "MusicComposition",
                "name": t['title'][lang],
                "composer": {
                    "@type": "Person",
                    "name": "Diego Olmos",
                    "url": "https://www.dolmosmusic.com/"
                },
                "genre": t['schema']['genre'][lang],
                "datePublished": str(t['schema']['datePublished']),
                "description": t['schema']['description'][lang],
                "url": t['url']
            }
        })
    
    name = "Soundtracks & Music Portfolio | DolmosMusic" if lang == 'en' else "Portfolio de Bandas Sonoras y Música | DolmosMusic"
    desc = "Portfolio of original soundtracks by Diego Olmos (DolmosMusic): video games, short films and audiovisual projects." if lang == 'en' else "Portfolio de bandas sonoras originales de Diego Olmos (DolmosMusic): videojuegos, cortometrajes y proyectos audiovisuales."
    page_url = "https://www.dolmosmusic.com/portfolio.html" if lang == 'en' else "https://www.dolmosmusic.com/es/portfolio.html"

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "name": name,
                "description": desc,
                "url": page_url,
                "creator": {
                    "@type": "Person",
                    "name": "Diego Olmos",
                    "alternateName": "DolmosMusic",
                    "jobTitle": "Video game music composer",
                    "url": "https://www.dolmosmusic.com/"
                },
                "mainEntity": {
                    "@type": "ItemList",
                    "numberOfItems": len(tracks),
                    "itemListElement": items
                }
            }
        ]
    }
    return json.dumps(schema, indent=2, ensure_ascii=False)

def update_portfolio_page(file_path, tracks, lang='en', prefix=''):
    content = open(file_path, encoding='utf-8').read()
    
    # Add preconnect if missing
    if 'fonts.gstatic.com' not in content:
        preconnect_html = '  <link rel="preconnect" href="https://fonts.googleapis.com">\n  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        content = re.sub(r'(<link[^>]*href=["\']https://fonts\.googleapis\.com)', preconnect_html + r'\1', content, count=1)
    
    # Open Graph & Twitter tags
    page_url = "https://www.dolmosmusic.com/portfolio.html" if lang == 'en' else "https://www.dolmosmusic.com/es/portfolio.html"
    title_og = "Portfolio | DolmosMusic - Soundtracks for Video Games and Short Films" if lang == 'en' else "Portfolio | DolmosMusic - Bandas Sonoras para Videojuegos y Cortometrajes"
    desc_og = "Portfolio of original soundtracks by Diego Olmos (DolmosMusic): video games, short films and audiovisual projects." if lang == 'en' else "Portfolio de bandas sonoras originales de Diego Olmos (DolmosMusic): videojuegos, cortometrajes y proyectos audiovisuales."
    locale_og = "en_US" if lang == 'en' else "es_ES"

    og_tags = f'''  <!-- Open Graph / social sharing -->
  <meta property="og:type" content="website" />
  <meta property="og:locale" content="{locale_og}" />
  <meta property="og:url" content="{page_url}" />
  <meta property="og:site_name" content="DolmosMusic" />
  <meta property="og:title" content="{title_og}" />
  <meta property="og:description" content="{desc_og}" />
  <meta property="og:image" content="https://www.dolmosmusic.com/images/duelite.webp" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{title_og}" />
  <meta name="twitter:description" content="{desc_og}" />
  <meta name="twitter:image" content="https://www.dolmosmusic.com/images/duelite.webp" />'''

    if 'property="og:title"' not in content:
        content = re.sub(r'(<title>.*?</title>)', r'\1\n\n' + og_tags, content, flags=re.DOTALL)

    # Static JSON-LD in head
    schema_json = build_schema(tracks, lang)
    schema_block = f'''  <script type="application/ld+json">
{schema_json}
  </script>'''
    
    # Remove any existing ld+json in head if present or append before </head>
    content = re.sub(r'  <script type="application/ld\+json">[\s\S]*?</script>\n', '', content)
    content = re.sub(r'(</head>)', schema_block + '\n\\1', content)

    # Heading fix (Change h2 to h1)
    if lang == 'en':
        content = re.sub(r'<h2>\s*Our Portfolio\s*</h2>', '<h1>Soundtracks & Music Portfolio</h1>', content)
        content = re.sub(r'<p>\s*Original soundtracks for video games, short films and audiovisual projects\s*</p>', '<p>Original soundtracks for video games, short films and audiovisual projects by Diego Olmos</p>', content)
    else:
        content = re.sub(r'<h2>\s*Nuestro Portfolio\s*</h2>', '<h1>Portfolio de Bandas Sonoras y Música</h1>', content)
        content = re.sub(r'<p>\s*Bandas sonoras originales para videojuegos, cortometrajes y proyectos audiovisuales\s*</p>', '<p>Bandas sonoras originales para videojuegos, cortometrajes y proyectos audiovisuales por Diego Olmos</p>', content)

    # Replace portfolio_container contents
    boxes_html = '\n'.join([render_box(t, lang, prefix) for t in tracks])
    container_replacement = f'<div class="portfolio_container slick-carousel">\n{boxes_html}\n    </div>'
    content = replace_balanced_div(content, '<div class="portfolio_container slick-carousel">', container_replacement)

    # Clean scripts: remove dynamic injection script
    content = re.sub(r'\s*<script type="text/javascript" src="[^"]*tracks\.js"></script>\s*<script>[\s\S]*?document\.head\.appendChild\(ldScript\);\s*\}\)\(\);\s*</script>', '', content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Updated {file_path}")

def update_index_page(file_path, tracks, lang='en', prefix=''):
    content = open(file_path, encoding='utf-8').read()

    # Preconnect
    if 'fonts.gstatic.com' not in content:
        preconnect_html = '  <link rel="preconnect" href="https://fonts.googleapis.com">\n  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        content = re.sub(r'(<link[^>]*href=["\']https://fonts\.googleapis\.com)', preconnect_html + r'\1', content, count=1)

    # Carousel H1 fix: Keep slide 1 as H1, convert slide 2 and 3 H1 to H2 with slider-title
    content = re.sub(r'<h1>\s*(VIDEO GAME\s*<br\s*/>\s*MUSIC AND FX)\s*</h1>', r'<h2 class="slider-title">\n                        \1\n                      </h2>', content)
    content = re.sub(r'<h1>\s*(MÚSICA Y FX\s*<br\s*/>\s*PARA VIDEOJUEGOS)\s*</h1>', r'<h2 class="slider-title">\n                        \1\n                      </h2>', content)
    content = re.sub(r'<h1>\s*(MUSIC FOR CORPORATE\s*<br\s*/>\s*AND PROMO VIDEOS)\s*</h1>', r'<h2 class="slider-title">\n                        \1\n                      </h2>', content)
    content = re.sub(r'<h1>\s*(MÚSICA PARA VÍDEOS\s*<br\s*/>\s*CORPORATIVOS Y PROMOCIONALES)\s*</h1>', r'<h2 class="slider-title">\n                        \1\n                      </h2>', content)

    # Slider nav thumbs (first 4)
    thumbs_html = '\n'.join([render_hero_thumb(t, lang, prefix) for t in tracks[:4]])
    nav_replacement = f'<div class="slider slider-nav slick_slider-nav">\n{thumbs_html}\n                </div>'
    content = replace_balanced_div(content, '<div class="slider slider-nav slick_slider-nav">', nav_replacement)

    # Portfolio section boxes
    boxes_html = '\n'.join([render_box(t, lang, prefix) for t in tracks])
    container_replacement = f'<div class="portfolio_container slick-carousel">\n{boxes_html}\n    </div>'
    content = replace_balanced_div(content, '<div class="portfolio_container slick-carousel">', container_replacement)

    # Clean scripts: remove tracks.js script and runtime DOM/Schema injection script
    content = re.sub(r'\s*<script type="text/javascript" src="[^"]*tracks\.js"></script>\s*<script>[\s\S]*?document\.head\.appendChild\(ldScript\);\s*\}\)\(\);\s*</script>', '', content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Updated {file_path}")

def update_simple_pages():
    for f in ['about.html', 'es/about.html', 'contact.html', 'es/contact.html']:
        p = os.path.join(DOCS_DIR, f)
        if not os.path.exists(p):
            continue
        c = open(p, encoding='utf-8').read()
        lang = 'es' if 'es/' in f else 'en'
        
        # Preconnect
        if 'fonts.gstatic.com' not in c:
            preconnect_html = '  <link rel="preconnect" href="https://fonts.googleapis.com">\n  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            c = re.sub(r'(<link[^>]*href=["\']https://fonts\.googleapis\.com)', preconnect_html + r'\1', c, count=1)
        
        # Remove unused slick CSS
        c = re.sub(r'\s*<!-- slider stylesheet -->\s*<link rel="stylesheet" href="[^"]*slick\.min\.css">\s*<link rel="stylesheet" href="[^"]*slick-theme\.min\.css">', '', c)
        # Remove unused slick JS
        c = re.sub(r'\s*<script type="text/javascript" src="[^"]*slick\.min\.js"></script>', '', c)

        # OpenGraph tags if missing
        if 'property="og:title"' not in c:
            page_name = 'About' if 'about' in f else 'Contact'
            page_name_es = 'Sobre mí' if 'about' in f else 'Contacto'
            title = f"{page_name_es if lang=='es' else page_name} | DolmosMusic - Original Soundtrack Composer in Murcia"
            desc_text = "Diego Olmos (DolmosMusic), composer and music producer in Murcia, Spain." if lang=='en' else "Diego Olmos (DolmosMusic), compositor y productor musical en Murcia, España."
            loc = 'es_ES' if lang == 'es' else 'en_US'
            url_target = f"https://www.dolmosmusic.com/{f}"

            og = f'''  <!-- Open Graph / social sharing -->
  <meta property="og:type" content="website" />
  <meta property="og:locale" content="{loc}" />
  <meta property="og:url" content="{url_target}" />
  <meta property="og:site_name" content="DolmosMusic" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{desc_text}" />
  <meta property="og:image" content="https://www.dolmosmusic.com/images/me.webp" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{title}" />
  <meta name="twitter:description" content="{desc_text}" />
  <meta name="twitter:image" content="https://www.dolmosmusic.com/images/me.webp" />'''
            c = re.sub(r'(<title>.*?</title>)', r'\1\n\n' + og, c, flags=re.DOTALL)

        # Heading fix
        if 'about' in f:
            if lang == 'en':
                c = re.sub(r'<h2>\s*About me\s*</h2>', '<h1>About Diego Olmos (DolmosMusic)</h1>', c)
            else:
                c = re.sub(r'<h2>\s*Sobre mí\s*</h2>', '<h1>Sobre Diego Olmos (DolmosMusic)</h1>', c)
        elif 'contact' in f:
            if lang == 'en':
                c = re.sub(r'<h2 class="" style="color:grey">Get In Touch</h2>', '<h1 class="" style="color:grey; font-size: 2.2rem; font-weight: bold; margin-bottom: 25px;">Get In Touch</h1>', c)
            else:
                c = re.sub(r'<h2 class="" style="color:grey">\s*(?:Get In Touch|Contacta conmigo)\s*</h2>', '<h1 class="" style="color:grey; font-size: 2.2rem; font-weight: bold; margin-bottom: 25px;">Contacto</h1>', c)

        with open(p, 'w', encoding='utf-8') as fh:
            fh.write(c)
        print(f"Updated {p}")

def main():
    optimize_images()
    tracks = parse_tracks()
    print(f"Loaded {len(tracks)} tracks.")
    
    # 1. Update docs/portfolio.html
    update_portfolio_page(os.path.join(DOCS_DIR, 'portfolio.html'), tracks, lang='en', prefix='')
    # 2. Update docs/es/portfolio.html
    update_portfolio_page(os.path.join(DOCS_DIR, 'es', 'portfolio.html'), tracks, lang='es', prefix='../')
    
    # 3. Update docs/index.html
    update_index_page(os.path.join(DOCS_DIR, 'index.html'), tracks, lang='en', prefix='')
    # 4. Update docs/es/index.html
    update_index_page(os.path.join(DOCS_DIR, 'es', 'index.html'), tracks, lang='es', prefix='../')
    
    # 5. Update docs/about.html and docs/contact.html
    update_simple_pages()
    
    print("Portfolio synchronization complete!")

if __name__ == '__main__':
    main()
