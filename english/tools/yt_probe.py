import json, re, sys, urllib.request, xml.etree.ElementTree as ET
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.8'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8', 'replace')
handles = ['@arirangnews', '@CNN', '@cnn10', '@VOALearningEnglish', '@bbcnews', '@DWNews', '@KBSNews', '@ABCNews', '@bbclearningenglish']
vids = []
for hnd in handles:
    try:
        page = get('https://www.youtube.com/' + hnd)
        m = re.search(r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[\w-]{22})"', page) or re.search(r'"externalId":"(UC[\w-]{22})"', page)
        cid = m.group(1) if m else None
        print(f'{hnd:22} channel {cid}')
        if not cid: continue
        root = ET.fromstring(get('https://www.youtube.com/feeds/videos.xml?channel_id=' + cid))
        ns = {'a': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
        es = root.findall('a:entry', ns)
        print(f'   feed {len(es)} entries')
        for e in es[:3]:
            vid = e.findtext('yt:videoId', namespaces=ns); t = e.findtext('a:title', namespaces=ns); d = e.findtext('a:published', namespaces=ns)
            print(f'   {vid} {d[:10]} {t[:70]}')
        for e in es[:2]:
            vids.append((hnd, e.findtext('yt:videoId', namespaces=ns)))
    except Exception as ex:
        print(f'{hnd:22} FAILED {type(ex).__name__}: {str(ex)[:120]}')

import youtube_transcript_api as yta
print('youtube-transcript-api', getattr(yta, '__version__', '?'))
from youtube_transcript_api import YouTubeTranscriptApi
api = YouTubeTranscriptApi()
ok = 0
for hnd, vid in vids:
    try:
        tl = api.list(vid)
        langs = [(t.language_code, 'auto' if t.is_generated else 'manual', t.is_translatable) for t in tl]
        en = None
        try: en = tl.find_manually_created_transcript(['en', 'en-US', 'en-GB'])
        except Exception: en = tl.find_transcript(['en', 'en-US', 'en-GB'])
        f = en.fetch()
        snips = list(f)
        words = sum(len(s.text.split()) for s in snips)
        punct = sum(1 for s in snips if re.search(r'[.?!]$', s.text.strip()))
        ko = None
        if en.is_translatable:
            try: ko = len(list(en.translate('ko').fetch()))
            except Exception as ex: ko = f'fail {type(ex).__name__}'
        print(f'CAPTIONS {hnd:20} {vid} langs={langs[:4]} picked={en.language_code}/{"auto" if en.is_generated else "manual"} segs={len(snips)} words={words} punct_end={punct} ko={ko}')
        ok += 1
    except Exception as ex:
        print(f'CAPTIONS {hnd:20} {vid} FAILED {type(ex).__name__}: {str(ex).splitlines()[0][:160] if str(ex) else ""}')
print('caption successes', ok, 'of', len(vids))

import subprocess
if vids:
    vid = vids[0][1]
    r = subprocess.run(['yt-dlp', '--skip-download', '--write-auto-subs', '--write-subs', '--sub-langs', 'en.*', '--sub-format', 'json3', '-o', '/tmp/p.%(ext)s', 'https://www.youtube.com/watch?v=' + vid], capture_output=True, text=True, timeout=120)
    print('yt-dlp rc', r.returncode)
    for line in (r.stdout + r.stderr).splitlines()[-8:]:
        print('   ', line[:200])
