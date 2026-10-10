# rf-calc 저장소 — 수정 방법

사용자가 폰 홈 화면에 설치해 쓰는 오프라인 웹앱(PWA) 세 개가 들어 있다. 사용자는 한국어를 쓰는 RF 엔지니어이고, 화면 문구는 한국어로 쓴다.

| 앱 | 주소 | 원본 |
|---|---|---|
| RF 공학계산기 | https://skt138500-code.github.io/rf-calc/ | `src/calc.html` |
| 내 주식 | https://skt138500-code.github.io/rf-calc/stocks/ | `stocks/index.html` |
| 차량관리 | https://skt138500-code.github.io/rf-calc/car/ | `car/index.html` |

## 배포
- **main에만 푸시한다.** `.github/workflows/stocks.yml`이 푸시마다(그리고 장 시간 15분마다) 시세를 받아 main + `stocks/data/`를 `gh-pages`에 강제 푸시하고, GitHub Pages가 `gh-pages`를 서비스한다.
- `gh-pages`에 직접 푸시하지 않는다(다음 실행 때 덮어써진다).

## 계산기 고칠 때
1. `src/calc.html` 수정 (루트 `index.html`은 빌드 결과물)
2. `python3 tools/build.py` → index.html, sw.js(캐시 버전), manifest 재생성
3. 커밋 → `git push origin main`

## 주식 앱 고칠 때
1. `stocks/index.html` 수정 → `python3 stocks/tools/build.py` (sw.js 캐시 버전, manifest, 아이콘)
2. 커밋 → `git push origin main`
- 관심종목: `stocks/watch/` 안의 파일 하나가 한 종목. 파일 이름 = 종목코드(국내 6자리, 미국 티커), 첫 줄 = 앱에 보일 이름.
- 앱의 "종목 추가"·"목록에서 삭제": 폰에 GitHub 토큰(fine-grained, rf-calc 저장소 Contents 쓰기)이 저장돼 있으면 GitHub Contents API로 바로 커밋한다. 토큰이 없으면 GitHub 새 파일/삭제 링크를 미리 채워서 연다. 토큰은 폰 localStorage(`stocks.gh`)에만 있다.
- 화면: 종목 / 배당 / 섹터 탭. 종목 목록 한 줄 = 로고 · 이름(보유 수량·코드) · 당일 그래프 · 가격+등락(손익). 국내 숫자는 '원' 없이 쓰고 그룹 제목에 단위를 적는다(공간 확보). 목록 행은 subgrid로 열을 맞춘다. 배당은 `quotes.json` 각 종목의 `div`(최근 3년 [배당락일, 1주 금액])로 계산한다. 배당 탭은 올해 1~12월 기준: 지난 배당락 = 받은 금액(실제 기록), 남은 달 = 작년 같은 때 배당이 다시 나온다고 가정한 예상. 지금 보유 수량을 1월부터 가졌다고 본다. 세후/세전 선택(세후 = 미국 15%, 국내 15.4% 원천징수만 뺌).
- 시장 탭: 지수·환율 카드(`quotes.json`의 `indices`), 뉴스 제목·링크(`data/news.json`, `stocks/tools/market.py`가 1시간마다 Google 뉴스/Yahoo RSS에서 모음 — 기사 본문은 저장하지 않음), AI 브리핑(`stocks/analysis/latest.json`). 브리핑은 평일 아침 Claude 예약 작업이 써서 main에 푸시한다. 형식: `{date:"YYYY-MM-DD", made, title, market:[문단], stocks:[{code, tone:"up|down|neutral", text}], watch:[{date:"MM-DD", text}], sources:[{title, url}]}`, 지난 것은 `stocks/analysis/YYYY-MM-DD.json`으로 14일 보관.
- 섹터·유형 분류: 유형은 성장·모멘텀 / 경기민감주 / 가치·우량주 / 배당주 / 기타. 기본값은 `stocks/index.html`의 `CLS` 표, 사용자가 바꾼 값은 폰 localStorage(`stocks.cls`)에만 저장.
- 백업·복원: 폰에만 있는 값(보유, 분류, 설정, 선택하면 GitHub 토큰)을 `MYSTOCK1.` + base64(JSON) 코드로 복사·붙여넣기. iOS는 홈 화면 앱을 지우면 이 값들이 지워질 수 있다.
- 아이콘: `stocks/tools/build.py`의 `icon()`이 그린다. 아이콘 파일이 없을 때만 새로 만드니, 바꿀 땐 PNG들을 지우고 빌드한다.
- 시세 수집: `stocks/tools/fetch.py` (표준 라이브러리만, Yahoo Finance v8 chart API, 5년 차트 요청에 `events=div`로 배당 내역도 받음). 목록의 작은 그래프는 당일 5분봉을 60점으로 줄인 `spark1d`(색은 전일 대비 방향). 로고는 `stocks/data/logos/`에 종목당 한 번만 받는다(국내: Toss → alphasquare, 미국: FMP → Parqet → alphasquare). 못 찾은 종목은 `_missing.json`에 적고 7일 뒤 다시 시도, 앱은 로고가 없으면 첫 글자 원을 보여준다. 국내 코드는 .KS → .KQ 순서로 찾는다. 실패한 종목은 gh-pages에 있던 이전 데이터를 유지한다.
- 보유 수량·평단가·분류·GitHub 토큰은 폰 localStorage에만 저장된다. 저장소(공개)에 올리지 않는다.
- 세 앱의 service worker는 자기 접두어(`rfcalc-`, `stocks-`, `car-`) 캐시만 지운다. 루트(계산기) service worker는 `/stocks/`·`/car/` 요청을 건드리지 않는다(`tools/build.py`). 주식·차량 앱 service worker는 다른 출처(GitHub API 등) 요청을 건드리지 않는다. 페이지(index.html)는 네트워크 우선이라 업데이트가 첫 실행에 바로 보이고, 오프라인이거나 3초 넘게 걸리면 저장본을 쓴다.

