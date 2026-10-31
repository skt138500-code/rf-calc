"""Write the English app's manifest, icons (when missing) and service worker.

Usage: python3 english/tools/build.py   (run after editing english/index.html)
"""
import hashlib
import json
import math
import pathlib

APP = pathlib.Path(__file__).resolve().parent.parent


def icon(size, pad=0.0, radius=True):
    """Night-blue tile (same ground as the other apps) with a speech bubble
    carrying a voice waveform that glows green to amber, like a carrier with an envelope."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter
    S = 2048

    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32) / (S - 1)
    t = np.clip((xx * 0.45 + yy * 0.75) / 1.2, 0, 1)[..., None]
    top, bot = np.array([36, 54, 84], np.float32), np.array([10, 17, 29], np.float32)
    bg = top + (bot - top) * t
    d = np.sqrt((xx - 0.5) ** 2 + (yy - 0.47) ** 2)
    glow = np.clip(1 - d / 0.55, 0, 1) ** 2.4 * 0.20
    bg = bg + (np.array([120, 230, 160], np.float32) - bg) * glow[..., None]
    im = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')

    sc = 1 - 2 * pad
    cx, cy = S / 2, S * 0.47
    bw, bh = S * 0.66 * sc, S * 0.44 * sc
    x0, y0, x1, y1 = cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2
    lw = int(S * 0.026 * sc)

    # bubble: dark glass fill, light outline, tail at the lower left
    bub = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    db = ImageDraw.Draw(bub)
    r = bh * 0.30
    tail = [(x0 + bw * 0.20, y1 - lw), (x0 + bw * 0.13, y1 + bh * 0.30), (x0 + bw * 0.40, y1 - lw)]
    db.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=(6, 10, 15, 235))
    db.polygon(tail, fill=(6, 10, 15, 235))
    im = Image.alpha_composite(im, bub)
    ol = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    do = ImageDraw.Draw(ol)
    do.rounded_rectangle([x0, y0, x1, y1], radius=r, outline=(220, 230, 242, 255), width=lw)
    do.line([tail[0], tail[1], tail[2]], fill=(220, 230, 242, 255), width=lw, joint='curve')
    do.rectangle([tail[0][0] + lw * 0.6, y1 - lw * 1.2, tail[2][0] - lw * 0.6, y1 + lw * 0.2], fill=(6, 10, 15, 255))
    im = Image.alpha_composite(im, ol)

    # waveform: a carrier under a speech-like envelope, green to amber, with a soft glow
    wav = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    dw = ImageDraw.Draw(wav)
    wx0, wx1 = x0 + bw * 0.12, x1 - bw * 0.12
    amp = bh * 0.30
    n = 700
    pts = []
    for i in range(n + 1):
        u = i / n
        env = math.sin(math.pi * u) ** 1.2 * (0.55 + 0.45 * abs(math.sin(u * math.pi * 2.6 + 0.4)))
        y = cy + math.sin(u * math.pi * 2 * 7.5) * amp * env
        pts.append((wx0 + (wx1 - wx0) * u, y))
    c0, c1 = np.array([143, 227, 166]), np.array([255, 196, 104])
    ww = int(S * 0.022 * sc)
    for i in range(n):
        col = tuple(int(v) for v in c0 + (c1 - c0) * (i / (n - 1)))
        dw.line([pts[i], pts[i + 1]], fill=col + (255,), width=ww)
    for p, col in ((pts[0], (143, 227, 166, 255)), (pts[-1], (255, 196, 104, 255))):
        dw.ellipse([p[0] - ww / 2, p[1] - ww / 2, p[0] + ww / 2, p[1] + ww / 2], fill=col)
    halo = wav.filter(ImageFilter.GaussianBlur(S * 0.02))
    im = Image.alpha_composite(im, halo)
    im = Image.alpha_composite(im, wav)

    if radius:
        rm = Image.new('L', (S, S), 0)
        ImageDraw.Draw(rm).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.225), fill=255)
        im.putalpha(rm)
    out = im.resize((size, size), Image.LANCZOS)
    return out if radius else out.convert('RGB')


ICONS = {'icon-192.png': (192, 0.0, True), 'icon-512.png': (512, 0.0, True),
         'icon-maskable-512.png': (512, 0.08, False), 'apple-touch-icon.png': (180, 0.0, False),
         'favicon.png': (64, 0.0, True)}
for name, (size, pad, rad) in ICONS.items():
    if not (APP / name).exists():
        icon(size, pad, rad).save(APP / name)

manifest = {
    'name': '영어 입 트레이너', 'short_name': '영어 입',
    'description': '학회 발표·질의응답 영어와 CNN 뉴스 듣기 — 듣고, 해석 보고, 따라 말하기', 'lang': 'ko',
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
sw = f'''// 영어 입 트레이너 — offline app shell. Study records and the API key live in this phone's localStorage, never on the server.
const CACHE = 'english-{version}';
const ASSETS = {json.dumps(assets)};
self.addEventListener('install', e => {{
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
}});
self.addEventListener('activate', e => {{
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k.startsWith('english-') && k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
}});
self.addEventListener('fetch', e => {{
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin !== self.location.origin) return;
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
    caches.match(e.request, {{ ignoreSearch: true }}).then(hit => hit || fetch(e.request).catch(() => Response.error()))
  );
}});
'''
(APP / 'sw.js').write_text(sw, encoding='utf-8')
print('built english', version)
