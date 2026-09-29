// Service Worker for S. Kumar & Bros Catalog
// Provides instant caching, offline support, and automatic cache updates on new builds.

const CACHE_VERSION = 'v-20260928';
const CACHE_NAME = 'skumar-catalog-' + CACHE_VERSION;

const CORE_ASSETS = [
    './',
    'index.html',
    'index.html',
    'print_catalog.html',
    'photo_catalog.html',
    'assets/css/search_catalog.css',
    'assets/css/photo_catalog.css',
    'assets/js/search_catalog.js',
    'assets/js/commerce_core.js',
    'assets/js/client_directory_core.js',
    'assets/js/bill_archive.js',
    'data/client_data.csv'
];

self.addEventListener('install', event => {
    self.skipWaiting();
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            return cache.addAll(CORE_ASSETS).catch(err => {
                console.warn('Some core assets failed to pre-cache:', err);
            });
        })
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(
                keys.filter(key => key !== CACHE_NAME).map(key => {
                    console.log('Removing old cache:', key);
                    return caches.delete(key);
                })
            );
        }).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // Bypass caching for seller API (port 8766), non-GET, and edit mode
    if (event.request.method !== 'GET' ||
        url.port === '8766' ||
        url.search.indexOf('edit=true') > -1 ||
        url.hostname === '127.0.0.1' ||
        url.hostname === 'localhost') {
        return;
    }

    // Navigation requests (HTML pages): Network-first with cache fallback
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request).then(response => {
                if (response && response.ok) {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                }
                return response;
            }).catch(() => {
                return caches.match(event.request).then(cached => {
                    return cached || caches.match('index.html');
                });
            })
        );
        return;
    }

    // Static assets (CSS, JS, images, CSV): Stale-While-Revalidate
    event.respondWith(
        caches.match(event.request).then(cachedResponse => {
            const fetchPromise = fetch(event.request).then(networkResponse => {
                if (networkResponse && networkResponse.ok) {
                    const clone = networkResponse.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                }
                return networkResponse;
            }).catch(() => null);

            return cachedResponse || fetchPromise;
        })
    );
});
