// 영어 입 트레이너 — offline app shell. Study records and the API key live in this phone's localStorage, never on the server.
const CACHE = 'english-dae9facdc4';
const ASSETS = ["./", "index.html", "manifest.webmanifest", "icon-192.png", "icon-512.png", "icon-maskable-512.png", "apple-touch-icon.png", "favicon.png", "../fonts/jbm-400.woff2", "../fonts/jbm-500.woff2", "../fonts/jbm-600.woff2"];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k.startsWith('english-') && k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin !== self.location.origin) return;
  if (e.request.mode === 'navigate') {
    // the page itself: newest from the network (so updates show on the first open),
    // the saved copy when offline or when the network takes longer than 3 seconds
    const net = fetch(e.request).then(r => {
      if (r.ok) { const c = r.clone(); caches.open(CACHE).then(k => k.put('index.html', c)); }
      return r;
    });
    const saved = () => caches.match('index.html');
    const slow = new Promise(res => setTimeout(res, 3000)).then(saved).then(r => r || net);
    e.respondWith(Promise.race([net.catch(() => saved().then(r => r || Response.error())), slow]));
    return;
  }
  e.respondWith(
    caches.match(e.request, { ignoreSearch: true }).then(hit => hit || fetch(e.request).catch(() => Response.error()))
  );
});
