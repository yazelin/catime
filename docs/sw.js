const STATIC_CACHE = "catime-static-v6";   // html/css/js/icons — network-first, cache is offline fallback
const CATS_CACHE = "catime-cats-v1";       // cat images — immutable, kept across updates
const CATLIST_RE = /catlist\.json$/;
const ICON_RE = /(icon|favicon|apple-touch-icon)/;

// Precache the app shell + latest catlist on install, so the app reliably
// opens offline (gallery structure + the catlist snapshot) even on first run.
// (Cat images stay on-demand cache-first — too many/large to precache.)
const CORE = [
  "./", "index.html", "style.css", "app.js", "dom-utils.js",
  "character.html", "character.js", "manifest.json",
  "icon-192.png", "icon-512.png", "apple-touch-icon.png", "favicon-32.png", "favicon.ico",
  "catlist.json"
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

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);

  // Cat images: immutable → cache-first, persist forever. Once a cat is in the
  // cache it is NEVER re-fetched (opaque cross-origin responses are cached too).
  // ponytail: unbounded — fine for an append-only gallery; the browser evicts
  // under storage pressure. Add an LRU cap only if quota becomes a real problem.
  if (isCatImage(url)) {
    event.respondWith(
      caches.open(CATS_CACHE).then((cache) =>
        cache.match(request).then((hit) =>
          hit ||
          fetch(request).then((resp) => {
            if (resp && (resp.ok || resp.type === "opaque")) cache.put(request, resp.clone());
            return resp;
          })
        )
      )
    );
    return;
  }

  // catlist.json: changes as new cats ship → network-first, fall back to cache offline.
  if (CATLIST_RE.test(url.pathname) || url.href.includes("catlist.json")) {
    event.respondWith(
      fetch(request)
        .then((resp) => {
          if (resp && resp.ok) {
            const copy = resp.clone();
            caches.open(STATIC_CACHE).then((c) => c.put(request, copy));
          }
          return resp;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // App shell (html/css/js/icons): network-first so a deploy shows up on the
  // next load without cache-busting; fall back to cache only when offline.
  const isStatic =
    request.destination === "document" ||
    request.destination === "style" ||
    request.destination === "script" ||
    (request.destination === "image" && ICON_RE.test(url.pathname));
  if (isStatic) {
    event.respondWith(
      fetch(request)
        .then((resp) => {
          if (resp && resp.ok) {
            const copy = resp.clone();
            caches.open(STATIC_CACHE).then((c) => c.put(request, copy));
          }
          return resp;
        })
        .catch(() => caches.match(request))
    );
  }
});
