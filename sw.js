/**
 * SuppDB Enterprise PWA Service Worker
 * Strategy: Stale-While-Revalidate (Instant load + background refresh)
 * Cache Name: suppdb-public-cache-v2026.07.1
 */

const CACHE_NAME = 'suppdb-public-cache-v2026.07.1';
const CORE_ASSETS = [
  '/',
  '/index.html',
  '/favicon.ico',
  '/favicon.png',
  '/og-image.png',
  '/site.webmanifest',
  '/sitemap.xml',
  '/samples/suppdb_sample.csv'
];

self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(CORE_ASSETS);
    })
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.map(key => {
          if (key !== CACHE_NAME && key.startsWith('suppdb-public-cache-')) {
            return caches.delete(key);
          }
        })
      ).then(() => self.clients.claim());
    })
  );
});

self.addEventListener('fetch', event => {
  // 1. Strictly bypass non-GET requests (such as POST to formsubmit.co)
  if (event.request.method !== 'GET') {
    return;
  }

  const url = new URL(event.request.url);

  // 2. Strictly bypass cross-origin APIs / endpoints (FormSubmit, PubChem, NIH DSLD, Google Fonts)
  if (url.origin !== self.location.origin) {
    return;
  }

  // 3. Stale-While-Revalidate for same-origin static assets & pages
  event.respondWith(
    caches.match(event.request).then(cachedResponse => {
      const fetchPromise = fetch(event.request).then(networkResponse => {
        if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseToCache);
          });
        }
        return networkResponse;
      }).catch(err => {
        return cachedResponse;
      });

      return cachedResponse || fetchPromise;
    })
  );
});
