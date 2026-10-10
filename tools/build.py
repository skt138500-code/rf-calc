"""Build the offline app (index.html, sw.js, manifest) at the repo root from src/calc.html.

Usage: python3 tools/build.py   (needs Pillow only if icons are missing)
"""
import hashlib
import json
import pathlib
import re
import shutil


ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'src' / 'calc.html'
DIST = ROOT

# ---------- fonts ----------
for w in (400, 500, 600):
    assert (DIST / 'fonts' / f'jbm-{w}.woff2').exists(), 'fonts/ folder is missing'

# ---------- icons ----------
def icon(size, maskable_pad=0.0, radius=True):
    from PIL import Image, ImageDraw, ImageFont
    S = 1024
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    bg = (23, 33, 44, 255)
    if radius:
        d.rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.22), fill=bg)
    else:
        d.rectangle([0, 0, S, S], fill=bg)
    pad = int(S * (0.17 + maskable_pad))
    inner = S - 2 * pad
    # readout strip
    sh = int(inner * 0.30)
    d.rounded_rectangle([pad, pad, S - pad, pad + sh], radius=int(inner * 0.06), fill=(44, 57, 72, 255))
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf', int(sh * 0.62))
    text = 'RF'
    tb = d.textbbox((0, 0), text, font=font)
    tx = S - pad - int(inner * 0.07) - (tb[2] - tb[0]) - tb[0]
    ty = pad + (sh - (tb[3] - tb[1])) // 2 - tb[1]
    d.text((tx, ty), text, font=font, fill=(238, 243, 249, 255))
    cx = pad + int(inner * 0.08)
    d.rectangle([cx, pad + int(sh * 0.22), cx + int(inner * 0.025), pad + int(sh * 0.78)], fill=(239, 160, 79, 255))
    # keys 3 x 2
    gap = int(inner * 0.06)
    top = pad + sh + gap
    kw = (inner - 2 * gap) // 3
    kh = (S - pad - top - gap) // 2
    colors = [(215, 221, 230, 255)] * 5 + [(63, 130, 218, 255)]
    colors[0] = (239, 160, 79, 255)
    for r in range(2):
        for c in range(3):
            x0 = pad + c * (kw + gap)
            y0 = top + r * (kh + gap)
            d.rounded_rectangle([x0, y0, x0 + kw, y0 + kh], radius=int(kw * 0.18), fill=colors[r * 3 + c])
    return im.resize((size, size), Image.LANCZOS)

ICONS = {'icon-192.png': (192, 0.0, True), 'icon-512.png': (512, 0.0, True), 'icon-maskable-512.png': (512, 0.06, False),
         'apple-touch-icon.png': (180, 0.0, False), 'favicon.png': (64, 0.0, True)}
for name, (size, pad, rad) in ICONS.items():
    if not (DIST / name).exists():
        icon(size, pad, rad).save(DIST / name)

