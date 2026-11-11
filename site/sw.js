/* Safari 12–compatible, dependency-free offline shell for iPad Air 1.
   The current app remains network-first and works when Service Workers are absent.
   Browser Cache Storage can retain diary content on this device; do not deploy
   private records to a publicly reachable site. */
'use strict';
var CACHE_NAME = 'knowledge-hub-pwa-v9';
var SHELL = ['./', './index.html', './app.js?v=9', './style.css?v=9', './manifest.webmanifest'];

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function (cache) {
      return cache.addAll(SHELL.map(function (url) {
        return new Request(url, {cache: 'reload'});
      }));
    }).then(function () {
      return self.skipWaiting();
    })
  );
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (key) {
        return key.indexOf('knowledge-hub-pwa-') === 0 && key !== CACHE_NAME;
      }).map(function (key) {
        return caches.delete(key);
      }));
    }).then(function () {
      return self.clients.claim();
    })
  );
});

self.addEventListener('fetch', function (event) {
  var request = event.request;
  if (request.method !== 'GET') return;
  var url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  // Never cache requests outside this app's own deployment scope.
  if (url.href.indexOf(self.registration.scope) !== 0) return;
  event.respondWith(
    fetch(request, {cache: 'no-cache'}).then(function (response) {
      if (!response.ok) return response;
      var copy = response.clone();
      event.waitUntil(
        caches.open(CACHE_NAME).then(function (cache) {
          return cache.put(request, copy);
        })
      );
      return response;
    }).catch(function () {
      return caches.match(request).then(function (cached) {
        if (cached) return cached;
        if (request.mode === 'navigate') return caches.match('./index.html');
        return Response.error();
      });
    })
  );
});
