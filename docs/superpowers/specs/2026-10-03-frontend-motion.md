# Frontend Motion Thesis (2026-10-03)

Presentation only (AGENTS.md rules 2, 9; DECISIONS §19). Motion reveals API values; it never computes, reorders, or invents them. No new dependencies: CSS transitions/keyframes, Web Animations API, View Transitions API, `requestAnimationFrame`. Tokens from `src/styles/tokens.css`; helpers from `src/hooks/motion.ts` (`prefersReducedMotion`, `usePrefersReducedMotion`, `useInViewOnce`).

## Thesis
Motion in Pipe Dreams exists to show that a decision was *made*, in order, against a bar, by an auditable process, and then to get out of the way. The product's claim is "the agent tested candidates and accepted only what cleared the gate"; one short, rehearsed sequence makes that sequence of evidence visible (testing, evidence accumulating, verdict). Everything else is quiet: orientation, continuity, acknowledgment. Anything that would not lose meaning if removed is cut.

## Focal moment: "the agent deciding" (Overview, once on first view)
Gate cards C1-C4 enter view (`useInViewOnce`, threshold 0.35) and resolve in `seq` order, 400 ms apart. Per card (~600 ms): "testing…" label (0-150 ms) -> origin-win dots fill, 40 ms stagger (150-350 ms) -> pooled-gain bar grows to its API value toward the required marker, `scaleX` (150-470 ms) -> ACCEPT/REJECT stamp lands, scale 1.12 -> 1 + opacity (470-620 ms). The card selected as V2 gets "Selected as V2" emphasis last (ring/opacity, 1800-2200 ms). **Total 2.2 s.** Non-blocking: all content is in the DOM at its end state from first paint (animation is `from`-only via WAAPI, so a script failure shows the final state); clicks, scroll, and links work throughout; a click anywhere on the section, or `Esc`, calls `finish()` on all animations. Never replays on re-render; `Replay` is not offered on Overview.

