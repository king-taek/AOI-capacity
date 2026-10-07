---
name: gsap
description: GSAP 3.15 (GreenSock) API reference with this repo's rules — tweens, timelines, eases, Flip, Draggable/Observer and the other now-free plugins, read from the bundled TypeScript definitions. Use before writing or changing any motion in the AOI result HTML (template.html) or a proposal/preview HTML: which GSAP calls are already inlined, how Flip is wired to the keyed morph, reduced-motion handling, and how to add a plugin without breaking the zero-external-request rule.
---

# GSAP 3.15 — 이 저장소에서 쓰는 법

## 지금 들어가 있는 것
- `aoi_capacity/ui/assets/template.html` 의 `<script id="vendor">` 에 **GSAP 3.15.0 본체 + Flip 플러그인**이 원문 그대로(머리말 · 라이선스 줄 유지) 인라인돼 있다. CDN 은 쓰지 않는다 — 결과 HTML 은 바깥 요청 0건(가드 `test_no_network_use_at_all` · `test_vendor_block_makes_no_requests_either`).
- 준비: `gInit()` 이 `gsap.registerPlugin(Flip)` · `gsap.defaults({ease:"power3.out"…})`. 쓸 수 있는지는 `G()` / `canAnim()`(Node 하네스에는 gsap 이 없어 false → morph 만). `reduced()`(prefers-reduced-motion)면 이동 없이 opacity 만.
- 실제로 쓰는 곳: `flipAfter`(목록 컨테이너의 키 순서가 바뀌거나 행이 들고날 때만, 3px 이상 움직인 행만 Flip), `enterView`(뷰 · 팝업이 처음 들어올 때 한 번 — 카드 stagger, 막대 `scaleY` 성장), 카운트업 `cnt()`(`.cards` 안 값이 바뀔 때만). 탭 표시자 `navGo` 는 GSAP 이 아니라 **WAAPI**(합성 스레드).

## 규칙(CLAUDE.md 정본 — 요약)
- **틀은 그대로, 내용만 바뀐다**: 루트 · 무대(`#app` · `.stage`)에 Flip 금지, 행 안 내용만 바뀐 렌더에는 transform 을 주지 않는다. 등장 연출은 처음 한 번.
- 막대 등장은 `scaleY` — `gsap.from({height:0}, clearProps:"height")` 는 inline `height:%` 까지 지워 막대가 주저앉는다(실측).
- 같은 요소에 GSAP 트윈과 CSS transition/animation 을 겹치지 않는다(`clearProps` 가 transition 을 다시 일으킨다 — 9/21 전수 감사).
- 시간: 상태 150~300ms, 레이아웃/오버레이 300~500ms, `cubic-bezier(.16,1,.3,1)` 계열, 나가는 것은 들어오는 것보다 빠르게.

## 새 플러그인이 필요할 때
GSAP 3.13 부터 모든 플러그인이 무료다(Draggable · InertiaPlugin · SplitText · MorphSVG · ScrollTrigger · Observer …). `types/` 에 전부 있다.
1. 정말 필요한지 먼저 본다 — 끌기 하나는 pointer 이벤트 몇 줄이 더 가볍다(파일 크기 · 인라인 vendor 가 커진다).
2. 쓴다면 npm `gsap@3.15.0` 의 `dist/<Plugin>.min.js` **원문 그대로**를 vendor 블록에 붙이고(머리말 유지), `gInit` 에서 `registerPlugin`. 가드의 허용 목록(gsap.com · w3.org)을 넘는 주소가 생기면 안 된다.
3. 브라우저 테스트(`dev/tests/test_dashboard_browser.py`)로 콘솔 오류 0 · 바깥 요청 0 확인.

## 참고 자료(이 폴더)
- `types/*.d.ts` — 공식 타입 정의(주석이 곧 API 설명). 자주 볼 것: `gsap-core.d.ts`(to/from/fromTo/set/timeline/defaults/utils), `tween.d.ts` · `timeline.d.ts`, `ease.d.ts`, `flip.d.ts`, `draggable.d.ts`, `observer.d.ts`, `gsap-utils.d.ts`.
- `README.md` — 원 저장소 README. 전체 문서는 https://gsap.com/docs (이 세션에서 웹을 못 쓰면 types 가 정본).

출처: https://github.com/greensock/GSAP @ `13e2b790546426a1a2e0e9b409f3f8dc6d6611f2` (3.15.0) — GSAP Standard "no charge" license: https://gsap.com/standard-license (저장소에 LICENSE 파일이 따로 없다; 인라인 코드의 머리말이 라이선스 고지다).
