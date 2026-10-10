"""Write the stock app's manifest, icons (when missing) and service worker.

Usage: python3 stocks/tools/build.py   (run after editing stocks/index.html)
"""
import hashlib
import json
import pathlib

APP = pathlib.Path(__file__).resolve().parent.parent
ROOT = APP.parent


def icon(size, pad=0.0, radius=True):
    """Night-blue tile, soft grid and volume bars, a glowing coral-to-amber trend line ending in a bright dot."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter
    S = 2048  # draw big, scale down for clean edges

    # background: diagonal gradient + warm glow where the line ends
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32) / (S - 1)
    t = np.clip((xx * 0.45 + yy * 0.75) / 1.2, 0, 1)[..., None]
    top, bot = np.array([36, 54, 84], np.float32), np.array([10, 17, 29], np.float32)
    bg = top + (bot - top) * t
    gx, gy = 0.80, 0.22
    d = np.sqrt((xx - gx) ** 2 + (yy - gy) ** 2)
    glow = np.clip(1 - d / 0.62, 0, 1) ** 2.2 * 0.30
    bg = bg + (np.array([255, 120, 92], np.float32) - bg) * glow[..., None]
    im = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')

    m = int(S * (0.17 + pad))          # content box
    w = S - 2 * m
    X = lambda u: m + u * w
    Y = lambda v: m + v * w
    lay = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    for k in range(4):                 # faint grid
        y = Y(0.12 + 0.25 * k)
        dl.line([(X(-0.04), y), (X(1.04), y)], fill=(255, 255, 255, 18), width=max(2, S // 340))
    heights = [0.16, 0.24, 0.20, 0.32, 0.27, 0.40, 0.48]   # volume bars
    bw = w / len(heights) * 0.46
    for i, h in enumerate(heights):
        cx = X((i + 0.5) / len(heights))
        dl.rounded_rectangle([cx - bw / 2, Y(1.0) - h * w * 0.55, cx + bw / 2, Y(1.0)], radius=bw * 0.28, fill=(120, 165, 235, 46))
    im = Image.alpha_composite(im, lay)

    # smooth trend line (Catmull-Rom through the points)
    pts = [(0.00, 0.80), (0.14, 0.66), (0.27, 0.71), (0.42, 0.50), (0.56, 0.57), (0.72, 0.34), (0.86, 0.25), (1.00, 0.10)]
    P = [pts[0]] + pts + [pts[-1]]
    curve = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for j in range(24):
            u = j / 24
            u2, u3 = u * u, u * u * u
            curve.append(tuple(0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * u + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * u2 + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * u3) for k in range(2)))
    curve.append(pts[-1])
    xy = [(X(a), Y(b)) for a, b in curve]

    # area under the line: brightest right under the line, fading toward the bottom
    cx_ = np.array([q[0] for q in xy], np.float32)
    cy_ = np.array([q[1] for q in xy], np.float32)
    cols = np.arange(S, dtype=np.float32)
    lineY = np.interp(cols, cx_, cy_)
    inside = (cols >= cx_[0]) & (cols <= cx_[-1])
    base = Y(1.0)
    py = np.arange(S, dtype=np.float32)[:, None]
    depth = (py - lineY[None, :]) / np.maximum(base - lineY[None, :], 1)
    a = np.where((depth >= 0) & (depth <= 1) & inside[None, :], (1 - np.clip(depth, 0, 1)) ** 1.8 * 0.55, 0)
    area = np.zeros((S, S, 4), np.uint8)
    area[..., 0], area[..., 1], area[..., 2] = 255, 112, 96
    area[..., 3] = (a * 255).astype(np.uint8)
    im = Image.alpha_composite(im, Image.fromarray(area, 'RGBA'))

    # the line itself: glow, then a left-to-right coral → amber stroke
    lw = int(S * 0.052)
    stroke = Image.new('L', (S, S), 0)
    ds = ImageDraw.Draw(stroke)
    # round brush along a densely resampled path: smooth edges, no notches at the joins
    dense = []
    for (x0, y0), (x1, y1) in zip(xy, xy[1:]):
        n = max(1, int(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5 / 3))
        dense += [(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n)]
    dense.append(xy[-1])
    for q in dense:
        ds.ellipse([q[0] - lw / 2, q[1] - lw / 2, q[0] + lw / 2, q[1] + lw / 2], fill=255)
    halo = stroke.filter(ImageFilter.GaussianBlur(S * 0.028))
    hl = Image.new('RGBA', (S, S), (255, 110, 90, 0))
    hl.putalpha(halo.point(lambda v: int(v * 0.75)))
    im = Image.alpha_composite(im, hl)
    gcol = np.zeros((S, S, 4), np.uint8)
    c0, c1 = np.array([255, 96, 104], np.float32), np.array([255, 196, 104], np.float32)
    tt = np.clip((xx - m / S) / (w / S), 0, 1)[..., None]
    gcol[..., :3] = (c0 + (c1 - c0) * tt).astype(np.uint8)
    gcol[..., 3] = np.array(stroke)
    im = Image.alpha_composite(im, Image.fromarray(gcol, 'RGBA'))

    # bright end point with a soft ring
    ex, ey = xy[-1]
    ring = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(ring)
    R = S * 0.088
    dr.ellipse([ex - R, ey - R, ex + R, ey + R], fill=(255, 205, 120, 70))
    ring = ring.filter(ImageFilter.GaussianBlur(S * 0.01))
    im = Image.alpha_composite(im, ring)
    dd = ImageDraw.Draw(im)
    r = S * 0.05
    dd.ellipse([ex - r, ey - r, ex + r, ey + r], fill=(255, 250, 240, 255))

    if radius:
        rm = Image.new('L', (S, S), 0)
        ImageDraw.Draw(rm).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.225), fill=255)
        im.putalpha(rm)
    out = im.resize((size, size), Image.LANCZOS)
    return out if radius else out.convert('RGB')


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
const LOGOS = 'stocks-logos';   // kept across app updates
const ASSETS = {json.dumps(assets)};
self.addEventListener('install', e => {{
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
}});
self.addEventListener('activate', e => {{
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k.startsWith('stocks-') && k !== CACHE && k !== LOGOS).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
}});
self.addEventListener('fetch', e => {{
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin !== self.location.origin) return;  // GitHub API etc. go straight to the network
  if (url.pathname.includes('/stocks/data/logos/')) {{
    // logos rarely change: saved copy first, so they show offline too
    e.respondWith(caches.open(LOGOS).then(k => k.match(e.request).then(hit => hit || fetch(e.request).then(r => {{
      if (r.ok) k.put(e.request, r.clone());
      return r;
    }}))));
    return;
  }}
  if (url.pathname.includes('/stocks/data/')) return;
  if (e.request.mode === 'navigate') {{
    // the page itself: newest from the network (so updates show on the first open),
    // the saved copy when offline or when the network takes longer than 3 seconds
    const net = fetch(e.request).then(r => {{
      if (r.ok) {{ const c = r.clone(); caches.open(CACHE).then(k => k.put('index.html', c)); }}
      return r;
    }});
    const saved = () => caches.match('index.html');
    const slow = new Promise(res => setTimeout(res, 3000)).then(saved).then(r => r || net);
    e.respondWith(Promise.race([net.catch(() => saved().then(r => r || Response.error())), slow]));
    return;
  }}
  e.respondWith(
    caches.match(e.request, {{ ignoreSearch: true }}).then(hit => hit || fetch(e.request).catch(() =>
      e.request.mode === 'navigate' ? caches.match('index.html') : Response.error()))
  );
}});
'''
(APP / 'sw.js').write_text(sw, encoding='utf-8')
print('built stocks', version)
