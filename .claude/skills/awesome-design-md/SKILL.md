---
name: awesome-design-md
description: Reference library of 73 DESIGN.md design-system analyses (Linear, Vercel, Stripe, Apple, Claude, …) from VoltAgent/awesome-design-md. Use when choosing or comparing visual language — type scale, spacing, color tokens, component density, dashboard/table patterns — for the AOI result HTML or the PyQt6 collector window. Read only the one or two DESIGN.md files that fit the question; never copy a brand's identity (logo, name, signature colors) into this product.
---

# awesome-design-md (참고 라이브러리)

`design-md/<브랜드>/DESIGN.md` 마다 한 회사 화면의 디자인 체계(글꼴 · 간격 · 색 토큰 · 컴포넌트 · 원칙)가 정리돼 있다.

## 이 저장소에서 쓰는 법
- 결과 HTML 의 토큰 · 색 · 용어 · 애니메이션 원칙의 정본은 `CLAUDE.md` 와 `template.html` 의 `:root` 다. 여기 파일은 **비교 · 영감용**이며 정본을 덮어쓰지 않는다.
- 데이터가 많은 업무 화면(표 · 목록 · 대시보드)에 가까운 것부터 본다: `linear.app`, `vercel`, `stripe`, `sentry`, `posthog`, `supabase`, `raycast`, `notion`, `claude` 등 (`ls design-md/` 로 전체 목록).
- 브랜드 고유 요소(로고 · 이름 · 시그니처 색)는 가져오지 않는다. 바깥 요청 0건 규칙 때문에 웹폰트 · CDN 도 쓰지 않는다.

출처: https://github.com/VoltAgent/awesome-design-md (MIT, `LICENSE`)
