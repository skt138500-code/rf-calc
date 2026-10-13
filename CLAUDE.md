# rf-calc 저장소 — 수정 방법

사용자가 폰 홈 화면에 설치해 쓰는 오프라인 웹앱(PWA) 네 개가 들어 있다. 사용자는 한국어를 쓰는 RF 엔지니어이고, 화면 문구는 한국어로 쓴다.

| 앱 | 주소 | 원본 |
|---|---|---|
| RF 공학계산기 | https://skt138500-code.github.io/rf-calc/ | `src/calc.html` |
| 내 주식 | https://skt138500-code.github.io/rf-calc/stocks/ | `stocks/index.html` |
| 차량관리 | https://skt138500-code.github.io/rf-calc/car/ | `car/index.html` |
| 영어 입 트레이너 | https://skt138500-code.github.io/rf-calc/english/ | `english/index.html` |

## 배포
- **main에만 푸시한다.** `.github/workflows/stocks.yml`이 푸시마다(그리고 장 밖에서는 3시간마다) 시세와 영어 뉴스 제목을 받아 main + `stocks/data/` + `english/data/`를 `gh-pages`에 강제 푸시하고, GitHub Pages가 `gh-pages`를 서비스한다.
- 장중 시세 (5분): GitHub 예약 실행은 몇 시간씩 밀리거나 빠지므로 짧은 cron을 쓰지 않는다. `.github/workflows/stocks-live.yml`이 장 시작 때 한 번 떠서 `stocks/tools/live.py`가 장이 열린 동안(국내 09:00–15:55 KST, 미국 09:30–16:15 ET) 5분마다 main을 받고 `fetch.py --quick`(당일 시세만, 1년·5년 기록과 배당은 1시간마다 전체로)으로 시세를 받아 **`quotes.json`만 `live` 브랜치에** 올린다(사이트 재빌드 없음). 앱은 GitHub API(`/contents/quotes.json?ref=live`, 폰에 열쇠가 있으면 같이 보냄)와 사이트의 `data/quotes.json` 중 새것을 쓴다. 전체 사이트(gh-pages)는 10분마다 — GitHub Pages가 시간당 재빌드 약 10번까지라서. main이 바뀌면 1분 안에 다시 배포. 6시간 작업 한도 전에 스스로 다음 실행을 띄운다(workflow_dispatch). GitHub cron은 몇 시간씩 늦으니 실행이 평일 장 사이 공백(국내 마감→미국 개장, 미국 마감→국내 개장, 최대 8시간)을 기다리며 이어가서 월요일에 한 번 시작되면 토요일 아침까지 스스로 돈다. 주말 뒤 월요일 시작은 cron 예비 + 앱: 장중에 앱을 열었는데 시세가 15분 넘게 오래됐으면 앱이 폰의 GitHub 열쇠로 이 workflow를 실행한다(열쇠에 Actions: Read and write 필요, 10분에 한 번까지). 휴장일(시세가 3시간 넘게 그대로)은 45분 뒤 스스로 끝낸다. 배포할 때 git으로 관리하지 않는 데이터 폴더(`stocks/data`, `english/data`)를 같이 올린다(영어 뉴스는 사이트 배포 직전에 `english/tools/news.py`를 돌려 새로 받는다 — 안 그러면 장중에 이 작업이 처음 불러온 옛 목록으로 계속 덮어쓴다) — 새 앱이 데이터 폴더를 쓰면 `live.py`의 `DATA_DIRS`와 두 workflow의 '지난 시세 불러오기'에 추가할 것.
- `gh-pages`에 직접 푸시하지 않는다(다음 실행 때 덮어써진다).

## 계산기 고칠 때
1. `src/calc.html` 수정 (루트 `index.html`은 빌드 결과물)
2. `python3 tools/build.py` → index.html, sw.js(캐시 버전), manifest 재생성
3. 커밋 → `git push origin main`

