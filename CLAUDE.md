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
- 화면: 종목 / 배당 / 섹터 탭. 배당은 `quotes.json` 각 종목의 `div`(최근 3년 [배당락일, 1주 금액])로 계산하고, 앞으로 1년은 "지난 1년이 반복된다"고 가정한다(세후 = 미국 15%, 국내 15.4% 원천징수만 뺌).
- 섹터·성격 분류: 기본값은 `stocks/index.html`의 `CLS` 표, 사용자가 바꾼 값은 폰 localStorage(`stocks.cls`)에만 저장.
- 시세 수집: `stocks/tools/fetch.py` (표준 라이브러리만, Yahoo Finance v8 chart API, 5년 차트 요청에 `events=div`로 배당 내역도 받음). 국내 코드는 .KS → .KQ 순서로 찾는다. 실패한 종목은 gh-pages에 있던 이전 데이터를 유지한다.
- 보유 수량·평단가·분류·GitHub 토큰은 폰 localStorage에만 저장된다. 저장소(공개)에 올리지 않는다.
- 두 앱의 service worker는 자기 접두어(`rfcalc-`, `stocks-`) 캐시만 지운다. 주식 앱 service worker는 다른 출처(GitHub API 등) 요청을 건드리지 않는다.
