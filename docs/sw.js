// Service Worker: cachea CSS/JS/imágenes para que sigan mostrándose al
// instante si la red tarda en estar lista (p. ej. justo al arrancar el PC).
const CACHE_NAME = 'dolmosmusic-cache-v1';

self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const isStaticAsset =
    req.destination === 'image' ||
    req.destination === 'style' ||
    req.destination === 'script' ||
    req.destination === 'font';

  if (!isStaticAsset) return;

  // Cache-first con actualización en segundo plano (stale-while-revalidate):
  // responde al instante desde caché si existe, y de paso refresca la copia
  // guardada para la próxima visita.
  event.respondWith(
    caches.open(CACHE_NAME).then((cache) =>
      cache.match(req).then((cached) => {
        const fetchPromise = fetch(req)
          .then((res) => {
            if (res && res.status === 200) cache.put(req, res.clone());
            return res;
          })
          .catch(() => cached);
        return cached || fetchPromise;
      })
    )
  );
});
