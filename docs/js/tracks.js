// ============================================================
// BANDAS SONORAS DEL PORTFOLIO / PORTFOLIO SOUNDTRACKS
// ============================================================
// Para añadir una banda sonora nueva:
//   1. Sube la imagen a la carpeta docs/images/
//   2. Copia uno de los bloques { ... } de abajo y pégalo en la lista
//   3. Cambia image, alt, title, url y schema por los de tu proyecto nuevo
//      (los campos admiten "en" y "es" para las dos versiones del sitio)
//   4. Ejecuta en la terminal: python build_and_sync.py
//      (Esto pre-renderiza todo el HTML estático, crea versiones WebP y actualiza el Schema SEO)
//   5. Sube los cambios con git: git add . && git commit -m "Nueva pista" && git push
// No hace falta tocar a mano index.html, portfolio.html ni sus versiones en /es/.
// ============================================================
window.TRACKS = [
  {
    image: "images/duelite.jpg",
    alt: {
      en: "Soundtrack for the video game Duelite",
      es: "Banda sonora del videojuego Duelite"
    },
    title: {
      en: "Duelite game soundtrack",
      es: "Banda sonora del videojuego Duelite"
    },
    url: "https://www.youtube.com/watch?v=YCVeZfKYYGM&list=PLscx0rdpUtmn6gh_V0w-uD3LHYnbv6_Q7&index=5",
    schema: {
      genre: {
        en: "Orchestral/Western Soundtrack",
        es: "Banda sonora orquestal / western"
      },
      datePublished: "2022",
      description: {
        en: "Betaking Studios reached out for a soundtrack for their new game, and they were delighted with the result.",
        es: "Betaking me contactó para darle una banda sonora a su nuevo juego y quedaron encantados con el resultado."
      }
    }
  },
  {
    image: "images/youtubelogo.jpg",
    alt: {
      en: "YouTube channel with DolmosMusic soundtracks",
      es: "Canal de YouTube con bandas sonoras de DolmosMusic"
    },
    title: {
      en: "Youtube channel with soundtracks",
      es: "Canal de YouTube con bandas sonoras"
    },
    url: "https://www.youtube.com/@sgiro2670",
    schema: {
      genre: {
        en: "Soundtracks",
        es: "Bandas sonoras"
      },
      datePublished: "2020",
      description: {
        en: "Channel where I upload all the soundtracks I create on my own, of every kind.",
        es: "Canal donde subo todas las bandas sonoras que voy haciendo por mi cuenta, de todo tipo."
      }
    }
  },
  {
    image: "images/cuatroCruces.jpg",
    alt: {
      en: "Soundtrack for the short film Cuatro Cruces",
      es: "Banda sonora del cortometraje Cuatro Cruces"
    },
    title: {
      en: "Cuatro Cruces short soundtrack",
      es: "Banda sonora del cortometraje Cuatro Cruces"
    },
    url: "https://www.youtube.com/watch?app=desktop&v=KC52zbHARf8",
    schema: {
      genre: {
        en: "Orchestral/Western Soundtrack",
        es: "Banda sonora orquestal / western"
      },
      datePublished: "2024",
      description: {
        en: "Composed for Metrópolis C.E., who asked for a soundtrack for one of their short films.",
        es: "Subido para Metrópolis C.E. Me pidieron una banda sonora para uno de sus cortos."
      }
    }
  },
  {
    image: "images/rabbittrail.jpg",
    alt: {
      en: "Soundtrack for the video game Rabbit Trail",
      es: "Banda sonora del videojuego Rabbit Trail"
    },
    title: {
      en: "Rabbit Trail game soundtrack",
      es: "Banda sonora del videojuego Rabbit Trail"
    },
    url: "https://www.youtube.com/watch?v=6f_WvwrR5o8&list=PLscx0rdpUtmn9G7_9QLuqcmh2ETMzsjWN",
    schema: {
      genre: {
        en: "Retro Soundtrack",
        es: "Banda sonora retro"
      },
      datePublished: "2025",
      description: {
        en: "My second video game soundtrack, a great experience working with the team.",
        es: "Segundo videojuego al que poner una banda sonora, un trabajo excelente con el equipo."
      }
    }
  },
  {
    image: "images/beatstarslogo.jpg",
    alt: {
      en: "DolmosMusic beats channel on YouTube",
      es: "Canal de beats de DolmosMusic en YouTube"
    },
    title: {
      en: "Beats Channel",
      es: "Canal de beats"
    },
    url: "https://www.youtube.com/@sgbeats6/videos",
    schema: {
      genre: {
        en: "Trap",
        es: "Trap"
      },
      datePublished: "2022",
      description: {
        en: "Channel where I've been publishing my trap beats for the music industry.",
        es: "Canal donde he ido publicando mis beats de trap para la industria."
      }
    }
  },
  {
    image: "images/catchadndefense.png",
    alt: {
      en: "Soundtrack for the video game Catch & Defense",
      es: "Banda sonora del videojuego Catch & Defense"
    },
    title: {
      en: "Catch & Defense",
      es: "Catch & Defense"
    },
    url: "https://www.youtube.com/watch?v=VZ0qeZskuyY&list=PLYwdEFA2eq4U",
    schema: {
      genre: {
        en: "Game Soundtrack",
        es: "Banda sonora de videojuego"
      },
      datePublished: "2026",
      description: {
        en: "Original soundtrack for the tower defense game \"Catch & Defense\".",
        es: "Banda sonora original para el juego estilo Tower Defense \"Catch & Defense\"."
      }
    }
  }
];