## 주식 앱 고칠 때
1. `stocks/index.html` 수정 → `python3 stocks/tools/build.py` (sw.js 캐시 버전, manifest, 아이콘)
2. 커밋 → `git push origin main`
- 관심종목: `stocks/watch/` 안의 파일 하나가 한 종목. 파일 이름 = 종목코드(국내 6자리, 미국 티커), 첫 줄 = 앱에 보일 이름.
- 앱의 "종목 추가"·"목록에서 삭제": 폰에 GitHub 토큰(fine-grained, rf-calc 저장소 Contents 쓰기 + 장중 시세 깨우기용 Actions 쓰기)이 저장돼 있으면 GitHub Contents API로 바로 커밋한다. 토큰이 없으면 GitHub 새 파일/삭제 링크를 미리 채워서 연다. 토큰은 폰 localStorage(`stocks.gh`)에만 있다.
- 화면: 종목 / 배당 / 섹터 탭. 종목 목록 한 줄 = 로고 · 이름(보유 수량·코드) · 당일 그래프 · 가격+등락(손익). 국내 숫자는 '원' 없이 쓰고 그룹 제목에 단위를 적는다(공간 확보). 목록 행은 subgrid로 열을 맞춘다. 배당은 `quotes.json` 각 종목의 `div`(최근 3년 [배당락일, 1주 금액])로 계산한다. 배당 탭은 올해 1~12월 기준: 지난 배당락 = 받은 금액(실제 기록), 남은 달 = 작년 같은 때 배당이 다시 나온다고 가정한 예상. 지금 보유 수량을 1월부터 가졌다고 본다. 세후/세전 선택(세후 = 미국 15%, 국내 15.4% 원천징수만 뺌).
- 시장 탭: 지수·환율 카드(`quotes.json`의 `indices`), 뉴스 제목·링크(`data/news.json`, `stocks/tools/market.py`가 1시간마다 Google 뉴스/Yahoo RSS에서 모음 — 기사 본문은 저장하지 않음), AI 브리핑(`stocks/analysis/latest.json`). 브리핑은 평일 아침 Claude 예약 작업이 써서 main에 푸시한다. 형식: `{date:"YYYY-MM-DD", made, title, market:[문단], stocks:[{code, tone:"up|down|neutral", text}], watch:[{date:"MM-DD", text}], sources:[{title, url}]}`, 지난 것은 `stocks/analysis/YYYY-MM-DD.json`으로 14일 보관.
- 섹터·유형 분류: 유형은 성장·모멘텀 / 경기민감주 / 가치·우량주 / 배당주 / 기타. 기본값은 `stocks/index.html`의 `CLS` 표, 사용자가 바꾼 값은 폰 localStorage(`stocks.cls`)에만 저장.
- 백업·복원: 폰에만 있는 값(보유, 분류, 설정, 선택하면 GitHub 토큰)을 `MYSTOCK1.` + base64(JSON) 코드로 복사·붙여넣기. iOS는 홈 화면 앱을 지우면 이 값들이 지워질 수 있다.
- 아이콘: `stocks/tools/build.py`의 `icon()`이 그린다. 아이콘 파일이 없을 때만 새로 만드니, 바꿀 땐 PNG들을 지우고 빌드한다.
- 시세 수집: `stocks/tools/fetch.py` (표준 라이브러리만, Yahoo Finance v8 chart API, 5년 차트 요청에 `events=div`로 배당 내역도 받음). 목록의 작은 그래프는 당일 5분봉을 60점으로 줄인 `spark1d`(색은 전일 대비 방향). 로고는 `stocks/data/logos/`에 종목당 한 번만 받는다(국내: Toss → alphasquare, 미국: FMP → Parqet → alphasquare). 못 찾은 종목은 `_missing.json`에 적고 7일 뒤 다시 시도, 앱은 로고가 없으면 첫 글자 원을 보여준다. 국내 코드는 .KS → .KQ 순서로 찾는다. 실패한 종목은 gh-pages에 있던 이전 데이터를 유지한다.
- 보유 수량·평단가·분류·GitHub 토큰은 폰 localStorage에만 저장된다. 저장소(공개)에 올리지 않는다.
- 네 앱의 service worker는 자기 접두어(`rfcalc-`, `stocks-`, `car-`, `english-`) 캐시만 지운다. 루트(계산기) service worker는 `/stocks/`·`/car/`·`/english/` 요청을 건드리지 않는다(`tools/build.py`). 주식·차량 앱 service worker는 다른 출처(GitHub API 등) 요청을 건드리지 않는다. 페이지(index.html)는 네트워크 우선이라 업데이트가 첫 실행에 바로 보이고, 오프라인이거나 3초 넘게 걸리면 저장본을 쓴다.

