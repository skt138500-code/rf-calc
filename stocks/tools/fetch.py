#!/usr/bin/env python3
"""Fetch quotes and price history for every stock listed in stocks/watch/.

Each file in stocks/watch/ is one stock: the file name is the code
(6-digit KRX code like 005930, or a US ticker like TSLA) and the first line
of the file is the name shown in the app.

Writes stocks/data/quotes.json and stocks/data/hist/<symbol>.json.
Uses only the Python standard library. Data source: Yahoo Finance chart API.
If a stock fails this run, its previous data (restored from gh-pages by the
workflow) is kept and marked stale.
"""
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
WATCH = ROOT / 'watch'
OUT = ROOT / 'data'
HIST = OUT / 'hist'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')
HOSTS = ['query1.finance.yahoo.com', 'query2.finance.yahoo.com']
EXCHANGES = {
    'KSC': '코스피', 'KOE': '코스닥', 'NMS': '나스닥', 'NGM': '나스닥', 'NCM': '나스닥',
    'NYQ': 'NYSE', 'PCX': 'NYSE Arca', 'ASE': 'NYSE American', 'BTS': 'Cboe',
}


class NotFound(Exception):
    pass


def chart(sym, rng, interval):
    query = urllib.parse.urlencode({'range': rng, 'interval': interval, 'includePrePost': 'false'})
    last = None
    for attempt in range(4):
        host = HOSTS[attempt % 2]
        url = f'https://{host}/v8/finance/chart/{urllib.parse.quote(sym)}?{query}'
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                body = json.load(r)
            res = (body.get('chart') or {}).get('result')
            if not res:
                raise NotFound(sym)
            return res[0]
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise NotFound(sym)
            last = f'HTTP {e.code}'
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last = str(e)
        time.sleep(2 + attempt * 3)
    raise RuntimeError(last or 'request failed')


def series(res):
    ts = res.get('timestamp') or []
    quote = ((res.get('indicators') or {}).get('quote') or [{}])[0]
    closes = quote.get('close') or []
    t, c = [], []
    for a, b in zip(ts, closes):
        if b is None:
            continue
        t.append(int(a))
        c.append(round(float(b), 4))
    return {'t': t, 'c': c}


def candidates(code):
    if re.fullmatch(r'\d{6}', code):
        return [code + '.KS', code + '.KQ']
    up = code.upper()
    out = [up]
    if '.' in up and not re.search(r'\.(KS|KQ)$', up):
        out.append(up.replace('.', '-'))
    return out


def file_name(sym):
    return re.sub(r'[^A-Za-z0-9.\-]', '_', sym) + '.json'


def fetch_one(code, name):
    last_err = None
    for sym in candidates(code):
        try:
            d1 = chart(sym, '1d', '5m')
        except NotFound:
            last_err = '종목을 찾지 못했어요'
            continue
        meta = d1.get('meta') or {}
        price = meta.get('regularMarketPrice')
        if price is None:
            last_err = '가격 정보가 없어요'
            continue
        prev = meta.get('chartPreviousClose') or meta.get('previousClose')
        y1 = chart(sym, '1y', '1d')
        time.sleep(0.4)
        y5 = chart(sym, '5y', '1wk')
        s1, sy1, sy5 = series(d1), series(y1), series(y5)
        period = (meta.get('currentTradingPeriod') or {}).get('regular') or {}
        item = {
            'code': code,
            'sym': sym,
            'name': name or meta.get('shortName') or meta.get('longName') or sym,
            'market': EXCHANGES.get(meta.get('exchangeName'), meta.get('fullExchangeName') or meta.get('exchangeName') or ''),
            'cur': meta.get('currency') or '',
            'tz': meta.get('exchangeTimezoneName') or 'UTC',
            'type': meta.get('instrumentType') or '',
            'price': price,
            'prev': prev,
            'time': meta.get('regularMarketTime'),
            'open': period.get('start'),
            'close': period.get('end'),
            'spark': sy1['c'][-30:],
            'hist': file_name(sym),
        }
        if prev:
            item['chg'] = round(price - prev, 4)
            item['pct'] = round((price - prev) / prev * 100, 3)
        hist = {'d1': s1, 'y1': sy1, 'y5': sy5, 'prev': prev, 'tz': item['tz']}
        return item, hist
    raise NotFound(last_err or '종목을 찾지 못했어요')


def main():
    OUT.mkdir(exist_ok=True)
    HIST.mkdir(exist_ok=True)
    try:
        old = json.loads((OUT / 'quotes.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        old = {}
    old_items = {it.get('code'): it for it in old.get('items', [])}

    entries = []
    for p in sorted(WATCH.iterdir()):
        if not p.is_file() or p.name.startswith('.'):
            continue
        text = p.read_text(encoding='utf-8', errors='replace').strip().splitlines()
        entries.append((p.name.strip(), (text[0].strip() if text else '')[:40]))

    items, errors, used = [], {}, set()
    for code, name in entries:
        try:
            item, hist = fetch_one(code, name)
            (HIST / item['hist']).write_text(json.dumps(hist, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
            items.append(item)
            used.add(item['hist'])
            print(f'ok   {code:8} {item["sym"]:10} {item["price"]}')
        except NotFound as e:
            errors[code] = str(e)
            print(f'miss {code:8} {e}')
        except Exception as e:  # network trouble: keep the previous data
            prev_item = old_items.get(code)
            if prev_item:
                prev_item['stale'] = True
                if name:
                    prev_item['name'] = name
                items.append(prev_item)
                used.add(prev_item.get('hist'))
            else:
                errors[code] = '시세를 받지 못했어요'
            print(f'fail {code:8} {e}', file=sys.stderr)
        time.sleep(0.4)

    fx = old.get('fx')
    try:
        res = chart('KRW=X', '1d', '5m')
        meta = res.get('meta') or {}
        if meta.get('regularMarketPrice'):
            fx = {'USDKRW': meta['regularMarketPrice'],
                  'prev': meta.get('chartPreviousClose') or meta.get('previousClose'),
                  'time': meta.get('regularMarketTime')}
    except Exception as e:
        print(f'fx   failed {e}', file=sys.stderr)

    for f in HIST.glob('*.json'):
        if f.name not in used:
            f.unlink()

    quotes = {'updated': int(time.time()), 'fx': fx, 'items': items, 'errors': errors}
    (OUT / 'quotes.json').write_text(json.dumps(quotes, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'{len(items)} items, {len(errors)} errors')
    fresh = [it for it in items if not it.get('stale')]
    if entries and not fresh and not errors:
        sys.exit('no data could be fetched')


if __name__ == '__main__':
    main()
