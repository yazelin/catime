const STATIC_CACHE = "catime-static-v1";
const CATLIST_RE = /catlist\.json$/;
const RELEASE_CATS = "https://github.com/yazelin/catime/releases/download/cats/";
const ICON_RE = /(icon|favicon|apple-touch-icon)/;

self.addEventListener("install", (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== STATIC_CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  const isCatlist = CATLIST_RE.test(url.pathname) || url.href.includes("catlist.json");
  const isReleaseCat = url.href.startsWith(RELEASE_CATS);
  const isStatic =
    request.destination === "document" ||
    request.destination === "style" ||
    request.destination === "script" ||
    (request.destination === "image" && ICON_RE.test(url.pathname));
  if (isCatlist || isReleaseCat) {
    event.respondWith(
      fetch(request)
        .then((resp) => {
          if (resp && resp.ok) {
            caches.open(STATIC_CACHE).then((c) => c.put(request, resp.clone()));
          }
          return resp;
        })
        .catch(() => caches.match(request))
    );
    return;
  }
  if (isStatic) {
    event.respondWith(
      caches.match(request).then((cached) =>
        cached ||
        fetch(request).then((resp) => {
          if (resp && resp.ok) {
            caches.open(STATIC_CACHE).then((c) => c.put(request, resp.clone()));
          }
          return resp;
        })
      )
    );
  }
});
