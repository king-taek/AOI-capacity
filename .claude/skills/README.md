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
| `ponytail/` · `ponytail-review/` · `ponytail-audit/` · `ponytail-debt/` · `ponytail-help/` · `ponytail-gain/` | https://github.com/DietrichGebert/ponytail `skills/*` @ `09c434ab` | MIT (`LICENSE`) | 코드를 덜 쓰게 하는 지침 + diff 검토 · 저장소 감사(10/18 추가) — 원본 플러그인의 hook · band 는 연결하지 않음 |
| `graphify/` | https://github.com/safishamsi/graphify `graphify/skill.md` + `graphify/skills/claude/references/` @ `86c57be8` (0.9.92) | Apache-2.0 (`LICENSE` · `NOTICE`) | 대화 중 코드 그래프 질의(10/18 추가) — 그래프 생성 자체는 이미 CI(`graphify.yml` · `dev/tools/graphify_build.py`)가 한다 |

- 원본을 고치지 않고 그대로 복사했다(awesome-design-md · gsap · animate-css · lottie-web 의 `SKILL.md` 와 이 README 만 새로 씀 — 세 라이브러리는 저장소에 스킬 파일이 없어 이 저장소 규칙을 담아 직접 썼다. 라이브러리 코드 자체는 이미 `template.html` 에 인라인돼 있다). 갱신은 같은 경로로 다시 복사한다.
- `.claude/` 는 업데이트 payload(`updater._UPDATE_TOP_ALLOW`) 밖이라 현장 PC 로 배포되지 않는다.
- 스킬의 규칙보다 `CLAUDE.md` 의 절대 규칙(바깥 요청 0 · 라이트 단일 · 용어 · "틀은 그대로, 내용만")이 우선한다.
- `design-motion-principles` 를 이 저장소에서 쓸 때: 대시보드는 업무 도구라 **Emil Kowalski(절제 · 속도)를 주 관점**으로 둔다 — `CLAUDE.md` 의 '틀은 그대로, 내용만 바뀐다' · 등장 연출은 처음 한 번과 같은 방향이다.
  감사 모드의 HTML 보고서(`references/report-template.html` · `demo-shell.html`)는 Google Fonts 를 불러온다 — **개발용 보고서에만** 쓰고, 그 글꼴 링크나 CDN 을 결과 HTML(`template.html`)로 옮기지 않는다(바깥 요청 0건). 보고서는 기본으로 저장소 맨 위 `motion-audits/` 에 쓰이니 커밋하지 않는다.
  예시 코드는 React · Framer Motion 중심이다 — 이 저장소는 순수 JS 렌더 + 인라인 GSAP/animate.css 이므로 원리만 가져온다(`gsap` · `animate-css` 스킬 참고).
- ponytail 은 **lite 또는 off** 로 쓴다(CLAUDE.md) — 이 저장소의 방어 코드(STALE · NAS 가드 · 범위 게이트)는 줄일 대상이 아니다. `/ponytail-review` · `/ponytail-audit` 위주.
- graphify 는 `--code-only` 로 돌린다(`docs/` 는 `.graphifyignore` 로 빠져 있다). template.html 의 인라인 JS 까지 보려면 `python dev/tools/graphify_build.py --out <임시 폴더>` 를 쓴다 — 스킬의 기본 `/graphify .` 는 인라인 `<script>` 를 읽지 못한다.

## 10/18 추가 설치 (사용자 요청 — 다양하게, 자동으로)

