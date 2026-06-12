const CACHE = 'mawsuat-alrijal-v1';
const ASSETS = [
  '/',
  '?nav='  // dummy to trigger asset caching
];

self.addEventListener('install', (e) => {
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(clients.claim());
});

self.addEventListener('fetch', (e) => {
  // Network-first for dynamic Streamlit content; cache for static assets
  if (e.request.destination === 'style' || e.request.destination === 'script' || e.request.destination === 'font') {
    e.respondWith(
      caches.open(CACHE).then(cache =>
        cache.match(e.request).then(cached =>
          cached || fetch(e.request).then(response => {
            cache.put(e.request, response.clone());
            return response;
          })
        )
      )
    );
  }
});
