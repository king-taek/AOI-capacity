---
name: lottie-web
description: lottie-web 5.13 (lottie_light, SVG renderer) reference with this repo's rules — loadAnimation options and the AnimationItem API from index.d.ts, plus the Bodymovin JSON schema (layers, shapes, transforms, keyframes) for hand-writing small animations. Use before adding or editing a Lottie animation in the AOI result HTML (template.html): assets must be inline animationData, never a path or URL; respect reduced motion; keep the container data-static so the keyed morph leaves the SVG alone.
---

# lottie-web 5.13 (lottie_light) — 이 저장소에서 쓰는 법

## 지금 들어가 있는 것
- `template.html` 의 `<script id="vendor">` 에 **lottie_light 5.13.0**(SVG 렌더러만, MIT 머리말 유지).
- 자산은 **손으로 쓴 JSON 둘** — `const LOTTIE={scan:…, check:…}`(브랜드의 웨이퍼 스캔 표식 · 'Error 없음' 의 체크). 붙이는 곳은 `data-lottie="scan|check"` 요소, 한 번만 `lottie.loadAnimation({container, renderer:"svg", loop, autoplay:!reduced(), animationData})`.
- 컨테이너는 `data-static` — 렌더(morph)가 Lottie 가 그린 SVG 자식을 건드리지 않는다.
- `prefers-reduced-motion` 이면 재생하지 않고 마지막 프레임에 멈춘다.

## 규칙
- **`path` · URL 로 JSON 을 읽지 않는다**(가드가 확인) — 결과 HTML 은 바깥 요청 0건 · 파일 하나. 자산은 `LOTTIE` 객체에 인라인.
- 자산은 작게(수 KB): 몇 개 레이어 · 셰이프 · 짧은 키프레임. 외부 이미지 자산(`assets` 의 image)은 쓰지 않는다.
- lottie_light 는 SVG 렌더러만 있다 — `renderer:"canvas"`/`"html"` 를 쓰지 않는다. 표현식(expressions)은 light 빌드에서 동작하지 않는다.
- 하네스(Node)에는 lottie 가 없다 — 없을 때도 화면이 깨지지 않게(빈 컨테이너) 둔다.

## 참고 자료(이 폴더)
- `index.d.ts` — `loadAnimation` 옵션(`AnimationConfigWithData`) · `AnimationItem`(play/stop/goToAndStop/setSpeed/setDirection/destroy · 이벤트 `complete`/`loopComplete`/`DOMLoaded`).
- `docs/json/` — Bodymovin JSON 스키마: `animation.json`(맨 위: `v` · `fr` · `ip` · `op` · `w` · `h` · `layers`), `layers/` · `shapes/`(rect · ellipse · path · fill · stroke · group · trim …) · `helpers/transform.json` · `properties/`(애니메이션 값 · 키프레임 `k`/`t`/`s`/`i`/`o`). 손으로 쓸 때 이 스키마와 `LOTTIE.scan` 을 본보기로.
- `README.md` · `LICENSE.md`.

출처: https://github.com/airbnb/lottie-web @ `bede03d25d232826e0c9dca1733d542d8a7754fb` (5.13.0) — MIT (`LICENSE.md`).
