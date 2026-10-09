# RF 공학계산기

광고 없는 오프라인 공학계산기. 휴대폰에서 아래 주소를 열고 홈 화면에 추가하면 인터넷 없이 앱처럼 쓸 수 있습니다.

https://skt138500-code.github.io/rf-calc/

- 계산: 삼각·역삼각, ln/log, 지수, 루트, 팩토리얼, EE, Ans, DEG/RAD, NORM/SCI/ENG(SI 접두어)
- RF: dBm⇄W, 주파수→파장, 스킨 깊이, VSWR⇄반사손실⇄|Γ|, 순방향/반사 전력, dB⇄비율
- 전원: SSPA RF 출력·DC 효율 → DC 전류, 분전반 전류, 차단기, 케이블 굵기(IEC 60364-5-52 참고), 접지선, 발열량

## 수정
원본은 `src/calc.html`이고, `python3 tools/build.py`로 앱 파일을 다시 만든 뒤 `main`과 `gh-pages` 브랜치에 푸시합니다. 자세한 순서는 `CLAUDE.md`에 있습니다.