## 차량관리 앱 고칠 때
1. `car/index.html` 수정 → `python3 car/tools/build.py` (sw.js 캐시 버전, manifest, 아이콘)
2. 커밋 → `git push origin main`
- 사용자의 차 두 대(SM6, 올란도)를 관리한다. (예전 기록·백업에 SM7로 잘못 들어간 차 이름은 앱이 열릴 때·복원할 때 `fixModel()`이 SM6으로 고친다.) 차량 정보·정비 기록은 폰 localStorage(`car.cars`, `car.logs`)에만 있다. 저장소(공개)에 기록·번호판을 올리지 않는다.
- 기록 한 건: `{car, date:"YYYY-MM-DD", cat, title, km, cost, nextKm, nextDate, memo, todo, done, doneDate?, ts}`. `cat`은 oil / atf / brake / tire / battery / inspect / parts / repair / etc / odo(주행거리만 적은 기록). `todo:true`는 할 일(`nextDate` = 기한).
- 화면: 현황 / 이력 / 비용 / 차량 탭. 현황 = 계기판식 주행거리(마지막 기록 이후는 최근 2년 하루 평균으로 추정, "추정" 표시) + 챙길 정비(지남·곧) + 할 일 + 관리 항목. 항목마다 가장 최근 기록의 다음 교체 km·날짜로 상태를 매기고, 다음 교체가 비어 있으면 차량 탭의 교체 주기(기본: 엔진오일 7,000km, 미션·브레이크오일 50,000km, 타이어 20,000km, 배터리·정기검사 24개월)로 계산한다. "곧" = 1,500km 또는 45일 이내. 정기검사는 다음 검사일 앞 90일 ~ 뒤 31일이 받을 수 있는 기간(사용자 검사서 문구)이라 그 기간에 들어서면 "곧", 끝나면 "지남".
- 백업·복원: `MYCAR1.` + base64(JSON `{v, at, cars, logs}`). Claude 아티팩트 "두 대 차계부"의 `CARLOG1.` 코드도 같은 모양이라 그대로 불러온다.
- 아이콘: `car/tools/build.py`의 `icon()`이 그린다(계기판 게이지). 파일이 없을 때만 새로 만든다.

