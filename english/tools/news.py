"""English news headlines and news videos for the 영어 입 트레이너 듣기 tab.

Usage: python3 english/tools/news.py   (run by the publish workflow; refreshes at most once an hour)
Standard library only. Keeps headlines + links and YouTube video ids + titles only, never article
text or captions: the user copies the text into the app themselves. (YouTube refuses caption
requests from GitHub's servers, so captions could not be fetched here anyway.)
Writes english/data/news.json (published to gh-pages, not committed to main).
"""
import calendar
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
# YouTube news channels: (id, name, handle, known channel id). The handle is looked up when the id is unknown.
CHANNELS = [
    ('arirang', 'Arirang News', '@arirangcokrarirangnews', ''),
    ('cnn', 'CNN', '@CNN', 'UCupvZG-5ko_eiXAupbDfxWw'),
    ('bbcnews', 'BBC News', '@bbcnews', 'UC16niRr50-MSBwiO3YDb3RA'),
    ('dw', 'DW News', '@DWNews', 'UCknLrEdhRCp1aegoMqRaCZg'),
    ('bbcle', 'BBC Learning English', '@bbclearningenglish', 'UCHaHD477h-FeBbVh9Sh7syA'),
]
PER_CHANNEL = 10
VIDEO_DAYS = 7
ATOM = {'a': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
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


def get(url, tries=3):
    """YouTube feeds answer 404/500 now and then from cloud runners: try a few times."""
    last = None
    for i in range(tries):
        try:
            return fetch(url)
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise last


def channel_id(handle):
    req = urllib.request.Request('https://www.youtube.com/' + handle, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36', 'Accept-Language': 'en-US,en;q=0.8'})
    with urllib.request.urlopen(req, timeout=20) as r:
        page = r.read(3_000_000).decode('utf-8', 'replace')
    m = re.search(r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[\w-]{22})"', page) or re.search(r'"externalId":"(UC[\w-]{22})"', page)
    return m.group(1) if m else ''


def videos(cid):
    """Channel upload feed -> [{v, t, ts}] (no Shorts)."""
    root = ET.fromstring(get('https://www.youtube.com/feeds/videos.xml?channel_id=' + cid))
    out = []
    for e in root.findall('a:entry', ATOM):
        vid = e.findtext('yt:videoId', namespaces=ATOM) or ''
        link = e.find('a:link', ATOM)
        href = link.get('href', '') if link is not None else ''
        title = clean(e.findtext('a:title', namespaces=ATOM))
        if not re.fullmatch(r'[\w-]{11}', vid) or '/shorts/' in href or re.search(r'#shorts?\b', title, re.I) \
                or re.search(r'\[\s*live\s*\]|^\s*live\b|\blive stream|\blivestream|🔴', title, re.I):   # live streams have no fixed script
            continue
        ts = 0
        try:
            ts = calendar.timegm(time.strptime((e.findtext('a:published', namespaces=ATOM) or '')[:19], '%Y-%m-%dT%H:%M:%S'))
        except Exception:
            pass
        out.append({'v': vid, 't': title, 'ts': ts})
    return out


def collect_videos(old, now):
    known = dict(old.get('chan') or {})
    keep_after = now - VIDEO_DAYS * 86400
    vids, chans = [], []
    for key, name, handle, cid in CHANNELS:
        cid = cid or known.get(key, '')
        try:
            if not cid:
                cid = channel_id(handle)
            if not cid:
                raise ValueError('channel id not found for ' + handle)
            known[key] = cid
            rows = videos(cid)
            ok = True
        except Exception as e:
            print(f'english video: {key} failed: {e}')
            rows = [x for x in old.get('videos', []) if x.get('ch') == key]
            ok = False
        rows = [r for r in rows if r.get('ts', 0) >= keep_after]
        rows.sort(key=lambda r: r.get('ts', 0), reverse=True)
        rows = rows[:PER_CHANNEL]
        for r in rows:
            r['ch'] = key
        vids.extend(rows)
        chans.append({'id': key, 'name': name, 'ok': ok, 'n': len(rows)})
        print(f'english video: {key:9} {"ok " if ok else "old"} {len(rows)}')
        time.sleep(0.5)
    vids.sort(key=lambda r: r.get('ts', 0), reverse=True)
    return vids, chans, known


def main():
    old = {}
    if OUT.exists():
        try:
            old = json.loads(OUT.read_text(encoding='utf-8'))
        except Exception:
            old = {}
        if time.time() - old.get('made', 0) < EVERY and 'videos' in old:   # an older file without videos refreshes at once
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
    vids, chans, known = collect_videos(old, now)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({'made': now, 'sources': sources, 'items': items, 'channels': chans, 'videos': vids, 'chan': known},
                              ensure_ascii=False, separators=(',', ':')), encoding='utf-8')


if __name__ == '__main__':
    main()