## 차량관리 앱 고칠 때
1. `car/index.html` 수정 → `python3 car/tools/build.py` (sw.js 캐시 버전, manifest, 아이콘)
2. 커밋 → `git push origin main`
- 사용자의 차 두 대(SM7, 올란도)를 관리한다. 차량 정보·정비 기록은 폰 localStorage(`car.cars`, `car.logs`)에만 있다. 저장소(공개)에 기록·번호판을 올리지 않는다.
- 기록 한 건: `{car, date:"YYYY-MM-DD", cat, title, km, cost, nextKm, nextDate, memo, todo, done, doneDate?, ts}`. `cat`은 oil / atf / brake / tire / battery / inspect / parts / repair / etc / odo(주행거리만 적은 기록). `todo:true`는 할 일(`nextDate` = 기한).
- 화면: 현황 / 이력 / 비용 / 차량 탭. 현황 = 계기판식 주행거리(마지막 기록 이후는 최근 2년 하루 평균으로 추정, "추정" 표시) + 챙길 정비(지남·곧) + 할 일 + 관리 항목. 항목마다 가장 최근 기록의 다음 교체 km·날짜로 상태를 매기고, 다음 교체가 비어 있으면 차량 탭의 교체 주기(기본: 엔진오일 7,000km, 미션·브레이크오일 50,000km, 타이어 20,000km, 배터리·정기검사 24개월)로 계산한다. "곧" = 1,500km 또는 45일 이내. 정기검사는 다음 검사일 앞 90일 ~ 뒤 31일이 받을 수 있는 기간(사용자 검사서 문구)이라 그 기간에 들어서면 "곧", 끝나면 "지남".
- 백업·복원: `MYCAR1.` + base64(JSON `{v, at, cars, logs}`). Claude 아티팩트 "두 대 차계부"의 `CARLOG1.` 코드도 같은 모양이라 그대로 불러온다.
- 아이콘: `car/tools/build.py`의 `icon()`이 그린다(계기판 게이지). 파일이 없을 때만 새로 만든다.
