const CACHE_NAME = 'otaku-insider-v1';
const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './about.html',
  './css/style.css',
  './js/app.js',
  './js/render.js',
  './js/search.js',
  './data/entries.json',
  './manifest.json'
];

// インストール時にキャッシュ
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(ASSETS_TO_CACHE))
  );
});

// フェッチ時にキャッシュ優先、なければネットワーク
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          // キャッシュにあればキャッシュを返しつつ、バックグラウンドで更新
          fetch(event.request).then(freshResponse => {
            caches.open(CACHE_NAME).then(cache => {
              cache.put(event.request, freshResponse);
            });
          });
          return response;
        }
        return fetch(event.request);
      })
  );
});

// 古いキャッシュの削除
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== CACHE_NAME)
            .map(key => caches.delete(key))
      );
    })
  );
});