## 영어 입 트레이너 고칠 때
1. `english/index.html` 수정 → `python3 english/tools/build.py` (sw.js 캐시 버전, manifest, 아이콘)
2. 커밋 → `git push origin main`
- 학회 발표·질의응답 영어 연습 + 국제 뉴스 듣기. 탭: 오늘(연속 학습일·14일 기록·할 일 3개·날마다 바뀌는 표현 5개) / 표현(묶음별 44문장, RAON RF 표현 포함) / 듣기(유튜브 영상 + 스크립트, 붙여넣은 글 → 문장별 해석) / 질문(청중 질문 듣고 답하기, 코칭) / 저장.
- 문장 카드: 듣기(speechSynthesis), 천천히(0.7배), 말해보기(Web Speech 음성 인식 en-US → 원문과 단어 맞춤 채점, 70% 이상이면 1회 기록), +1회(오늘의 표현 3회씩 → 할 일 자동 완료), 별(저장).
- AI는 두 방식. ① 설정에 Claude API 키(폰 localStorage `english.key`에만, 백업 코드에도 안 넣음)가 있으면 브라우저에서 `api.anthropic.com/v1/messages`를 바로 부른다(`anthropic-dangerous-direct-browser-access` 헤더). 해석·코칭은 `claude-sonnet-5-5`(설정에서 `claude-haiku-5-5`로 바꿀 수 있음), 질문 만들기는 항상 Haiku. 응답은 JSON으로 받는다. ② 키가 없으면 버튼이 사용자의 Claude 아티팩트 "영어 입 트레이너"(https://claude.ai/artifact/4LbZ53zfg5xzeJvdYBSvoz, `#listen`·`#qa`)를 열어 Pro 요금제로 쓰게 한다. 코칭은 요청문을 복사하고 claude.ai/new를 연다.
- 아티팩트의 "홈 화면 앱으로 보내기" 코드: `ENGLIST1.` + base64(UTF-8 JSON `{v, items:[{title, ts, sentences:[{en, ko, keys, t?}], vocab, video?, timed?}], saved:[{en, ko, src}]}`). 듣기 탭 "Claude에서 만든 자료 가져오기"가 읽는다.
- 기록: 폰 localStorage(`english.state` = `{days:{YYYY-MM-DD:{p,n,q,reps}}, saved, library, settings}`). 백업·복원 코드는 `MYENG1.` + base64(JSON).
- 듣기 탭 "오늘의 영어 뉴스": `english/tools/news.py`(표준 라이브러리)가 배포 작업 때 최대 1시간에 한 번 RSS에서 **제목·링크만** 모아 `english/data/news.json`(`{made, sources:[{id,name,group,ok,n}], items:[{src,t,url,ts,lv?}], channels, videos, chan}`)을 쓴다. 기사 본문은 저장하지 않는다(사용자가 사이트에서 직접 복사). 묶음: easy = News in Levels(레벨 1~3을 한 줄로 묶어 `lv`), Breaking News English / world = BBC World, NPR World, The Guardian / science = Physics World. 실패한 소스는 이전 제목을 유지한다. `english/data`는 main에 커밋하지 않고(.gitignore) 워크플로가 gh-pages에서 불러와 `git add -f`로 배포한다. 앱은 `data/news.json`을 네트워크로 받고 마지막 목록을 localStorage(`english.feed`)에 둔다.
- **영상으로 듣기** (듣기 탭 맨 위, 시트 `sh-vid`): 유튜브 링크(youtu.be, watch?v=, shorts, live) 또는 "오늘의 뉴스 영상" 목록 → YouTube IFrame API 플레이어(위에 고정) + 아래 문장 목록(영어·해석). 재생 중인 문장 강조·자동 스크롤, 문장 누르면 그 위치로, 문장 반복, 한 문장씩 멈추기, 속도 1/0.75/0.5, 영상 자막(CC) 켜기·끄기. 채널이 외부 재생을 막은 영상(오류 101/150/153)은 유튜브로 여는 링크를 보여 주고 스크립트 공부는 계속된다.
- **유튜브는 GitHub 서버(Actions)의 자막 요청을 막는다**(2026-10 시험: youtube-transcript-api `RequestBlocked`, yt-dlp "Sign in to confirm you're not a bot"). 그래서 스크립트는 위의 Supadata API로 받거나, 사용자가 직접 넣는다: "자막 사이트 열기"가 영상 링크를 복사하고 supadata.ai/youtube-transcript(예비: vidIQ)를 연다 → 시간 표시 켜고 Copy → 앱에 붙여넣기. `parseScript()`가 "0:03" 줄, "[00:03] 글", SRT/VTT, "1 minute, 5 seconds"(유튜브 모바일) 형식을 읽고, 시간 표시가 있으면 조각을 문장으로 묶어(`mergeTimed`) 문장마다 시작 시간 `t`를 둔다. 시간 표시가 없는 원고(방송사 홈페이지 원고 등)는 글자 수 비율로 영상 길이에 나누고, "자막 맞추기"로 누른 문장=지금 시간 기준점(`anchors:[[문장 번호, 초]]`)을 잡아 구간별 선형으로 맞춘다(`sentenceTimes`).
- **자막 자동 받기 (기본 경로)**: 설정의 Supadata 무료 키(폰 localStorage `english.sdkey`에만, 백업 코드에 안 넣음, 무료 월 100 크레딧·카드 없음)가 있으면 영상을 열 때 앱이 폰에서 바로 `GET https://api.supadata.ai/v1/transcript?url=<유튜브 주소>&lang=en&mode=native`(헤더 `x-api-key`)를 부른다 — Supadata는 브라우저 호출(CORS `*`, `x-api-key` 허용)을 받는다(2026-10 확인). 응답 `content:[{text, offset(ms), duration, lang}]` → `mergeTimed`로 문장 + 시간. 202면 `jobId`를 1.5초마다 `/v1/transcript/{jobId}`로 확인. 206 = 자막 없음 → "AI 받아쓰기"(`mode=generate`, 영상 1분에 2크레딧) 버튼. 기존 자막은 1크레딧이고, 받은 스크립트는 저장돼서 같은 영상을 다시 열면 요청하지 않는다. 키가 없으면 영상 화면이 "자막 키 넣기"로 설정의 해당 칸을 연다. 직접 붙여넣기(아래)는 접힌 "직접 붙여넣기"로 남겨 둔다.
- **구간**: 자막 조각(Supadata `content`는 영상에 따라 캡션 한 줄이기도, 수십 초짜리 한 덩어리이기도 하다)은 먼저 `expandUnits`가 문장으로 쪼개 조각의 offset~offset+duration 안에 글자 수 비율로 시간을 나눈 뒤 묶는다. 스크립트는 문장이 아니라 약 30초 구간(1분에 2개)으로 묶는다(`groupTimed`: 24~25초 넘은 뒤 첫 문장 끝에서 자르고, 문장부호가 없으면 36초에서 자름, 10초 안 되는 꼬리는 앞 구간에 붙임 / 시간 없는 원고는 `groupWords` 약 60단어). 예전에 문장 단위로 저장됐거나(평균 15초 미만) 한 덩어리로 들어온(구간이 40초 넘음, 마지막 구간은 단어 수×0.4초로 어림) 영상은 열 때 `regroupIfNeeded`가 다시 묶는다. 해석 프롬프트(앱·아티팩트 모두)는 구간 하나에 결과 하나(`i` = 구간 번호)이고, 결과 안에 `lines:[{en, ko}]`로 문장마다 해석을 받는다. 화면은 구간 카드 안에서 영어 문장 바로 아래에 그 문장의 해석을 보여 준다(구간의 `en`/`ko`는 lines를 이어 붙인 것, 보내기 코드에도 `lines`가 들어간다). 화면 문구도 '구간'(구간마다 멈추기, 이전/다음 구간).
- **Claude 해석 가져오기**: "Claude로 해석"을 누르면 `english.pending = {id, title, ts}`를 적어 두고, 해석이 안 끝난 동안 모든 탭 아래쪽에 고정 배너(`#pend`)와 영상 화면 아래 고정 막대(`#vid-pend`)에 "해석 가져오기" 버튼을 띄운다. 누르면 클립보드를 읽어(iOS는 '붙여넣기' 한 번 더) `ENGLIST1.` 코드면 가져와 그 영상 화면을 연다. 클립보드를 못 읽으면 듣기 탭의 가져오기 칸을 열어 준다. Claude 앱과 홈 화면 앱(iOS에서는 저장소도 따로)이 함께 쓰는 통로가 클립보드뿐이라 이 방식이다.
- 영상 자료는 `library` 항목에 `video:{id,title,ch}`, `timed`, `anchors`, 문장마다 `t`를 더해 저장(영상 하나에 항목 하나, id `v<영상ID>`). 해석: API 키가 있으면 문장 번호를 붙여 3,500자씩 보내고(`videoPrompt`) 응답의 `i`(시작 줄 번호)로 시간을 이어받는다. 키가 없으면 "Claude로 해석"이 `VIDEO: <url> | <제목> | <채널>` 다음 줄부터 `[m:ss] 문장`을 복사해 아티팩트를 연다 → 아티팩트는 이 모양의 글이 붙여넣어지면 바로 해석을 시작하고(paste 이벤트) 같은 방식으로 시간을 지켜 해석하고, 보내기 코드(`ENGLIST1.`)의 항목에 `video`, `timed`, 문장 `t`가 들어간다 → 영상 화면 "코드 붙여넣기"나 듣기 탭 가져오기로 들어오면 그 영상 화면이 열린다.
- "오늘의 뉴스 영상": `news.py`가 유튜브 채널 업로드 RSS(서버에서도 받아짐)에서 영상 ID·제목·날짜만 모은다(`videos:[{v,t,ts,ch}]`, `channels:[{id,name,ok,n}]`, 핸들→채널 ID는 `chan`에 기억). 채널: Arirang News(@arirangcokrarirangnews), CNN, BBC News, DW News, BBC Learning English. Shorts와 생방송([LIVE] 등)은 뺀다(CNN 10 채널 피드는 404라 뺐다). 7일 안, 채널마다 10개.
- 아이콘: `english/tools/build.py`의 `icon()`(말풍선 안 음성 파형). 파일이 없을 때만 새로 만든다.
