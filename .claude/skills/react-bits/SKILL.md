---
name: react-bits
description: React Bits (DavidHDev/react-bits) catalog — 100+ animated UI pieces (text animations, animations, backgrounds, components, micro-interactions) with one-line descriptions, plus how to fetch a single component's source at a pinned commit and port it to this repo's vanilla-JS dashboard. Use when looking for an interaction or motion idea (counters, list reveals, spotlight cards, toggles, loaders, tooltips) for the AOI result HTML or a proposal/preview HTML. The components are React and many need three/ogl/motion — port only the idea or small vanilla-able ones; never vendor the library.
---

# React Bits — 이 저장소에서 쓰는 법

React Bits 는 **스킬 저장소가 아니라 React 컴포넌트 모음(웹사이트 소스, 248MB)** 이다. 그래서 이 폴더에는 **목록 · 라이선스 · 쓰는 법만** 두고, 컴포넌트 코드는 넣지 않았다(아래 라이선스).

## 이 폴더에 있는 것
- `llms.txt` — 원 저장소가 AI 용으로 낸 전체 목록(분류 · 이름 · 한 줄 설명 · 페이지 주소). **아이디어는 여기서 찾는다.**
- `components_index.txt` — 분류별 폴더 이름(소스 경로를 찾을 때).
- `LICENSE.md` — MIT + **Commons Clause**.

## 라이선스 — 꼭 지킬 것
- 제품의 **일부로 쓰는 것**(포팅해서 template 안에 넣기 포함)은 상업적 용도로도 허용된다. 저작권 고지를 남긴다.
- **컴포넌트 자체를 재배포하면 안 된다** — 그대로든, 묶음이든, **포팅한 버전이든** 따로 떼어 내놓는 것 금지. 그래서:
  - 원본 소스를 이 저장소에 통째로 · 여러 개 복사해 두지 않는다(참고용 사본도 'bundle' 이 된다).
  - 포팅한 코드는 **template.html 안에서 제품의 일부로만** 쓰고, 그 자리에 출처 주석을 단다:
    `/* 이 모션은 React Bits <이름>(https://github.com/DavidHDev/react-bits, MIT + Commons Clause)을 바탕으로 포팅 */`
  - 포팅한 것을 별도 라이브러리 · 스니펫 모음으로 내놓지 않는다.

## 컴포넌트 하나의 소스 보기(개발 환경에서만, 커밋하지 않음)
```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/DavidHDev/react-bits /tmp/react-bits
cd /tmp/react-bits && git sparse-checkout set src/content/<분류>/<이름>   # 예: src/content/TextAnimations/CountUp
# JS+CSS 는 src/content/…, TS+CSS 는 src/ts-default/… — 고정 커밋: 63a008de65732d73010bd219d25d15c47739bb31
```
(웹: 각 컴포넌트 페이지 `https://www.reactbits.dev/<분류>/<kebab-이름>` — 이 세션에서 웹을 못 쓰면 git 으로.)

## 포팅 규칙(CLAUDE.md 정본이 우선)
- 결과 HTML 은 **React 없음 · 바깥 요청 0건 · 단일 파일**. 쓸 수 있는 라이브러리는 이미 인라인된 **GSAP 3.15 + Flip · animate.css 일부 · lottie_light** 뿐(`gsap` · `animate-css` · `lottie-web` 스킬). **three · ogl · motion(framer-motion) · matter-js 가 필요한 것은 쓰지 않는다**(Backgrounds 대부분, 3D · WebGL 효과).
- 렌더는 `render()` → HTML 문자열 → 키 있는 morph. React 의 상태 · 이펙트는 `state` + `setState` 와 렌더 뒤 훅(`enterView` 류)으로 옮긴다. 매 렌더마다 다시 도는 효과는 금지(**틀은 그대로, 내용만 바뀐다** · 등장 연출은 처음 한 번).
- 업무 대시보드다 — 커서 효과 · 반짝이 테두리 · 파티클 · 끊임없이 움직이는 배경은 넣지 않는다. `design-motion-principles` 스킬의 **Emil Kowalski(절제 · 속도)** 관점으로 거른다. `prefers-reduced-motion` 을 존중한다.

## 이 대시보드에 쓸 만한 후보(아이디어 수준 — 쓰기 전에 사용자에게 안으로 보여 준다)
- Text Animations: **Count Up**(이미 비슷한 `cnt()` 있음) · Shuffle/Decrypted 계열(글자 넘김 `txMix` 와 겹침 — 바꿀 이유가 있을 때만)
- Animations: **Fade Content · Animated Content**(처음 등장 한 번) · Gradual Blur(긴 목록 끝 흐림)
- Components: **Animated List**(목록 등장) · **Spotlight Card**(카드 hover 강조, 아주 약하게) · **Stepper** · **Elastic Slider**(값 고르기) · Counter
- Micro: **Status Mark**(상태 아이콘) · **Hold Button**(되돌릴 수 없는 동작 확인) · Squish Switch · Warm Tooltip · Lattice Loader(로딩)

출처: https://github.com/DavidHDev/react-bits @ `63a008de65732d73010bd219d25d15c47739bb31` — MIT + Commons Clause License Condition v1.0 (`LICENSE.md`).
