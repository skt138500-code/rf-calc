# RF 공학계산기 — 수정 방법

사용자가 폰에 설치해 쓰는 오프라인 웹앱(PWA)이다. GitHub Pages가 **gh-pages 브랜치**를 서비스한다.

## 고칠 때 순서
1. 원본은 `src/calc.html` 하나다. 루트의 `index.html`은 빌드 결과물이니 직접 고치지 않는다.
2. `src/calc.html` 수정 → `python3 tools/build.py` 실행
   (index.html, sw.js 캐시 버전, manifest가 다시 만들어진다. sw.js 버전이 바뀌어야 폰에서 새 버전을 받는다.)
3. 커밋 후 두 브랜치에 모두 푸시: `git push origin main && git push origin main:gh-pages`
4. 확인: https://skt138500-code.github.io/rf-calc/

## 구조
- `src/calc.html`: 화면, 스타일, 계산 엔진(`<script id="engine">`), UI 스크립트가 들어 있는 단일 파일. claude.ai 아티팩트로도 그대로 게시 가능.
- `tools/build.py`: 구글 폰트 링크를 내장 폰트(`fonts/`)로 바꾸고 manifest, 설치 안내, service worker를 붙인다. 아이콘은 없을 때만 Pillow로 만든다.
- 탭: 계산 / RF(dBm·파장·스킨 깊이·VSWR·순방향/반사·dB) / 전원(SSPA → 분전반 전류·차단기·케이블) / 기록.
- 케이블 허용전류는 IEC 60364-5-52 구리, 부하 도체 3개 값(`AMP` 표). 참고용이며 앱 안에도 그렇게 적혀 있다.
- 사용자는 한국어를 쓰는 RF 엔지니어. 화면 문구는 한국어로 쓴다.
