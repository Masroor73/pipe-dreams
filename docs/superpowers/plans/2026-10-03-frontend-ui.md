# Frontend UI — Implementation Plan

Spec: `docs/superpowers/specs/2026-10-03-frontend-ui-design.md`. Contract: `docs/API_CONTRACT.md`. Package manager: npm (pnpm unavailable). Each task is one worker; workers must not touch `engine/`, `backend/`, or `docs/API_CONTRACT.md`, and must never compute ranks/scores/gate outcomes client-side.

## Task 1 — Scaffold + design system (sequential, blocks all others)
- Vite + React + strict TS in `frontend/`; approved deps only; ESLint not required.
- `src/styles/tokens.css` (impeccable skill): type scale (min 14px), spacing, colour tokens (one water-blue accent; semantic accept/reject and HIGH/MEDIUM/LOW_VERIFY colours), radii, shadows, motion durations; Fontsource font.
- `src/lib/api.ts` (typed fetch per endpoint, `ApiError`, fixture mode), `src/fixtures/*.json`, `src/hooks/use*.ts`, `src/lib/synthetic.ts` (banner predicate), `src/lib/format.ts` (display-only formatting).
- Router shell: banner, top nav, health gate, `?asset=` side-panel slot, placeholder pages.
- Shared components: `SyntheticBanner`, `DataState` (loading/empty/error), `Section`.
- Tests: api client, banner predicate/component, DataState.
- Acceptance: `npm run typecheck`, `npm test`, `npm run build` pass.

## Task 2 — Overview page (parallel after 1)
Headline, capture chart with CI whiskers + split selector, gate cards, rank-change cards, teasers, footer. Tests for headline (V2 vs V1-retained), gate cards, rank cards, empty/error.

## Task 3 — Map page + asset side panel (parallel after 1)
MapLibre via `react-map-gl/maplibre`, offline plain-background style, V1/V2 toggle, confidence colours + legend, click → `?asset=`. `AssetPanel` slide-in with V1/V2 side by side. Tests for panel states.

## Task 4 — Audit, Escalation, Limits pages (parallel after 1)
Vertical timeline, sortable escalation table (sorting is UI ordering only), not-covered list + data-quality figures. Tests for empty/error and sorting.

## Task 5 — Polish + critique (after 2–4)
emil-design-eng polish (hover/press, panel slide, tab transitions, reduced motion); impeccable critique from Playwright screenshots; fix; save screenshots to `frontend/screenshots/`.

## Task 6 — Docs (orchestrator)
TECH_STACK.md frontend deps with justifications; README run instructions.
