"""English news headlines for the 영어 입 트레이너 듣기 tab.

Usage: python3 english/tools/news.py   (run by the publish workflow; refreshes at most once an hour)
Standard library only. Keeps headlines + links only, never article text: the user opens the
story on its own site and copies the text into the app themselves.
Writes english/data/news.json (published to gh-pages, not committed to main).
"""
import email.utils
import html
import json
import pathlib
import re
import time
import urllib.request
import xml.etree.ElementTree as ET

APP = pathlib.Path(__file__).resolve().parent.parent
OUT = APP / 'data' / 'news.json'
EVERY = 55 * 60      # seconds between refreshes
KEEP_DAYS = 5
PER_SOURCE = 12
UA = 'Mozilla/5.0 (rf-calc english app; +https://github.com/skt138500-code/rf-calc)'

# (group, id, name, feed)
FEEDS = [
    ('easy', 'nil', 'News in Levels', 'https://www.newsinlevels.com/feed/'),
    ('easy', 'bne', 'Breaking News English', 'https://breakingnewsenglish.com/bne.xml'),
    ('world', 'bbc', 'BBC World', 'https://feeds.bbci.co.uk/news/world/rss.xml'),
    ('world', 'npr', 'NPR World', 'https://feeds.npr.org/1004/rss.xml'),
    ('world', 'guardian', 'The Guardian', 'https://www.theguardian.com/world/rss'),
    ('science', 'pw', 'Physics World', 'https://physicsworld.com/feed/'),
]
LEVEL = re.compile(r'\s*[–—-]\s*level\s*(\d)\s*$', re.I)
PROMO = re.compile(r'easy speaking in english|english course|e-?book', re.I)


def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s or ''))).strip()


def when(s):
    try:
        return int(email.utils.parsedate_to_datetime(s).timestamp())
    except Exception:
        return 0


def parse(xml_bytes):
    """RSS 2.0 items -> [{t, url, ts}] (titles and links only)."""
    root = ET.fromstring(xml_bytes)
    out = []
    for it in root.iter('item'):
        t = clean(it.findtext('title'))
        url = (it.findtext('link') or '').strip()
        if not t or not url.startswith('http'):
            continue
        out.append({'t': t, 'url': url, 'ts': when(it.findtext('pubDate') or '')})
    return out


def shape(src, items):
    """Per-source tidy-up. News in Levels posts each story three times (level 1-3): fold them into one row."""
    if src == 'nil':
        groups = {}
        for it in items:
            if PROMO.search(it['t']):
                continue                      # the site's own course adverts, not news
            m = LEVEL.search(it['t'])
            if not m:
                continue
            base = LEVEL.sub('', it['t']).strip()
            g = groups.setdefault(base, {'t': base, 'url': '', 'ts': 0, 'lv': {}})
            g['lv'][m.group(1)] = it['url']
            g['ts'] = max(g['ts'], it['ts'])
        rows = []
        for g in groups.values():
            g['url'] = g['lv'].get('2') or g['lv'].get('1') or next(iter(g['lv'].values()))
            g['lv'] = dict(sorted(g['lv'].items()))
            rows.append(g)
        return rows
    return items


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/rss+xml, application/xml, text/xml'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read(4_000_000)


def main():
    old = {}
    if OUT.exists():
        try:
            old = json.loads(OUT.read_text(encoding='utf-8'))
        except Exception:
            old = {}
        if time.time() - old.get('made', 0) < EVERY:
            print('english news: fresh enough, skipped')
            return
    now = int(time.time())
    keep_after = now - KEEP_DAYS * 86400
    items, sources = [], []
    for group, sid, name, url in FEEDS:
        try:
            rows = shape(sid, parse(fetch(url)))
            ok = True
        except Exception as e:                 # one feed failing keeps its previous headlines
            print(f'english news: {sid} failed: {e}')
            rows = [x for x in old.get('items', []) if x.get('src') == sid]
            ok = False
        rows = [r for r in rows if r.get('ts', 0) >= keep_after or not r.get('ts')]
        rows.sort(key=lambda r: r.get('ts', 0), reverse=True)
        rows = rows[:PER_SOURCE]
        for r in rows:
            r['src'] = sid
        items.extend(rows)
        sources.append({'id': sid, 'name': name, 'group': group, 'ok': ok, 'n': len(rows)})
        print(f'english news: {sid:9} {"ok " if ok else "old"} {len(rows)}')
        time.sleep(0.5)
    items.sort(key=lambda r: r.get('ts', 0), reverse=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({'made': now, 'sources': sources, 'items': items}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')


if __name__ == '__main__':
    main()
