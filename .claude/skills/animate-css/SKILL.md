---
name: animate-css
description: animate.css 4.1.1 reference with this repo's rules — the full keyframe source (fading, sliding, zooming, attention seekers …), utility classes (delay, speed, repeat) and docs. Use before adding or changing an enter/exit or attention animation in the AOI result HTML (template.html) or a proposal/preview HTML: which subset is already inlined, how to copy another keyframe verbatim with its license header, and when to prefer a plain CSS keyframe or GSAP instead.
---

# animate.css 4.1.1 — 이 저장소에서 쓰는 법

## 지금 들어가 있는 것
- `template.html` 의 `<style>` 안에 **일부만 원문 그대로**: `:root` 변수(`--animate-duration` …) · `.animate__animated` · `.animate__faster` · reduced-motion 규칙 · `fadeIn` · `fadeOut` · `fadeInDown` · `fadeOutUp` · `fadeInUp` · `fadeOutDown`. 머리말(`animate.css - https://animate.style/ · Version 4.1.1 · Hippocratic License 2.1`)을 지우지 않는다.
- 쓰는 곳: 팝업 덮개(`.ov`) 들고남(`animate__fadeIn/fadeOut`), 토스트 · 필터 칩 · 선택 Lot 상세(`fadeInUp/Down`). 클래스는 끝나면 즉시 뗀다(`onEnd`).
- 대화상자 자체의 등장 · 퇴장은 animate.css 가 아니라 자체 키프레임(`.dlg.in/.out` — `dlgIn/dlgOut`)이다. 덱 transform transition 과 겹치지 않게 하려고 바꿨다(9/21).

## 규칙
- 바깥 요청 0건 — `animate.min.css` 를 링크로 붙이지 않는다. 필요한 키프레임만 `source/` 에서 **원문 그대로** 복사해 기존 블록 안에 넣고, 블록 머리말의 '실은 것' 목록을 갱신한다.
- 클릭마다 다시 도는 연출은 두지 않는다(CLAUDE.md '틀은 그대로, 내용만'). 주의를 끄는 효과(attention seekers: bounce · shake · pulse …)는 사용자가 요청할 때만, 1회.
- 같은 요소에 GSAP 트윈과 animate.css 클래스를 함께 걸지 않는다.

## 참고 자료(이 폴더)
- `source/<묶음>/<이름>.css` — 애니메이션마다 키프레임 + 클래스 원문(`_vars.css` · `_base.css` 가 공통 부분). 묶음: fading · sliding · zooming · back · bouncing · flippers · lightspeed · rotating · specials · attention_seekers.
- `docs/` — 원 문서: 사용법(`01-usage.md`), 유틸리티 클래스(지연 · 속도 · 반복, `02-utilities.md`), 모범 사례(`03-best-practices.md` — 큰 요소 · 루트 요소 · 무한 반복 피하기), JS 로 쓰기(`04-javascript.md`), 접근성(`08-accessibility.md`).
- `README.md` · `LICENSE`.

출처: https://github.com/animate-css/animate.css @ `3f8ab233dbbd9d2fe577528d2296382954be3d1a` (4.1.1) — Hippocratic License 2.1 (`LICENSE`).
