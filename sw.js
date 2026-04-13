const CACHE_NAME = 'otaku-insider-v12';
const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './weekly.html',
  './weekly-archive.html',
  './about.html',
  './privacy.html',
  './contact.html',
  './css/style.css',
  './js/app.js',
  './js/render.js',
  './js/weekly.js',
  './js/weekly-archive.js',
  './js/search.js',
  './js/menu.js',
  './assets/weekly-headers/otaku_header_cool_editorial_1776085572240.png',
  './assets/weekly-headers/otaku_header_emotional_energy_1776085587532.png',
  './assets/weekly-headers/otaku_header_simple_elegant_1776085601859.png',
  './data/entries.json',
  './data/entries_ja.json',
  './manifest.json'
];

// インストール時にキャッシュ
self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(ASSETS_TO_CACHE))
  );
});

// データファイルはネットワーク優先、それ以外はキャッシュ優先
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  const isDataFile = url.pathname.includes('/data/');

  if (isDataFile) {
    // Network First: データは常に最新を取得、失敗時のみキャッシュ
    event.respondWith(
      fetch(event.request)
        .then(response => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
  } else {
    // Stale While Revalidate: キャッシュを返しつつバックグラウンド更新
    event.respondWith(
      caches.match(event.request)
        .then(response => {
          const fetchPromise = fetch(event.request).then(freshResponse => {
            caches.open(CACHE_NAME).then(cache => {
              cache.put(event.request, freshResponse);
            });
          });
          if (response) {
            return response;
          }
          return fetch(event.request);
        })
    );
  }
});

// 古いキャッシュの削除
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== CACHE_NAME)
          .map(key => caches.delete(key))
      );
    }).then(() => self.clients.claim())
  );
});