# ---------- manifest ----------
manifest = {
    'name': 'RF 공학계산기',
    'short_name': 'RF계산기',
    'description': '광고 없는 오프라인 공학계산기 — RF 변환, SSPA 전원 계산',
    'lang': 'ko',
    'start_url': './',
    'scope': './',
    'display': 'standalone',
    'orientation': 'portrait',
    'background_color': '#17212c',
    'theme_color': '#17212c',
    'icons': [
        {'src': 'icon-192.png', 'sizes': '192x192', 'type': 'image/png'},
        {'src': 'icon-512.png', 'sizes': '512x512', 'type': 'image/png'},
        {'src': 'icon-maskable-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
    ],
}
(DIST / 'manifest.webmanifest').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

# ---------- index.html ----------
src = SRC.read_text(encoding='utf-8')
title = re.search(r'<title>.*?</title>', src).group(0)
body = src.replace(title, '', 1)
body = re.sub(r'<link rel="preconnect"[^>]*>\s*', '', body)
body = re.sub(r'<link rel="stylesheet" href="https://fonts\.googleapis\.com[^>]*>\s*', '', body)
assert 'fonts.googleapis' not in body

head = f'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
{title}
<meta name="description" content="광고 없는 오프라인 공학계산기">
<meta name="theme-color" content="#e3e7ed" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0d1116" media="(prefers-color-scheme: dark)">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="RF계산기">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="format-detection" content="telephone=no">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" type="image/png" href="favicon.png">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<style>
@font-face{{font-family:"JetBrains Mono";font-weight:400;font-style:normal;font-display:swap;src:url(fonts/jbm-400.woff2) format("woff2")}}
@font-face{{font-family:"JetBrains Mono";font-weight:500;font-style:normal;font-display:swap;src:url(fonts/jbm-500.woff2) format("woff2")}}
@font-face{{font-family:"JetBrains Mono";font-weight:600;font-style:normal;font-display:swap;src:url(fonts/jbm-600.woff2) format("woff2")}}
:root{{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}
html,body{{overscroll-behavior:none}}
body{{margin:0;font-size:14px}}
img{{max-width:100%}}
[hidden]{{display:none!important}}
.install{{flex:none;display:flex;align-items:center;gap:8px;margin-bottom:8px;padding:8px 8px 8px 12px;background:var(--surface);border:1px solid var(--accent);border-radius:12px}}
.install-t{{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px;font-size:12px;color:var(--ink-soft);line-height:1.4}}
.install-t strong{{font-size:13px;color:var(--ink);font-weight:600}}
.install-go{{flex:none;border:0;background:var(--accent);color:var(--on-accent);border-radius:8px;padding:8px 12px;font:600 13px var(--font-ui);cursor:pointer}}
.install-x{{flex:none;border:0;background:transparent;color:var(--ink-soft);font:500 16px var(--font-ui);padding:6px 8px;cursor:pointer}}
</style>
</head>
<body>
'''

install_js = '''
<script>
(function () {
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () { navigator.serviceWorker.register('./sw.js').catch(function () {}); });
  }
  var standalone = (window.matchMedia && matchMedia('(display-mode: standalone)').matches) || navigator.standalone === true;
  if (standalone) return;
  try { if (localStorage.getItem('rfcalc.installDismissed') === '1') return; } catch (e) {}
  var ios = /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  var bar = document.createElement('div');
  bar.className = 'install';
  bar.innerHTML = '<div class="install-t"><strong>홈 화면에 설치하기</strong><span id="ins-msg">한 번 설치하면 인터넷 없이 앱처럼 열려요</span></div>' +
    '<button class="install-go" id="ins-go">' + (ios ? '방법 보기' : '설치') + '</button>' +
    '<button class="install-x" id="ins-x" aria-label="안내 닫기">✕</button>';
  document.querySelector('.app').prepend(bar);
  var deferred = null;
  window.addEventListener('beforeinstallprompt', function (e) { e.preventDefault(); deferred = e; });
  window.addEventListener('appinstalled', function () { bar.remove(); });
  document.getElementById('ins-go').addEventListener('click', function () {
    var msg = document.getElementById('ins-msg');
    if (deferred) {
      deferred.prompt();
      deferred.userChoice.then(function (r) { if (r.outcome === 'accepted') bar.remove(); deferred = null; });
      return;
    }
    msg.textContent = ios
      ? '아래쪽 공유 버튼(□↑) → "홈 화면에 추가" → 추가'
      : '오른쪽 위 메뉴(⋮) → "홈 화면에 추가" 또는 "앱 설치"';
    msg.style.color = 'var(--ink)';
  });
  document.getElementById('ins-x').addEventListener('click', function () {
    bar.remove();
    try { localStorage.setItem('rfcalc.installDismissed', '1'); } catch (e) {}
  });
})();
</script>
'''

index = head + body + install_js + '</body>\n</html>\n'
(DIST / 'index.html').write_text(index, encoding='utf-8')

# ---------- service worker ----------
assets = ['./', 'index.html', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png',
          'icon-maskable-512.png', 'apple-touch-icon.png', 'favicon.png',
          'fonts/jbm-400.woff2', 'fonts/jbm-500.woff2', 'fonts/jbm-600.woff2']
h = hashlib.sha256()
for a in assets[1:]:
    h.update((DIST / a).read_bytes())
version = h.hexdigest()[:10]
sw = f'''// RF 공학계산기 — offline cache
const CACHE = 'rfcalc-{version}';
const ASSETS = {json.dumps(assets)};
self.addEventListener('install', e => {{
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
}});
self.addEventListener('activate', e => {{
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k.startsWith('rfcalc-') && k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
}});
self.addEventListener('fetch', e => {{
  if (e.request.method !== 'GET') return;
  const path = new URL(e.request.url).pathname;
  if (path.includes('/stocks/') || path.includes('/car/')) return;  // the other apps have their own service workers
  e.respondWith(
    caches.match(e.request, {{ ignoreSearch: true }}).then(hit => hit || fetch(e.request).catch(() =>
      e.request.mode === 'navigate' ? caches.match('index.html') : Response.error()))
  );
}});
'''
(DIST / 'sw.js').write_text(sw, encoding='utf-8')
(DIST / '.nojekyll').write_text('')
print('built', version)
