# rf-calc 저장소 — 수정 방법

사용자가 폰 홈 화면에 설치해 쓰는 오프라인 웹앱(PWA) 두 개가 들어 있다. 사용자는 한국어를 쓰는 RF 엔지니어이고, 화면 문구는 한국어로 쓴다.

| 앱 | 주소 | 원본 |
|---|---|---|
| RF 공학계산기 | https://skt138500-code.github.io/rf-calc/ | `src/calc.html` |
| 내 주식 | https://skt138500-code.github.io/rf-calc/stocks/ | `stocks/index.html` |

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
- 섹터·유형 분류: 유형은 성장·모멘텀 / 경기민감주 / 가치·우량주 / 배당주 / 기타. 기본값은 `stocks/index.html`의 `CLS` 표, 사용자가 바꾼 값은 폰 localStorage(`stocks.cls`)에만 저장.
- 백업·복원: 폰에만 있는 값(보유, 분류, 설정, 선택하면 GitHub 토큰)을 `MYSTOCK1.` + base64(JSON) 코드로 복사·붙여넣기. iOS는 홈 화면 앱을 지우면 이 값들이 지워질 수 있다.
- 아이콘: `stocks/tools/build.py`의 `icon()`이 그린다. 아이콘 파일이 없을 때만 새로 만드니, 바꿀 땐 PNG들을 지우고 빌드한다.
- 시세 수집: `stocks/tools/fetch.py` (표준 라이브러리만, Yahoo Finance v8 chart API, 5년 차트 요청에 `events=div`로 배당 내역도 받음). 목록의 작은 그래프는 당일 5분봉을 60점으로 줄인 `spark1d`(색은 전일 대비 방향). 로고는 `stocks/data/logos/`에 종목당 한 번만 받는다(국내: Toss → alphasquare, 미국: FMP → Parqet → alphasquare). 못 찾은 종목은 `_missing.json`에 적고 7일 뒤 다시 시도, 앱은 로고가 없으면 첫 글자 원을 보여준다. 국내 코드는 .KS → .KQ 순서로 찾는다. 실패한 종목은 gh-pages에 있던 이전 데이터를 유지한다.
- 보유 수량·평단가·분류·GitHub 토큰은 폰 localStorage에만 저장된다. 저장소(공개)에 올리지 않는다.
- 두 앱의 service worker는 자기 접두어(`rfcalc-`, `stocks-`) 캐시만 지운다. 주식 앱 service worker는 다른 출처(GitHub API 등) 요청을 건드리지 않는다. 페이지(index.html)는 네트워크 우선이라 업데이트가 첫 실행에 바로 보이고, 오프라인이거나 3초 넘게 걸리면 저장본을 쓴다.
