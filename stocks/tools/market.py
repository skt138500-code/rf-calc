"""Market indices and news headlines for the 시장 tab.

Called from fetch.py. Standard library only.
- indices(): main indexes, VIX, US 10-year yield and bitcoin (Yahoo chart API, same as quotes)
- news(): headlines + links only (no article text), at most once an hour:
  market news from Google News (Korean), per-stock news from Google News (Korean),
  topped up with Yahoo Finance headlines (English) for US stocks with little Korean coverage.
"""
import email.utils
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

INDICES = [
    ('^KS11', '코스피'), ('^KQ11', '코스닥'), ('^GSPC', 'S&P 500'), ('^IXIC', '나스닥'),
    ('^SOX', '필라델피아 반도체'), ('^VIX', 'VIX 변동성'), ('^TNX', '미국 10년 금리'), ('BTC-USD', '비트코인'),
]
NEWS_EVERY = 55 * 60          # seconds between news refreshes
NEWS_DAYS = 3                 # keep headlines from the last few days
PER_STOCK = 6
MARKET_QUERIES = ['코스피 증시', '뉴욕증시']


def indices(chart, thin):
    out = []
    for sym, name in INDICES:
        try:
            res = chart(sym, '1d', '5m')
        except Exception as e:  # one index failing must not stop the rest
            print(f'idx  {sym:8} {e}')
            continue
        meta = res.get('meta') or {}
        price = meta.get('regularMarketPrice')
        prev = meta.get('chartPreviousClose') or meta.get('previousClose')
        if price is None:
            continue
        closes = [round(float(c), 4) for c in (((res.get('indicators') or {}).get('quote') or [{}])[0].get('close') or []) if c is not None]
        item = {'sym': sym, 'name': name, 'price': price, 'prev': prev, 'cur': meta.get('currency') or '',
                'time': meta.get('regularMarketTime'), 'tz': meta.get('exchangeTimezoneName') or 'UTC', 'spark': thin(closes, 48)}
        if prev:
            item['chg'] = round(price - prev, 4)
            item['pct'] = round((price - prev) / prev * 100, 3)
        out.append(item)
        time.sleep(0.3)
    return out


def _rss(url, ua):
    req = urllib.request.Request(url, headers={'User-Agent': ua, 'Accept': 'application/rss+xml, application/xml, text/xml'})
    with urllib.request.urlopen(req, timeout=15) as r:
        root = ET.fromstring(r.read(3_000_000))
    out = []
    for it in root.iter('item'):
        title = (it.findtext('title') or '').strip()
        link = (it.findtext('link') or '').strip()
        src_el = it.find('source')
        src = (src_el.text or '').strip() if src_el is not None else ''
        try:
            ts = int(email.utils.parsedate_to_datetime(it.findtext('pubDate')).timestamp())
        except Exception:
            ts = 0
        if src and title.endswith(' - ' + src):
            title = title[: -len(src) - 3].strip()
        if title and link.startswith('http'):
            out.append({'t': ts, 'title': title[:200], 'src': src[:40], 'link': link})
    return out


def _google(q):
    return 'https://news.google.com/rss/search?' + urllib.parse.urlencode({'q': q, 'hl': 'ko', 'gl': 'KR', 'ceid': 'KR:ko'})


def _yahoo(ticker):
    return 'https://feeds.finance.yahoo.com/rss/2.0/headline?' + urllib.parse.urlencode({'s': ticker, 'region': 'US', 'lang': 'en-US'})


def _pick(rows, n, since):
    seen, out = set(), []
    for r in sorted(rows, key=lambda r: -r['t']):
        key = re.sub(r'\W+', '', r['title'])[:40]
        if r['t'] and r['t'] < since or key in seen:
            continue
        seen.add(key)
        out.append(r)
        if len(out) >= n:
            break
    return out


def news(path, stocks, ua):
    """stocks: [(code, name, is_korean)]. Writes path (news.json) when it is due; returns nothing."""
    try:
        old = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        old = {}
    if time.time() - old.get('updated', 0) < NEWS_EVERY and set(old.get('stocks', {})) >= {c for c, _, _ in stocks}:
        return
    since = time.time() - NEWS_DAYS * 86400
    data = {'updated': int(time.time()), 'market': [], 'stocks': {}}
    rows = []
    for q in MARKET_QUERIES:
        try:
            rows += _rss(_google(q + ' when:1d'), ua)
        except Exception as e:
            print(f'news market {q}: {e}')
        time.sleep(0.6)
    data['market'] = _pick(rows, 12, since) or old.get('market', [])
    for code, name, kr in stocks:
        rows = []
        hangul = re.search(r'[가-힣]', name or '')
        # a Korean name searches well as is; a bare ticker (MAIN, O) matches too much, so keep only
        # headlines that carry the ticker itself, e.g. "뱅크 오브 아메리카(BAC) 주가"
        q = f'"{name}" when:{NEWS_DAYS}d' if hangul else f'"{code}" 주가 when:7d'
        try:
            rows = _rss(_google(q), ua)
        except Exception as e:
            print(f'news {code}: {e}')
        if not hangul:
            rows = [r for r in rows if re.search(r'(?<![A-Za-z])' + re.escape(code) + r'(?![A-Za-z])', r['title'])]
        time.sleep(0.6)
        picked = _pick(rows, PER_STOCK, since if hangul else time.time() - 7 * 86400)
        if not kr and len(picked) < 3:
            try:
                en = _rss(_yahoo(code), ua)
                for r in en:
                    r['en'] = True
                picked = _pick(picked + en, PER_STOCK, time.time() - 7 * 86400)
            except Exception as e:
                print(f'news {code} yahoo: {e}')
            time.sleep(0.6)
        data['stocks'][code] = picked or old.get('stocks', {}).get(code, [])
        print(f'news {code:8} {len(data["stocks"][code])}')
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