| 폴더 | 출처 · 고정 커밋 | 라이선스 | 무엇 |
|---|---|---|---|
| `brainstorming/` · `systematic-debugging/` · `test-driven-development/` · `writing-plans/` · `executing-plans/` · `subagent-driven-development/` · `dispatching-parallel-agents/` · `requesting-code-review/` · `receiving-code-review/` · `verification-before-completion/` · `finishing-a-development-branch/` · `using-git-worktrees/` · `writing-skills/` · `using-superpowers/` | https://github.com/obra/superpowers `skills/*` 6.1.1 (Defect_Tracking 과 같은 사본) | MIT (`.claude/licenses/superpowers-MIT.txt`) | 계획 → 테스트 먼저 → 체계적 디버깅 → 완료 전 검증 → 리뷰 요청/받기 흐름 |
| `interview-me/` · `documentation-and-adrs/` · `observability-and-instrumentation/` · `deprecation-and-migration/` · `security-and-hardening/` · `performance-optimization/` | https://github.com/addyosmani/agent-skills `skills/*` @ `aeac41d4` | MIT (`.claude/licenses/addyosmani-agent-skills-MIT.txt`) | 요구 묻기 · 결정 기록 · 로그 · 삭제/이전 · 보안 · 성능. 체크리스트는 `.claude/references/` |
| `change-impact/` · `codebase-onboarding/` · `code-tour/` · `python-testing/` · `regex-vs-llm-structured-text/` · `skill-stocktake/` + 에이전트 `.claude/agents/silent-failure-hunter.md` · `python-reviewer.md` | https://github.com/affaan-m/ecc @ `76aaa77d` (v2.2.3) 에서 발췌 | MIT (`.claude/licenses/ecc-MIT.txt`) | 변경 영향 · 코드 안내 · pytest · 파서 판단 · 스킬 점검 · 조용한 실패/파이썬 리뷰 |
| `ui-ux-pro-max/` | https://github.com/nextlevelbuilder/ui-ux-pro-max-skill `.claude/skills/ui-ux-pro-max` @ `56ea9cf1` (2.15.0) | MIT (`.claude/licenses/ui-ux-pro-max-MIT.txt`) | 로컬 CSV 로 팔레트 · 글꼴 · UX 지침 검색(네트워크 없음) |
| `design-dna/` | https://github.com/zanwei/design-dna @ `593e39bc` | MIT (`LICENSE`) | 참고 화면에서 토큰 · 느낌 · 효과를 JSON 으로 뽑고 적용 |
| `frontend-design/` | https://github.com/anthropics/skills `skills/frontend-design` @ `dbd4588f` | Apache-2.0 (`LICENSE.txt`) | 새 화면의 미적 방향 · 글꼴 선택 |
| `review-animations/` · `improve-animations/` · `animation-performance/` · `emil-design-eng/` | https://github.com/emilkowalski/skills @ `2d228630` | MIT (`.claude/licenses/emilkowalski-skills-MIT.txt`) | 모션 리뷰 · 개선 계획 · 프레임 예산 · Emil Kowalski 원칙 |

- 원본을 고치지 않고 그대로 복사했다(awesome-design-md 의 `SKILL.md` 만 예외). hook 은 하나도 연결하지 않았다 — ECC 의 gateguard 처럼 수정마다 멈추게 하는 것이 있어서다. ECC 의 토큰 · 모델 설정도 가져오지 않았다.
- 설치 전 NVIDIA SkillSpector(`--no-llm`)로 전부 검사했다. 걸린 항목은 공격 용어를 설명하는 문서 · 스킬 파일을 고치라는 안내(writing-skills) · 중첩 코드 블록을 위한 폭 0 공백(improve-animations `PLAN-TEMPLATE.md`) 같은 오탐이었고, 스크립트에 바깥 전송은 없었다.
- Addy 스킬이 `../../references/*.md` 로 가리키는 체크리스트는 `.claude/references/` 에 있다. 폴더 안에 라이선스가 없는 출처의 원문은 `.claude/licenses/` 에 있다.
- 겹칠 때 우선순위는 `CLAUDE.md` 에 적었다. 갱신은 같은 고정 커밋 경로에서 다시 복사한다.
- 결과 HTML 의 바깥 요청 0건 규칙이 모든 디자인 · 모션 스킬보다 우선한다(웹폰트 · CDN · 사진 URL 금지). 모션은 CLAUDE.md 의 '틀은 그대로, 내용만' 을 따른다.
