# Proposal: Consequence-weight sensitivity ("raise consequence weight → Top-25 moves")

Status: **PROPOSAL, needs team approval.** Nothing below is implemented.
Owner of the open decision: Mia (engine). Raised: 2026-10-03, integration branch.

## Why

Case 8 asks for consequence-aware planning and Top-25 comparability (`docs/RUBRIC_TRACEABILITY.md`, Case 8 Traceability). A judge-facing view where raising the consequence weight visibly reorders the Top 25 would show both.

## Current contract: not supported

- `docs/API_CONTRACT.md` has no route that varies consequence weight. `/api/assets` returns one frozen `priority_score` and `rank` per plan.
- `docs/ARTIFACT_SCHEMAS.md` has no artifact with ranks under alternative consequence weights. `plan_v1`/`plan_v2` carry `consequence_tier` and `priority_score` only.
- The priority formula (how `likelihood_score` and consequence combine) and the consequence tier bands are **open** (`docs/DECISIONS.md` §16 keeps consequence minimal: diameter/asset-class tier by default). `config/policy_config.DRAFT.yaml` has no consequence weight key yet.

So the frontend and API **must not** compute this. Re-ranking in React or FastAPI would invent the scoring formula (AGENTS.md rules 2, 3, 4) and would be heavy per-request work (rule 8).

## Proposed shape

### Who computes it

The **engine** computes it offline, after the plan is frozen, using the same priority function that produced `plan_v2.parquet`. The weight grid and Top-N size come from config. The API only reads and serves the artifact. The frontend only displays precomputed steps (a discrete slider, no interpolation).

This is a **display sensitivity on the frozen plan**. It is not a policy candidate. It must never feed the revision gate or policy selection, and must never be evaluated on, or tuned against, the 2023–2025 final window (AGENTS.md rule 6).

### Config (new keys, engine-owned)

```yaml
consequence_sensitivity:
  plan: "v2"
  top_n: 25                      # reuse planning.organizer_top_n
  reference_weight_id: "w_ref"   # the weight used by the frozen plan
  weights:                       # ordered, low → high; values are placeholders
    - { id: "w0",    consequence_weight: 0.0 }
    - { id: "w_ref", consequence_weight: <frozen value> }
    - { id: "w2",    consequence_weight: <higher> }
    - { id: "w3",    consequence_weight: <highest> }
```

### Artifact 1: `consequence_sensitivity.csv`

One row per (weight, asset) for every asset that is in the Top N under **any** weight. This keeps the file small (a few hundred rows at most) and lets the UI show entries and exits.

| column | type | meaning |
|---|---|---|
| `weight_id` | string | id from config |
| `consequence_weight` | float | value from config |
| `asset_id` | string | joins to `plan_v2.parquet` |
| `rank` | int | rank under this weight (full-network rank, 1..N) |
| `in_top_n` | bool | `rank <= top_n` |
| `priority_score` | float | engine output under this weight |
| `consequence_tier` | string | passthrough (physical column, identical across weights) |
| `rank_at_reference` | int | rank under `reference_weight_id` |
| `delta_rank_vs_reference` | int | `rank - rank_at_reference` (negative = rose) |

Integrity: per `weight_id`, ranks unique; exactly `top_n` rows with `in_top_n = true`; the `reference_weight_id` rows must equal `plan_v2.parquet` rank and `priority_score` for the same assets (validator check).

### Artifact 2: fields in `audit_summary.json` (or a small `consequence_sensitivity.json`)

```json
{
  "plan": "v2",
  "top_n": 25,
  "reference_weight_id": "w_ref",
  "weights": [
    { "weight_id": "w0", "consequence_weight": 0.0, "n_entered": 4, "n_exited": 4, "top_n_overlap": 21,
      "tier_mix": { "T1": 6, "T2": 11, "T3": 8 } }
  ]
}
```

Counts are engine-computed so the UI does not derive them.

### Route: `GET /api/consequence-sensitivity`

Query: none for the core view (plan fixed by config). Response, in the standard envelope:

```json
{
  "meta": { "synthetic": true, "config_hash": "PLACEHOLDER" },
  "data": {
    "plan": "v2",
    "top_n": 25,
    "reference_weight_id": "w_ref",
    "weights": [ { "weight_id": "w0", "consequence_weight": 0.0, "n_entered": 4, "n_exited": 4, "top_n_overlap": 21, "tier_mix": { "T1": 6 } } ],
    "items": [ { "weight_id": "w0", "asset_id": "seg_000123", "rank": 3, "in_top_n": true, "priority_score": 0.81,
                 "consequence_tier": "T1", "rank_at_reference": 7, "delta_rank_vs_reference": -4 } ]
  }
}
```

Returns `503 artifacts_unavailable` if the artifact is missing. To keep the existing demo working before the engine ships it, the artifact should be **optional**: the route returns 503 and the frontend hides the view. All other routes stay healthy.

Per AGENTS.md rule 13, adding it means updating `backend/app/schemas`, `docs/API_CONTRACT.md`, `docs/ARTIFACT_SCHEMAS.md`, `scripts/validate_artifacts.py`, the synthetic generator and `frontend/src/types/api.ts` in one change.

### Frontend view (after approval)

A discrete step control (one stop per configured weight, keyboard accessible) above a Top-25 list. On each step the list reorders with a FLIP move animation (instant under reduced motion). Assets entering or leaving the Top 25 get an enter/exit treatment, and the tier mix comes straight from `weights[].tier_mix`. The synthetic banner stays visible. There is no client-side ranking, interpolation or score maths.

## Decisions needed from the team

1. The priority formula: how `consequence_weight` combines with `likelihood_score` (Mia).
2. The consequence tier bands (diameter / asset-class cut points) and whether they are frozen before the final test.
3. The weight grid values, and which one is the frozen reference.
4. Whether this ships for the demo or is listed as post-core.
5. Whether Top-N is fixed at `organizer_top_n` (25) or also offered at the 1/2/5/10 % length budgets.
