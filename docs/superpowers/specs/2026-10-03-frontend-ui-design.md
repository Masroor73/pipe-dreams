# Frontend UI — Design Spec (approved 2026-10-03)

Scope: the React + TypeScript + Vite app in `frontend/`. Presentation only (AGENTS.md rule 2, DECISIONS §19): every rank, score, gate outcome and policy selection is read from the API (`docs/API_CONTRACT.md`) and displayed verbatim. No client-side scoring, no LLM, no Bearspaw claims (DECISIONS §17).

## Shell
- Persistent thin **SYNTHETIC / PLACEHOLDER DATA** banner at the very top whenever any response has `meta.synthetic == true` or `meta.config_hash == "PLACEHOLDER"` (ARCHITECTURE §11), including deep links.
- Top nav: **Overview · Map · Agent audit · Escalation · Limits**.
- If `/api/health` is `degraded` (or unreachable), show an app-level "Artifacts unavailable" state instead of pages.
- Asset detail is a right-hand side panel that slides in over any page, driven by `?asset=<id>`; it shows V1 vs V2 side by side from `/api/assets/{id}`.

## Pages
1. **Overview** (one scroll, in demo order)
   1. Headline: "V2 catches X% of future breaking assets at 5% budget vs Y% count-only", or "V1 retained" when `v2_equals_v1`. Values are looked up from `series` rows, never computed.
   2. Capture chart (Recharts): count-only, organizer baseline (event capture only, since its `asset_capture` is null), V1, V2 at 1/2/5/10% budgets with CI whiskers. Split selector (final / validation origin / confirmation) picks which rows are shown.
   3. Agent decision: C1–C4 gate cards (ACCEPT/REJECT, origin wins x/n, difference vs required_delta) from `/api/audit` candidate fields.
   4. Three rank-change cards (`/api/rank-changes?demo_only=true`).
   5. Escalation and limits teasers linking to their tabs.
   6. Footer: config hash, git tag/commit, and the "final test window viewed once before" disclosure (`final_test_previously_viewed`).
2. **Map**: full-bleed MapLibre (`react-map-gl/maplibre`) from `/api/assets/geojson`, V1/V2 toggle, lines coloured by `evidence_confidence`. No-tile fallback: lines on a plain background; works offline. Clicking a line opens the asset panel.
3. **Agent audit**: vertical timeline PLAN_V1 → … → PLAN_V2 from `/api/audit`; candidate events show their gate figures.
4. **Escalation**: sortable table of `/api/escalations`.
5. **Limits**: not-covered items (`/api/not-covered`) and data-quality figures (`/api/data-quality`).

## Visual tone
Calm engineering. Light theme only, generous white space, one water-blue accent; green/amber/red only where they carry meaning (accept/reject, confidence tiers). Tabular numerals. Projector-legible: no text below 14px. Desktop/laptop only. Plain CSS with tokens in `src/styles/tokens.css`; Phosphor icons only; one self-hosted Fontsource typeface. Motion via CSS transitions, respecting `prefers-reduced-motion`.

## Code structure
- `src/types/api.ts` — contract types (snake_case).
- `src/lib/api.ts` — one typed fetch per endpoint; fixture mode when `VITE_USE_FIXTURES=true`.
- `src/fixtures/` — contract-shaped synthetic JSON (`meta.synthetic: true`, `config_hash: "PLACEHOLDER"`).
- `src/hooks/` — one data hook per endpoint (loading / error / data / meta).
- `src/pages/` — one per tab. `src/components/` — banner, chart, gate cards, rank cards, side panel, timeline, tables, state blocks.
- Every data block has loading, empty and error states.

## Testing
Vitest + Testing Library: API client, banner logic, section empty/error states, overview/decision/rank-change rendering. Visual check with Playwright MCP screenshots (saved to `frontend/screenshots/`, synthetic, review only).
