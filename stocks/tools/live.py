#!/usr/bin/env python3
"""장중 시세: refresh prices every 10 minutes while the Korean or the US market is open.

GitHub runs scheduled workflows only when it has capacity (often hours late, sometimes not
at all), so a cron every 10 minutes does not work. Instead one run of
.github/workflows/stocks-live.yml stays up for a whole trading session and publishes to
gh-pages itself. A job may run at most 6 hours, so before that it starts the next run
(workflow_dispatch with the job's own token, which GitHub allows) and stops.

Each round: take the newest main (new stocks, app changes), run fetch.py, publish main +
the data folders to gh-pages. A change on main is picked up within a minute.
Standard library only.
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
EVERY = 10 * 60                   # seconds between price refreshes
POLL = 60                         # how often to look for a new commit on main
MAX_RUN = 5 * 3600 + 40 * 60      # hand over to a fresh run before GitHub's 6-hour limit
WAIT_FOR_OPEN = 25 * 60           # started a little early: wait at most this long for the open
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


def one_round(head):
    """Newest main → fresh prices → publish. Returns False if main moved meanwhile."""
    git('fetch', '-q', '--depth=1', 'origin', 'main')
    git('reset', '-q', '--hard', 'FETCH_HEAD')   # untracked data folders stay
    r = subprocess.run([sys.executable, 'stocks/tools/fetch.py'], cwd=ROOT, capture_output=True, text=True)
    tail = (r.stdout.strip().splitlines() or [''])[-1]
    if r.returncode:
        log(f'시세 받기 실패, 배포 안 함: {r.stderr.strip()[-300:]}')
        return True
    if main_head() != head:
        log('그 사이 main이 바뀌어서 다시 받음')
        return False
    publish()
    log(f'배포 완료 · {tail}')
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
    last_round, last_head, holiday = 0.0, None, set()
    while True:
        session = session_now()
        if session in holiday:
            session = None
        if not session:
            wait = seconds_to_open()
            if last_round or wait is None or wait > WAIT_FOR_OPEN:
                log('장이 닫혀서 끝냄')
                return
            log(f'장 시작까지 {int(wait // 60)}분 기다림')
            time.sleep(min(wait + 5, POLL))
            continue
        if time.time() - started > MAX_RUN:
            start_next_run()
            return
        head = main_head()
        if time.time() - last_round >= EVERY or head != last_head:
            try:
                ok = one_round(head)
            except Exception as e:  # one bad round must not end the session
                log(f'이번 회차 실패: {e}')
                ok = True
            if ok:
                last_round, last_head = time.time(), head
                if not traded_recently(session) and time.time() - started > 45 * 60:
                    log(f'{session} 시장 휴장으로 보여서 이 시장은 그만 받음')
                    holiday.add(session)
                continue
        time.sleep(POLL)


if __name__ == '__main__':
    main()
