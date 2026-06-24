const STATIC_CACHE = "catime-static-v8";   // html/css/js/icons — network-first, cache is offline fallback
const CATS_CACHE = "catime-cats-v1";       // cat images — immutable, kept across updates
const CATLIST_RE = /catlist\.json$/;
const ICON_RE = /(icon|favicon|apple-touch-icon)/;
const RAW = "https://raw.githubusercontent.com/yazelin/catime/main/characters/";
const CATLIST_URL = "https://raw.githubusercontent.com/yazelin/catime/main/catlist.json";

// Precache the app shell + latest catlist + character data/avatars on install,
// so the app + character pages reliably work offline even on first run.
// (Cat images stay on-demand cache-first — too many/large to precache.)
const CORE = [
  "./", "index.html", "style.css", "app.js", "dom-utils.js",
  "character.html", "character.js", "manifest.json",
  "icon-192.png", "icon-512.png", "apple-touch-icon.png", "favicon-32.png", "favicon.ico",
  CATLIST_URL,
  "avatars/momo.webp", "avatars/captain.webp", "avatars/mochi.webp", "avatars/lingling.webp",
  RAW + "index.json", RAW + "momo.json", RAW + "captain.json", RAW + "mochi.json", RAW + "lingling.json"
];

// A cat image = a GitHub Release asset under any "cats" / "cats-YYYY-MM" tag.
// These never change once published, so they can be cached forever.
function isCatImage(url) {
  return /\/releases\/download\/cats[-/]/.test(url.href) && /\.(webp|png|jpe?g)$/i.test(url.pathname);
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((c) => Promise.allSettled(CORE.map((u) => c.add(u))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      // drop old static caches; KEEP the cats cache so viewed images survive updates
      Promise.all(keys
        .filter((k) => k !== STATIC_CACHE && k !== CATS_CACHE)
        .map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// network-first: try network (cache fresh), fall back to cache when offline.
function networkFirst(request) {
  return fetch(request).then((resp) => {
    if (resp && resp.ok) { const copy = resp.clone(); caches.open(STATIC_CACHE).then((c) => c.put(request, copy)); }
    return resp;
  }).catch(() => caches.match(request));
}
// cache-first: local copy wins; only fetch (and cache) when not cached.
function cacheFirst(request, cacheName) {
  return caches.open(cacheName).then((cache) =>
    cache.match(request).then((hit) =>
      hit || fetch(request).then((resp) => {
        if (resp && (resp.ok || resp.type === "opaque")) cache.put(request, resp.clone());
        return resp;
      })
    )
  );
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);

  // Cat images → cache-first (immutable, own persistent cache).
  if (isCatImage(url)) { event.respondWith(cacheFirst(request, CATS_CACHE)); return; }

  // catlist.json → stale-while-revalidate: serve the local copy instantly
  // (local-first, fast, offline-ok) and refresh the cache in the background.
  // A cache-busted request (?_=...) is the page asking for the truly-latest
  // list to diff for the "最新" band → straight to network, don't cache.
  if (CATLIST_RE.test(url.pathname) || url.href.includes("catlist.json")) {
    if (url.search) { event.respondWith(fetch(request)); return; }
    event.respondWith(
      caches.open(STATIC_CACHE).then((cache) =>
        cache.match(request).then((cached) => {
          const fresh = fetch(request).then((resp) => {
            if (resp && resp.ok) cache.put(request, resp.clone());
            return resp;
          }).catch(() => cached);
          return cached || fresh;
        })
      )
    );
    return;
  }

  // Code (html/css/js) → network-first (always pull the latest).
  if (request.destination === "document" || request.destination === "style" || request.destination === "script") {
    event.respondWith(networkFirst(request));
    return;
  }

  // Everything else (icons, avatars, character JSON, og image) → cache-first.
  const cacheable =
    (request.destination === "image" &&
      (ICON_RE.test(url.pathname) || /\/avatars\//.test(url.pathname) || /og-image/.test(url.pathname))) ||
    url.href.startsWith(RAW);
  if (cacheable) { event.respondWith(cacheFirst(request, STATIC_CACHE)); return; }
});
