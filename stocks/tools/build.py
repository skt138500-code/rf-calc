"""Write the stock app's manifest, icons (when missing) and service worker.

Usage: python3 stocks/tools/build.py   (run after editing stocks/index.html)
"""
import hashlib
import json
import pathlib

APP = pathlib.Path(__file__).resolve().parent.parent
ROOT = APP.parent


def icon(size, pad=0.0, radius=True):
    from PIL import Image, ImageDraw
    S = 1024
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    bg = (23, 33, 44, 255)
    if radius:
        d.rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.22), fill=bg)
    else:
        d.rectangle([0, 0, S, S], fill=bg)
    m = int(S * (0.18 + pad))
    w = S - 2 * m
    for k in range(4):  # faint grid
        y = m + int(w * (0.15 + 0.25 * k))
        d.line([(m, y), (S - m, y)], fill=(44, 57, 72, 255), width=int(S * 0.008))
    pts = [(0.00, 0.78), (0.16, 0.62), (0.30, 0.70), (0.46, 0.44), (0.60, 0.52), (0.78, 0.26), (1.00, 0.12)]
    xy = [(m + int(w * x), m + int(w * y)) for x, y in pts]
    area = xy + [(S - m, S - m), (m, S - m)]
    overlay = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(overlay).polygon(area, fill=(255, 122, 112, 60))
    im = Image.alpha_composite(im, overlay)
    d = ImageDraw.Draw(im)
    d.line(xy, fill=(255, 122, 112, 255), width=int(S * 0.045), joint='curve')
    ex, ey = xy[-1]
    r = int(S * 0.05)
    d.ellipse([ex - r, ey - r, ex + r, ey + r], fill=(238, 243, 249, 255))
    return im.resize((size, size), Image.LANCZOS)


ICONS = {'icon-192.png': (192, 0.0, True), 'icon-512.png': (512, 0.0, True),
         'icon-maskable-512.png': (512, 0.06, False), 'apple-touch-icon.png': (180, 0.0, False),
         'favicon.png': (64, 0.0, True)}
for name, (size, pad, rad) in ICONS.items():
    if not (APP / name).exists():
        icon(size, pad, rad).save(APP / name)

manifest = {
    'name': '내 주식', 'short_name': '내 주식',
    'description': '광고 없는 관심종목·보유 수익률 앱', 'lang': 'ko',
    'start_url': './', 'scope': './', 'display': 'standalone', 'orientation': 'portrait',
    'background_color': '#17212c', 'theme_color': '#17212c',
    'icons': [
        {'src': 'icon-192.png', 'sizes': '192x192', 'type': 'image/png'},
        {'src': 'icon-512.png', 'sizes': '512x512', 'type': 'image/png'},
        {'src': 'icon-maskable-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
    ],
}
(APP / 'manifest.webmanifest').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

assets = ['./', 'index.html', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'icon-maskable-512.png',
          'apple-touch-icon.png', 'favicon.png', '../fonts/jbm-400.woff2', '../fonts/jbm-500.woff2', '../fonts/jbm-600.woff2']
h = hashlib.sha256()
for a in assets[1:]:
    h.update(((APP / a).resolve()).read_bytes())
version = h.hexdigest()[:10]
sw = f'''// 내 주식 — offline app shell. Prices (data/) always come from the network;
// the page keeps its own last copy for offline use.
const CACHE = 'stocks-{version}';
const ASSETS = {json.dumps(assets)};
self.addEventListener('install', e => {{
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
}});
self.addEventListener('activate', e => {{
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k.startsWith('stocks-') && k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
}});
self.addEventListener('fetch', e => {{
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin !== self.location.origin) return;  // GitHub API etc. go straight to the network
  if (url.pathname.includes('/stocks/data/')) return;
  e.respondWith(
    caches.match(e.request, {{ ignoreSearch: true }}).then(hit => hit || fetch(e.request).catch(() =>
      e.request.mode === 'navigate' ? caches.match('index.html') : Response.error()))
  );
}});
'''
(APP / 'sw.js').write_text(sw, encoding='utf-8')
print('built stocks', version)
