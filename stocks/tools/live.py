#!/usr/bin/env python3
"""장중 시세: refresh prices every 5 minutes while the Korean or the US market is open.

GitHub runs scheduled workflows only when it has capacity (often hours late, sometimes not
at all), so a cron every 10 minutes does not work. Instead one run of
.github/workflows/stocks-live.yml stays up for a whole trading session and publishes to
gh-pages itself. A job may run at most 6 hours, so before that it starts the next run
(workflow_dispatch with the job's own token, which GitHub allows) and stops.

Each round (5 minutes): take the newest main, run fetch.py (--quick: today's prices only;
a full fetch with 1-year/5-year history once an hour), then
- push quotes.json alone to the `live` branch — no site rebuild; the app reads it through
  the GitHub API, so prices are at most ~5 minutes old;
- every 10 minutes (or when main changed) publish main + the data folders to gh-pages.
  GitHub Pages allows about 10 site rebuilds an hour, which is why the site itself is not
  rebuilt every 5 minutes.
A change on main is picked up within a minute.

Between sessions on weekdays (Korean close → US open, US close → next Korean open) the run
stays up and waits, handing over every ~6 hours, so once started on a Monday it keeps
going until Saturday morning without relying on GitHub's late cron. Over the weekend it
ends; Monday is started by the cron backups or by the app (it wakes this workflow when
opened during market hours with old prices). Standard library only.
"""
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import urllib.request
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[2]
EVERY = 5 * 60                    # seconds between price refreshes (→ live branch)
SITE_EVERY = 10 * 60              # seconds between full site publishes (→ gh-pages)
FULL_EVERY = 60 * 60              # seconds between full fetches (1-year/5-year history, dividends)
POLL = 60                         # how often to look for a new commit on main
MAX_RUN = 5 * 3600 + 40 * 60      # hand over to a fresh run before GitHub's 6-hour limit
BRIDGE = 8 * 3600                 # keep waiting through gaps up to this long (weekday gaps are 3¾h and 6½h)
DATA_DIRS = ['stocks/data', 'english/data']   # git-ignored, produced by the fetch scripts
# (exchange time zone, open, last refresh) on weekdays. The end is a little after the close
# so the closing price arrives (Yahoo shows Korean prices about 20 minutes late).
SESSIONS = [
    ('국내', 'Asia/Seoul', dt.time(9, 0), dt.time(15, 55)),
    ('미국', 'America/New_York', dt.time(9, 30), dt.time(16, 15)),
]


def log(msg):
    print(time.strftime('%H:%M:%S'), msg, flush=True)


def git(*args, env=None, check=True):
    r = subprocess.run(['git', *args], cwd=ROOT, env=env, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f'git {args[0]}: {r.stderr.strip()}')
    return r.stdout.strip()


def session_now(now=None):
    """The open session's name, or None."""
    now = now or dt.datetime.now(dt.timezone.utc)
    for name, tz, start, end in SESSIONS:
        local = now.astimezone(ZoneInfo(tz))
        if local.weekday() < 5 and start <= local.time() < end:
            return name
    return None


def seconds_to_open(now=None):
    """Seconds until the next session opens (within the next day), or None."""
    now = now or dt.datetime.now(dt.timezone.utc)
    best = None
    for _, tz, start, _ in SESSIONS:
        local = now.astimezone(ZoneInfo(tz))
        for add in (0, 1):
            day = local.date() + dt.timedelta(days=add)
            if day.weekday() >= 5:
                continue
            at = dt.datetime.combine(day, start, ZoneInfo(tz))
            wait = (at - local).total_seconds()
            if wait > 0 and (best is None or wait < best):
                best = wait
    return best


def traded_recently(session, hours=3):
    """False on a market holiday: no stock of that market has traded in the last few hours."""
    try:
        q = json.loads((ROOT / 'stocks/data/quotes.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return True
    kr = session == '국내'
    times = [it.get('time') or 0 for it in q.get('items', []) if (it.get('cur') == 'KRW') == kr]
    return not times or time.time() - max(times) < hours * 3600


def main_head():
    out = git('ls-remote', 'origin', 'refs/heads/main', check=False)
    return out.split()[0] if out else None


def publish():
    """Commit the working tree (minus .github) + data folders as the whole gh-pages branch."""
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, GIT_INDEX_FILE=os.path.join(tmp, 'index'))
        git('read-tree', '--empty', env=env)
        git('add', '-A', '.', env=env)
        for d in DATA_DIRS:
            if (ROOT / d).exists():
                git('add', '-f', d, env=env)
        git('rm', '-r', '-q', '--cached', '--ignore-unmatch', '.github', env=env)
        tree = git('write-tree', env=env)
    commit = git('commit-tree', tree, '-m', '배포 ' + time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime()))
    git('push', '-q', '-f', 'origin', f'{commit}:refs/heads/gh-pages')


