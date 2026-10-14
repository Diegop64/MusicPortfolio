# DOlmosMusic (web actual, dirección "Créditos")

Este es el código de la web. `build.py` genera la página en `docs/`, que es la carpeta que publica
GitHub Pages en www.dolmosmusic.com. La versión anterior está guardada en `legacy/` (ver abajo).

## Generar y ver la web en local

```
python v2/build.py
python -m http.server 8124 --directory docs
```

Abre http://localhost:8124 (inglés) y http://localhost:8124/es/ (español).
Las fuentes y los vídeos de YouTube necesitan conexión a internet.
Para probar sin tocar `docs/`: `python v2/build.py --out v2/preview`.

## Añadir o editar trabajos: `data/works.json`

El orden de la web es el orden del archivo. Cada trabajo es un bloque así:

```json
{
  "title": "Duelite",
  "cover": "images/duelite.jpg",
  "type": { "en": "Video game", "es": "Videojuego" },
  "client": "Betaking Studios",
  "year": 2022,
  "genre": { "en": "Orchestral, western", "es": "Orquestal, western" },
  "description": { "en": "...", "es": "..." },
  "youtube": "https://www.youtube.com/watch?v=YCVeZfKYYGM&list=...",
  "tracks": [
    { "title": "Wasted", "detail": { "en": "Main theme", "es": "Tema principal" }, "youtube": "https://www.youtube.com/watch?v=ckYBydKpR9k" },
    { "title": "Old West", "section": { "en": "Map 1", "es": "Mapa 1" }, "detail": { "en": "Map screen", "es": "Pantalla de mapa" }, "youtube": "https://www.youtube.com/watch?v=mS33qFtNF10" }
  ]
}
```

| Campo | ¿Obligatorio? | Qué hace |
|---|---|---|
| `title` | sí | Título grande del crédito |
| `cover` | sí | Ruta dentro de `v2/` (sube la imagen a `v2/images/`) o un enlace `https://...`. Se crea la versión WebP sola |
| `type` | sí | Videojuego, Cortometraje... |
| `year` | sí | Año |
| `client` | no | Aparece como "Videojuego para Betaking Studios, 2022" |
| `genre` | no | Línea bajo el título |
| `description` | no | Solo para Google (datos estructurados) |
| `youtube` | sí, si no hay `tracks` | Un vídeo o un vídeo con `&list=`. Sin `tracks`, el botón dice "Escuchar" y lo reproduce; si lleva lista, se navega desde el menú del reproductor |
| `tracks` | no | Lista de temas. Si hay alguno, el botón dice "Ver los N temas" y cada tema reproduce su enlace. Cada tema lleva `title`, `youtube` y dos columnas opcionales que se alinean entre temas: `section` (mapa, mundo, tienda...) y `detail` (combate, jefe...). Si solo pones una, aparece en la primera columna |

- Textos: una cadena normal si es igual en los dos idiomas, o `{ "en": "...", "es": "..." }`.
- Enlaces de YouTube: vale cualquier formato (`watch?v=`, `youtu.be/`, `shorts/`, `embed/`).
- Cuidado con las comas: entre bloques sí, después del último no.

Al terminar, ejecuta `python v2/build.py` (y sube los cambios con git para publicarlos). Si algo está mal, no genera la web y te dice qué
corregir, por ejemplo: `Trabajo 2 (Cuatro Cruces): el enlace no es de YouTube`.

## Otros textos: `data/site.json`

Subtítulo del hero, aviso "Compuesto sin IA" (`no_ai`), sobre mí, opinión, catálogo, preguntas frecuentes, redes, correo, formulario
(Formspree) y SEO. Los textos de botones y etiquetas están en `I18N`, al principio de `build.py`.

## Estructura

```
v2/
  build.py          genera ../docs a partir de data/, src/ y static/
  data/             works.json y site.json (lo que editas)
  src/page.html     plantilla
  src/css, src/js   estilos y comportamiento
  images/           imágenes de origen
  static/           se copia tal cual: CNAME (dominio), robots.txt, verificación de Google
```

`build.py` también crea en `docs/`:
- `sitemap.xml` con la portada en inglés y en español.
- Redirecciones desde las páginas antiguas (`about.html`, `portfolio.html`, `contact.html` y sus
  versiones en `/es/`) a la sección correspondiente de la portada.
- `sw.js`, que borra la caché que dejó la versión anterior en los navegadores de quien ya la visitó
  y se desinstala.
- Los enlaces a `style.css` y `main.js` llevan `?v=...`, que cambia solo cuando cambian, para que
  nadie vea estilos viejos.

No edites `docs/` a mano: se sobrescribe cada vez que ejecutas `build.py`.

## Versión anterior

- `legacy/v1/` contiene la web anterior completa (`docs/`) y su script (`build_and_sync.py`).
  Sigue funcionando: `python -m http.server 8123 --directory legacy/v1/docs`.
- `legacy/web-v1-2026-10-14.zip` es la misma versión empaquetada en un solo archivo.

## Pendiente

- La carpeta `v2/site/` es de antes, cuando la web se generaba ahí; ya no se usa y se puede borrar.
