---
name: motion-reference
description: モーションリファレンス (motion-reference.takayustudio.jp, TakayuStudio) — a Japanese dictionary of ~780 motion demos searchable by motion name, speed, easing and feel. Use only when picking a concrete motion pattern's name, duration (ms) or easing for this repo, when comparing two candidate motions, or when the user mentions this site or pastes an item from it. Link-only: no code or text from the site is stored here. Whether to animate at all is decided by this repo's rules and judgment skills first.
---

# モーションリファレンス — 이 저장소에서 쓰는 법

**사전이다.** "이 움직임을 뭐라고 부르고, 몇 ms 에 어떤 이징이면 그 느낌이 나나" 를 찾는 곳이지,
"움직여도 되나" 나 "어떻게 짜나" 를 정하는 곳이 아니다.

- 주소: https://motion-reference.takayustudio.jp/ (운영: たかゆ / TakayuStudio, https://takayustudio.jp)
- 내용(2026-10-20 확인): 모션 데모 782개(텍스트 모션 228종 포함). UI · 게임 · 스크롤 · 폼 · 제스처 · SVG ·
  원칙 · 이징 · 스프링 · 카메라 · 트랜지션. 항목마다 관찰 포인트 · 주의점 · 이징 곡선과 HTML/CSS/WAAPI/GSAP/React/After Effects 코드 탭,
  비교 · 조정 랩(이징 이름은 GSAP 식 `easeOutCubic` · `easeOutBack` …, 시간은 `ms`).

## 라이선스 — 꼭 지킬 것
- 사이트에 라이선스 · 이용약관이 **없다**. 적힌 것은 "オリジナルデモによる個人学習用リファレンス" (개인 학습용 레퍼런스) 한 줄과 운영자 사이트의 `© TakayuStudio` 뿐이다.
- 그래서 **코드 · 설명문 · 이미지 · 목록을 이 저장소에 복사하지 않는다**(참고용 사본 · 스니펫 모음 · 항목 목록 파일도 금지).
  가져오는 것은 **이름 · 수치(ms, cubic-bezier 값) · 관찰한 원리**뿐이고, 코드는 이 저장소의 방식으로 **새로 쓴다**.
- 코드를 그대로 쓰고 싶으면 먼저 사용자에게 말하고 운영자 허락을 받는다. 허락 없이 옮긴 코드는 넣지 않는다.
- 참고한 자리에는 주석 한 줄만 남긴다: `# 모션 참고: モーションリファレンス「<항목 이름>」(https://motion-reference.takayustudio.jp/) — 수치만 참고, 코드는 자체 작성`

## 찾는 법
- 사이트는 브라우저에서 그려지는 한 페이지라 WebFetch 로는 항목 내용이 안 보이고, 클라우드 세션의 curl 은 프록시에 막힌다(2026-10-20 실측).
  그러니 **사용자가 고른 항목의 이름 · ms · 이징(또는 화면 캡처)을 받아서** 쓰는 것이 기본이다. 사용자가 고르기 어려워하면
  사이트의 분류 이름과 찾을 낱말(예: "フェードイン", "スライド", "スプリング", "easeOutCubic")을 알려 준다.
- 수치를 옮길 때: GSAP 식 이징 이름 ↔ cubic-bezier 는 표준 값으로 바꾼다
  (`easeOutCubic` = `cubic-bezier(.33,1,.68,1)`, `easeInOutCubic` = `(.65,0,.35,1)`, `easeOutQuint` = `(.22,1,.36,1)`, `easeOutBack` = `(.34,1.56,.64,1)`, `easeInCubic` = `(.32,0,.67,0)`).
  스프링은 지속시간 · 감쇠 느낌만 가져오고, 이 저장소에 스프링 엔진을 새로 들이지 않는다.

## 다른 스킬과의 관계(겹칠 때)
1. 이 저장소 `CLAUDE.md` 의 규칙이 언제나 먼저다.
2. "움직일지 · 얼마나 절제할지" 는 판단 스킬이 정한다(아래 저장소별 절).
3. 그다음 이 사전에서 이름 · 수치를 고른다.
4. 구현은 이 저장소의 기존 모션 코드 · 구현 스킬로 한다.
사이트의 데모는 대부분 쇼케이스용이라 화려하다 — 업무 도구인 이 앱에는 **짧고 조용한 쪽**을 고르고, 끝없이 도는 장식 · 튀는 오버슈트 · 과한 이동은 고르지 않는다.

## 이 저장소(AOI-capacity 결과 HTML)에서
- 판단: `design-motion-principles`(주 관점 Emil Kowalski — 절제 · 속도) · `emil-design-eng`. 리뷰 `review-animations`, 프레임 예산 `animation-performance`.
- 구현: `template.html` 에 이미 인라인된 **GSAP 3.15 + Flip · animate.css 일부 · lottie_light** 와 CSS 만(`gsap` · `animate-css` · `lottie-web` 스킬).
  사이트의 React 탭은 쓰지 않고, GSAP · CSS 탭의 **수치**만 본다. 새 라이브러리 · CDN · 웹폰트는 들이지 않는다(바깥 요청 0건).
- `react-bits` 와의 구분: react-bits 는 **컴포넌트** 아이디어, 이 사전은 **움직임 하나의 이름 · 시간 · 이징**.
- CLAUDE.md 의 화면 규칙이 이긴다: **틀은 그대로, 내용만 바뀐다** · 등장 연출은 뷰 · 팝업이 처음 들어올 때 한 번 ·
  상태 150~300ms · 레이아웃/오버레이 300~500ms · 기본 `cubic-bezier(.16,1,.3,1)` · 나가는 것은 더 빠르게 · `prefers-reduced-motion` 이면 opacity 만.
  사이트 값이 이 범위를 벗어나면 이 범위로 맞춘다.
