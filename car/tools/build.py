"""Write the car app's manifest, icons (when missing) and service worker.

Usage: python3 car/tools/build.py   (run after editing car/index.html)
"""
import hashlib
import json
import math
import pathlib

APP = pathlib.Path(__file__).resolve().parent.parent


def icon(size, pad=0.0, radius=True):
    """Night-blue tile (same ground as 내 주식) with an instrument-cluster gauge:
    faint track and ticks, a green-to-amber arc with a soft glow, a coral needle near the end."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter
    S = 2048

    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32) / (S - 1)
    t = np.clip((xx * 0.45 + yy * 0.75) / 1.2, 0, 1)[..., None]
    top, bot = np.array([36, 54, 84], np.float32), np.array([10, 17, 29], np.float32)
    bg = top + (bot - top) * t
    d = np.sqrt((xx - 0.5) ** 2 + (yy - 0.56) ** 2)
    glow = np.clip(1 - d / 0.55, 0, 1) ** 2.4 * 0.22
    bg = bg + (np.array([120, 230, 160], np.float32) - bg) * glow[..., None]
    im = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')

    scale = 1 - 2 * pad
    cx, cy = S / 2, S * (0.5 + 0.06 * scale)
    R = S * 0.315 * scale
    lw = S * 0.062 * scale
    a0, a1 = 150, 390            # PIL angles: clockwise from 3 o'clock, gap at the bottom
    val = 0.78                   # how far the arc is filled
    box = [cx - R, cy - R, cx + R, cy + R]

    lay = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    dl.arc(box, a0, a1, fill=(255, 255, 255, 34), width=int(lw))
    for k in range(13):          # ticks inside the track
        a = math.radians(a0 + (a1 - a0) * k / 12)
        r1, r2 = R - lw * 0.95, R - lw * (1.55 if k % 3 == 0 else 1.3)
        dl.line([(cx + r1 * math.cos(a), cy + r1 * math.sin(a)), (cx + r2 * math.cos(a), cy + r2 * math.sin(a))],
                fill=(255, 255, 255, 120 if k % 3 == 0 else 60), width=max(2, int(S * 0.012 * scale)))
    im = Image.alpha_composite(im, lay)

    # filled arc: many short segments from green to amber, plus a blurred copy as glow
    arc = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    da = ImageDraw.Draw(arc)
    end = a0 + (a1 - a0) * val
    n = 160
    c0, c1 = np.array([143, 227, 166]), np.array([255, 196, 104])
    for i in range(n):
        s = a0 + (end - a0) * i / n
        e = a0 + (end - a0) * (i + 1) / n + 0.6
        col = tuple(int(v) for v in c0 + (c1 - c0) * (i / (n - 1)))
        da.arc(box, s, e, fill=col + (255,), width=int(lw))
    for a in (a0, end):          # round caps
        r = math.radians(a)
        px, py = cx + (R - lw / 2) * math.cos(r), cy + (R - lw / 2) * math.sin(r)
        col = (143, 227, 166, 255) if a == a0 else (255, 196, 104, 255)
        da.ellipse([px - lw / 2, py - lw / 2, px + lw / 2, py + lw / 2], fill=col)
    halo = arc.filter(ImageFilter.GaussianBlur(S * 0.022))
    im = Image.alpha_composite(im, halo)
    im = Image.alpha_composite(im, arc)

    # needle and hub
    nd = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    dn = ImageDraw.Draw(nd)
    a = math.radians(end)
    L = R - lw * 1.7
    w = S * 0.034 * scale
    tip = (cx + L * math.cos(a), cy + L * math.sin(a))
    nx, ny = -math.sin(a), math.cos(a)
    back = (cx - S * 0.05 * scale * math.cos(a), cy - S * 0.05 * scale * math.sin(a))
    dn.polygon([tip, (cx + nx * w, cy + ny * w), back, (cx - nx * w, cy - ny * w)], fill=(255, 118, 104, 255))
    hr = S * 0.062 * scale
    dn.ellipse([cx - hr, cy - hr, cx + hr, cy + hr], fill=(240, 244, 250, 255))
    hr2 = hr * 0.42
    dn.ellipse([cx - hr2, cy - hr2, cx + hr2, cy + hr2], fill=(23, 33, 44, 255))
    shadow = nd.filter(ImageFilter.GaussianBlur(S * 0.012))
    sh = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    sh.putalpha(shadow.getchannel('A').point(lambda v: int(v * 0.5)))
    im = Image.alpha_composite(im, sh)
    im = Image.alpha_composite(im, nd)

    # a short odometer bar under the gauge
    dd = ImageDraw.Draw(im)
    bw_, bh_ = S * 0.30 * scale, S * 0.075 * scale
    by = cy + R * 0.62
    dd.rounded_rectangle([cx - bw_ / 2, by, cx + bw_ / 2, by + bh_], radius=bh_ * 0.22, fill=(6, 10, 15, 255), outline=(60, 78, 100, 255), width=max(2, int(S * 0.004)))
    for k in range(5):
        x = cx - bw_ / 2 + bw_ * (k + 0.5) / 5
        dd.rounded_rectangle([x - bw_ * 0.06, by + bh_ * 0.28, x + bw_ * 0.06, by + bh_ * 0.72], radius=bh_ * 0.08,
                             fill=(238, 243, 249, 210 if k < 4 else 255) if k < 4 else (143, 227, 166, 255))

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
    'name': '차량관리', 'short_name': '차량관리',
    'description': '광고 없는 차량관리 앱 — 다음 정비, 정비 이력, 비용', 'lang': 'ko',
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
sw = f'''// 차량관리 — offline app shell. Records live in this phone's localStorage, never on the server.
const CACHE = 'car-{version}';
const ASSETS = {json.dumps(assets)};
self.addEventListener('install', e => {{
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
}});
self.addEventListener('activate', e => {{
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k.startsWith('car-') && k !== CACHE).map(k => caches.delete(k))))
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
print('built car', version)
