const CACHE_NAME = 'mvp-collector-cache-v1';
const URLsToCache = [
  '/', 
  '/static/css/styles.css',
  '/static/js/scripts.js',
  // adicione aqui outros recursos estáticos que queira cachear
];

// Instalação: cache dos recursos
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(URLsToCache))
      .then(self.skipWaiting())
  );
});

// Ativação: limpar caches antigos
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => 
      Promise.all(
        keys.filter(key => key !== CACHE_NAME)
            .map(key => caches.delete(key))
      )
    )
  );
});

// Interceptar fetch: servir do cache, fallback para rede
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(cached => cached || fetch(event.request))
  );
});