def publish_live():
    """quotes.json alone, as the whole `live` branch (one commit, replaced every time)."""
    blob = git('hash-object', '-w', 'stocks/data/quotes.json')
    r = subprocess.run(['git', 'mktree'], cwd=ROOT, input=f'100644 blob {blob}\tquotes.json\n',
                       capture_output=True, text=True, check=True)
    commit = git('commit-tree', r.stdout.strip(), '-m', '시세 ' + time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime()))
    git('push', '-q', '-f', 'origin', f'{commit}:refs/heads/live')


def one_round(head, full, site):
    """Newest main → fresh prices → live branch (+ site). Returns False if main moved meanwhile."""
    git('fetch', '-q', '--depth=1', 'origin', 'main')
    git('reset', '-q', '--hard', 'FETCH_HEAD')   # untracked data folders stay
    cmd = [sys.executable, 'stocks/tools/fetch.py'] + ([] if full else ['--quick'])
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    tail = (r.stdout.strip().splitlines() or [''])[-1]
    if r.returncode:
        log(f'시세 받기 실패, 배포 안 함: {r.stderr.strip()[-300:]}')
        return True
    publish_live()
    if not site:
        log(f'시세 올림{" (전체)" if full else ""} · {tail}')
        return True
    if main_head() != head:
        log('그 사이 main이 바뀌어서 다시 받음')
        return False
    publish()
    log(f'시세 + 사이트 배포{" (전체)" if full else ""} · {tail}')
    return True


def start_next_run():
    repo, token = os.environ.get('GITHUB_REPOSITORY'), os.environ.get('GITHUB_TOKEN')
    if not (repo and token):
        log('다음 실행을 시작할 수 없음 (토큰 없음)')
        return
    req = urllib.request.Request(
        f'https://api.github.com/repos/{repo}/actions/workflows/stocks-live.yml/dispatches',
        data=json.dumps({'ref': 'main'}).encode(), method='POST',
        headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            log(f'6시간 한도 전에 다음 실행으로 넘김 ({r.status})')
    except Exception as e:
        log(f'다음 실행 시작 실패: {e}')


def main():
    started = time.time()
    last_round, last_site, last_full, last_head, holiday = 0.0, 0.0, 0.0, None, set()
    waiting = False
    while True:
        session = session_now()
        if session in holiday:
            session = None
        wait = None if session else seconds_to_open()
        if time.time() - started > MAX_RUN:
            if session or (wait is not None and wait <= BRIDGE):
                start_next_run()
            else:
                log('다음 장이 멀어서 끝냄')
            return
        if not session:
            if wait is None or wait > BRIDGE:
                log('다음 장이 멀어서 끝냄 (주말)')
                return
            if not waiting:
                log(f'다음 장 시작까지 {int(wait // 60)}분 기다림')
                waiting = True
            time.sleep(min(wait + 5, 300))
            continue
        waiting = False
        head = main_head()
        if time.time() - last_round >= EVERY or head != last_head:
            began = time.time()   # rounds start every 5 minutes, however long a fetch takes
            full = began - last_full >= FULL_EVERY - 30
            site = head != last_head or began - last_site >= SITE_EVERY - 30
            try:
                ok = one_round(head, full, site)
            except Exception as e:  # one bad round must not end the session; try again next round
                log(f'이번 회차 실패: {e}')
                last_round, last_head = began, head
                time.sleep(POLL)
                continue
            if ok:
                last_round = began
                if full:
                    last_full = began
                if site:
                    last_site, last_head = began, head
                if not traded_recently(session) and time.time() - started > 45 * 60:
                    log(f'{session} 시장 휴장으로 보여서 이 시장은 그만 받음')
                    holiday.add(session)
                continue
        time.sleep(max(1, min(POLL, last_round + EVERY - time.time())))


if __name__ == '__main__':
    main()
