# .claude/skills — 설치한 외부 스킬 (2026-10-06, 사용자 요청)

| 폴더 | 출처 · 고정 커밋 | 라이선스 | 무엇 |
|---|---|---|---|
| `taste-skill/` | https://github.com/Leonxlnx/taste-skill `skills/taste-skill` @ `ce26fc25` | MIT | 안티-슬롭 프론트엔드 원칙(랜딩·포트폴리오 중심 — 대시보드에는 원칙만 골라 씀) |
| `impeccable/` | https://github.com/pbakaus/impeccable `.claude/skills/impeccable` @ `cf3d2fa0` | Apache-2.0 (`LICENSE` · `NOTICE.md`) | UI 설계 · 감사 · 다듬기 · 애니메이션 · 문구 명령 모음 |
| `awesome-design-md/` | https://github.com/VoltAgent/awesome-design-md `design-md/` @ `13be5c05` | MIT | DESIGN.md 73개 참고 라이브러리(SKILL.md 는 이 저장소에서 덧붙인 안내) |
| `gsap/` | https://github.com/greensock/GSAP `types/` · `README.md` @ `13e2b790` (3.15.0) | GSAP Standard "no charge" (https://gsap.com/standard-license) | GSAP API 참고(타입 정의) + 이 저장소의 모션 규칙(10/7 추가) |
| `animate-css/` | https://github.com/animate-css/animate.css `source/` · `docsSource/sections` @ `3f8ab233` (4.1.1) | Hippocratic-2.1 (`LICENSE`) | 키프레임 원문 · 문서 + 인라인 부분집합 규칙(10/7 추가) |
| `lottie-web/` | https://github.com/airbnb/lottie-web `index.d.ts` · `docs/json` @ `bede03d2` (5.13.0) | MIT (`LICENSE.md`) | loadAnimation API · Bodymovin JSON 스키마 + 인라인 자산 규칙(10/7 추가) |
| `design-motion-principles/` | https://github.com/kylezantos/design-motion-principles `skills/design-motion-principles` @ `4a9ca879` | MIT (`LICENSE`) | 모션 설계 · 감사(Emil Kowalski · Jakub Krehel · Jhey Tompkins 세 관점, 안티-슬롭 체크리스트) — 원본 그대로(10/7 추가) |
| `react-bits/` | https://github.com/DavidHDev/react-bits `public/llms.txt` · `LICENSE.md` @ `63a008de` | MIT + **Commons Clause**(`LICENSE.md`) | React 애니메이션 · 컴포넌트 **목록**과 포팅 규칙만(10/7 추가) — 컴포넌트 소스는 넣지 않았다(라이선스가 묶음 · 포팅본 재배포를 금지). 필요할 때 고정 커밋에서 한 개만 받아 template 안에 포팅 |

- 원본을 고치지 않고 그대로 복사했다(awesome-design-md · gsap · animate-css · lottie-web 의 `SKILL.md` 와 이 README 만 새로 씀 — 세 라이브러리는 저장소에 스킬 파일이 없어 이 저장소 규칙을 담아 직접 썼다. 라이브러리 코드 자체는 이미 `template.html` 에 인라인돼 있다). 갱신은 같은 경로로 다시 복사한다.
- `.claude/` 는 업데이트 payload(`updater._UPDATE_TOP_ALLOW`) 밖이라 현장 PC 로 배포되지 않는다.
- 스킬의 규칙보다 `CLAUDE.md` 의 절대 규칙(바깥 요청 0 · 라이트 단일 · 용어 · "틀은 그대로, 내용만")이 우선한다.
- `design-motion-principles` 를 이 저장소에서 쓸 때: 대시보드는 업무 도구라 **Emil Kowalski(절제 · 속도)를 주 관점**으로 둔다 — `CLAUDE.md` 의 '틀은 그대로, 내용만 바뀐다' · 등장 연출은 처음 한 번과 같은 방향이다.
  감사 모드의 HTML 보고서(`references/report-template.html` · `demo-shell.html`)는 Google Fonts 를 불러온다 — **개발용 보고서에만** 쓰고, 그 글꼴 링크나 CDN 을 결과 HTML(`template.html`)로 옮기지 않는다(바깥 요청 0건). 보고서는 기본으로 저장소 맨 위 `motion-audits/` 에 쓰이니 커밋하지 않는다.
  예시 코드는 React · Framer Motion 중심이다 — 이 저장소는 순수 JS 렌더 + 인라인 GSAP/animate.css 이므로 원리만 가져온다(`gsap` · `animate-css` 스킬 참고).
