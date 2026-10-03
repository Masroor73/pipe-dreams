# Pipe Dreams — API Contract

Base URL in local development:

```text
http://localhost:8000
```

Base path:

```text
/api
```

The API is read-only for the core demo.

## `GET /api/health`

Response:

```json
{
  "status": "ok"
}
```

## `GET /api/overview`

Purpose:
- homepage / judge-facing comparison.

Response concept:

```json
{
  "synthetic": false,
  "config_hash": "sha256...",
  "selected_policy_id": "C4_joint_2000_plus_hl10",
  "v1_policy_id": "V1",
  "final_test_previously_viewed": true,
  "budgets_pct": [1, 2, 5, 10],
  "series": []
}
```

## `GET /api/assets`

Query parameters may include:
- `plan=v1|v2`;
- `selected_only=true|false`;
- `limit`.

Returns map/list-safe asset summaries.

## `GET /api/assets/{asset_id}`

Returns:
- ranks;
- selected state;
- likelihood/priority score;
- consequence tier;
- evidence-confidence tier;
- evidence basis;
- action;
- change explanation;
- geometry / centroid fields needed by UI.

## `GET /api/audit`

Returns ordered autonomous-loop events from `agent_log.jsonl`.

## `GET /api/escalations`

Returns in-dataset escalation records.

## `GET /api/not-covered`

Returns explicit coverage/evidence gaps.

## `GET /api/data-quality`

Returns data-quality and matchability disclosures.

---

## Contract Rules

1. Backend response models are Pydantic schemas.
2. Frontend does not infer missing domain fields.
3. Frontend does not calculate priority or gate outcomes.
4. API does not mutate frozen artifacts.
5. Synthetic flag is propagated on all judge-facing overview responses.
6. Schema changes require updating this document and frontend types in the same pull request.