**Audit tab companion:** "Replay agent run" button (the user's explicit action, so a longer run is acceptable). Steps timeline events in `seq` order, 350 ms each (event fades/rises 6 px over 200 ms, previous highlight drops), capped at 6 s total (step shortens to fit). Button becomes "Stop"; Stop or `Esc` shows everything instantly. Keyboard-triggerable, focus stays on the button.

## Continuity
- Tab/route change: cross-fade via `document.startViewTransition` (120 ms out is implicit in the browser cross-fade; duration 200 ms, `--ease-in-out`). Feature-detected; fallback is an instant swap. Banner and nav carry `view-transition-name` so they never fade.
- Asset panel: keeps existing slide-in (transform, 200 ms ease-out; exit 150 ms).
- Split-tab switch (chart): the new series draws left to right (see table), old lines unmount instantly (exit faster than enter).
- Map V1/V2 toggle: changed segments briefly emphasized so the viewer sees *what the plan change was*.

## Feedback
Buttons/tabs/toggles: `:active` `scale(0.97)`, 150 ms; hover/focus color changes 150 ms; hover effects gated by `(hover: hover) and (pointer: fine)`. Sortable-table sort changes: instant. Keyboard actions are never animated beyond focus ring.

## Budget
| Item | Limit |
|---|---|
| Routine interaction | <= 200 ms (`--duration-fast` 150 / `--duration-base` 200) |
| Authored one-time reveals | <= 600 ms each; whole Overview first-view choreography <= 2.4 s, only gate sequence exceeds 600 ms in aggregate |
| Easing | enter/draw: `cubic-bezier(0.22, 1, 0.36, 1)` (`--ease-out`); on-screen move/cross-fade: `cubic-bezier(0.65, 0, 0.35, 1)` (`--ease-in-out`); count-up/line draw use `--ease-out`; no ease-in, bounce, or elastic |
| Stagger | 40 ms (dots), 80 ms (rank cards), 400 ms (gate cards, authored) |
| Max concurrent | 6 running animations at any moment (gate cards overlap by ~200 ms, so <= 2 cards active); everything else sequenced |
| Properties | transform, opacity, stroke-dashoffset only; no width/height/top/left/blur; `will-change` set only while running, removed on `finish` |
| Map | WebGL paint opacity transition only; one pulse per toggle |
| Reduced motion | `prefersReducedMotion()` -> skip animation, render end state; opacity/color state feedback (stamp color, selected ring) stays as an instant change |
| **Never animated** | SYNTHETIC banner; data tables (escalation, limits, data-quality); every number in the escalation table; footer/disclosures; chart axes, CI whiskers, tooltips; error/empty/loading states |

## Per-item spec
| Item | Trigger | Property | Duration | Easing | Delay / stagger | Reduced motion | Technique |
|---|---|---|---|---|---|---|---|
| Gate sequence (cards, dots, bar, stamp) | Section first in view (once) | opacity, transform (`scaleX` bar, scale stamp) | 600 ms/card; total 2.2 s | ease-out | card 400 ms; dots 40 ms | End state instantly | WAAPI timeline from `useInViewOnce`, `finish()` on skip |
| "Selected as V2" emphasis | After last card | opacity, ring transform | 400 ms | ease-out | at 1800 ms | Static emphasis | WAAPI |
| Audit "agent run as cinema" (replaces the old replay button) | Play / scrubber / arrow keys / Space | Top 25 FLIP (transform), gate stamp (opacity, scale 1.08), map ring (transform, opacity), timeline dim (opacity) | Dwell 0.9 to 2 s per step by event type; FLIP 560 ms on autoplay, 240 ms on manual steps; stamp 180 ms; ring 700 ms | ease-in-out (0.77,0,0.175,1) for moves; ease-out otherwise | 14 ms per moved row on autoplay | Every step jumps to its end state; no FLIP, no rings, no caption animation | `useCinema` (step state), `frameAt` (pure sequencing), `useFlip` (batched reads, WAAPI writes) |
| Headline / stat count-up | First view | text only (tabular-nums, fixed width) | 600 ms | ease-out | none | Final value | rAF; last frame sets the exact API string |
| Capture chart lines | First render; split switch | stroke-dashoffset | 600 ms first, 400 ms switch | ease-out | 60 ms per series | Drawn instantly | `pathLength=1` dash trick; whiskers/points fade in 150 ms after line |
| Rank-change cards | First view | arrow translateX 8 px + opacity (rank count-up removed in review: it showed the V1 rank as V2 before scrolling into view) | 320 ms | ease-out | 80 ms per card | Final rank + arrow | WAAPI arrow |
| Map changed-segment emphasis | Load; V1/V2 toggle | line-opacity pulse (0.35 -> 1) on changed segment ids | 500 ms | ease-in-out | none | No pulse | MapLibre paint transition; ids from API plan diff, not computed |
| Tab cross-fade | Nav click | opacity | 200 ms | ease-in-out | none | Instant swap | `startViewTransition` |
| Asset panel | `?asset=` change | transform | 200 in / 150 out | ease-out | none | Instant | existing CSS |
| Section fade/rise | First scroll into view | opacity, translateY 8 px | 320 ms | ease-out | none | Instant | `useInViewOnce`; CSS class |
| Press feedback | `:active` | transform scale 0.97 | 150 ms | ease-out | none | Kept (not spatial travel) | CSS |

## Cut / not doing
- Section fade/rise limited to the Escalation/Limits teasers and footer only (headline, chart, gates, rank cards have their own reveals); trimmed from "all Overview sections".
- Map segment *width* animation (non-compositor); opacity pulse only.
- Replay on Overview; looping, idle, or ambient animation; parallax; scroll-driven animation.
- Number count-up on tables, escalation figures, or data-quality values.
- Chart point/whisker animation beyond a single fade; tooltip animation.
- Page-load choreography, skeleton shimmer beyond a static placeholder, bounce/spring.
- Any animation that gates interaction or hides content until finished.

## Agent-run cinema: contract gap

The cinema uses only existing routes: `/api/audit`, `/api/assets?plan=v1|v2&limit=25`, `/api/rank-changes`, `/api/escalations`, and `/api/assets/{id}` for the centroids of escalated assets that are outside both Top 25 lists. The contract has **no per-step or per-candidate rankings** and **no "segments touched" field** on audit events. So:

- the Top 25 changes only once, at `PLAN_V2` (V1 order, then V2 order);
- `DIAGNOSE`, `TEST_CANDIDATE`, `ACCEPT` and `REJECT` steps highlight no assets, and the map says so;
- the highlight sets are membership only: the V1 Top 25 (`PLAN_V1`), V1 `selected` (`EVALUATE`), assets new to the V2 Top 25 or in `rank_changes.csv` (`PLAN_V2`), and `escalation.csv` (`ESCALATE`).

Showing candidate-by-candidate reordering would need an engine artifact (for example a per-candidate Top-N list per validation origin) and a contract change. It must not be computed in React.
