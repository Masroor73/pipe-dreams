# Pipe Dreams — API Contract

Base URL in local development:

```text
http://localhost:8000
```

Base path:

```text
/api
```

The API is read-only for the core demo. Every route is `GET`. The optional post-core `POST /api/scenarios/capacity` (see `ARCHITECTURE.md` §8) is **not** part of this contract until it is added here.

---

## Conventions

| Topic | Rule |
|---|---|
| Field casing | `snake_case` on the wire, identical to artifact column names. No Pydantic aliases; frontend types use the same names. |
| Missing values | Fields are always present; unknown/not-applicable values are `null`. Never omitted. |
| Percentages | `budget_pct` is a whole-number percent of network length (`1`, `2`, `5`, `10`). |
| Rates / capture / shares | Fractions in `[0, 1]` (e.g. `asset_capture: 0.184`). |
| Dates | ISO 8601 strings: `YYYY-MM-DD` for dates, `YYYY-MM-DDTHH:MM:SSZ` for timestamps. |
| Coordinates | `latitude` / `longitude` and all GeoJSON are WGS84 (EPSG:4326). EPSG:3776 is engine-internal only. |
| Lengths | metres (`length_m`). |
| Geometry | GeoJSON (MapLibre-native). The backend converts `geometry_wkt` → GeoJSON at load time; no spatial computation per request. |

### Enums

```text
PolicyId          = "V1" | "C1" | "C2" | "C3" | "C4"
BaselineId        = "count_only" | "organizer_cell"
PlanId            = "v1" | "v2"
Split             = "validation" | "final" | "confirmation"
EvidenceConfidence= "HIGH" | "MEDIUM" | "LOW_VERIFY"
AuditEventType    = "PLAN_V1" | "EVALUATE" | "DIAGNOSE" | "TEST_CANDIDATE"
                  | "ACCEPT" | "REJECT" | "PLAN_V2" | "ESCALATE"
CandidateDecision = "ACCEPT" | "REJECT"
```

`consequence_tier`, `recommended_action`, escalation `status`, and `ui_severity` are strings whose allowed values are frozen in `config/`. The API passes them through unchanged; the frontend must not hardcode their meaning beyond display.

### Response envelope

Every response except `/api/health` is:

```json
{
  "meta": {
    "synthetic": true,
    "config_hash": "PLACEHOLDER"
  },
  "data": { }
}
```

The frontend shows the persistent **SYNTHETIC / PLACEHOLDER DATA** banner whenever `meta.synthetic == true` or `meta.config_hash == "PLACEHOLDER"`, on every page, including deep links.

### Errors

```json
{
  "error": {
    "code": "asset_not_found",
    "message": "No asset with id 'abc123' in plan v2."
  }
}
```

| HTTP | `code` | When |
|---|---|---|
| 404 | `asset_not_found` | unknown `asset_id` |
| 404 | `not_found` | unknown route |
| 422 | `invalid_query` | bad query parameter (FastAPI validation) |
| 503 | `artifacts_unavailable` | required artifact missing or failed schema validation |

---

## `GET /api/health`

Not wrapped in the envelope, so it works even when artifacts are broken.

```json
{
  "status": "ok",
  "artifacts_loaded": true,
  "artifact_dir": "artifacts/synthetic",
  "synthetic": true
}
```

`status` is `"ok"` or `"degraded"`. It is `"degraded"`, with `artifacts_loaded: false` and `synthetic: null`, when the artifact loader failed (synthetic-ness is unknown without loaded artifacts).

---

## `GET /api/overview`

Purpose: homepage / judge-facing comparison. Sources: `audit_summary.json`, `validation_results.csv`.

```json
{
  "meta": { "synthetic": true, "config_hash": "PLACEHOLDER" },
  "data": {
    "git_commit": "abc1234",
    "git_tag": "final-freeze-v1",
    "v1_policy_id": "V1",
    "selected_policy_id": "V1",
    "v2_equals_v1": true,
    "final_test_previously_viewed": true,
    "budgets_pct": [1, 2, 5, 10],
    "revision_gate": {
      "min_origin_wins": 2,
      "n_origins": 3,
      "min_improvement_in_se": 1.0,
      "bootstrap_block_km": 1.0
    },
    "series": [
      {
        "split": "validation",
        "origin_cutoff": "2013-12-31",
        "policy_id": "V1",
        "policy_type": "policy",
        "budget_pct": 5,
        "asset_capture": 0.21,
        "event_capture": 0.24,
        "lift_vs_count_only": 1.12,
        "ci_low": 0.18,
        "ci_high": 0.25,
        "matched_break_share": 0.83,
        "pooled_gate_score": 0.19,
        "accepted_vs_v1": null,
        "notes": null
      }
    ]
  }
}
```

`series` holds one row per row of `validation_results.csv`. `policy_id` is a `PolicyId` or `BaselineId`. `policy_type` is `"policy"` or `"baseline"`.

Rules:
- `organizer_cell` rows have `asset_capture: null` and report `event_capture` only.
- `confirmation` rows may have `asset_capture: null`. They are directional relative lift only.
- `final` rows contain only V1, the selected policy, and baselines.
- `origin_cutoff` is `null` for `final` and `confirmation` rows when it does not apply.
- `v2_equals_v1`, `budgets_pct`, `revision_gate` come straight from `audit_summary.json`; `final_test_previously_viewed` = `audit_summary.final_test.previously_viewed`.

---

## `GET /api/assets`

Paged list for tables. No line geometry here; use `/api/assets/geojson` for the map.

Query parameters:

| Param | Type | Default |
|---|---|---|
| `plan` | `PlanId` | `v2` |
| `selected_only` | bool | `false` |
| `evidence_confidence` | `EvidenceConfidence` | none |
| `consequence_tier` | string | none |
| `sort` | `rank` \| `priority_score` \| `length_m` | `rank` |
| `limit` | int, 1–500 | `100` |
| `offset` | int ≥ 0 | `0` |

```json
{
  "meta": { "synthetic": true, "config_hash": "PLACEHOLDER" },
  "data": {
    "plan": "v2",
    "total": 18432,
    "limit": 100,
    "offset": 0,
    "items": [
      {
        "asset_id": "seg_000123",
        "rank": 1,
        "selected": true,
        "length_m": 142.6,
        "priority_score": 0.913,
        "consequence_tier": "T1",
        "evidence_confidence": "HIGH",
        "recommended_action": "INSPECT",
        "latitude": 51.0447,
        "longitude": -114.0719
      }
    ]
  }
}
```

---

## `GET /api/assets/geojson`

Map layer. Returns a bare GeoJSON `FeatureCollection` inside `data`, so it can be passed straight to a MapLibre source.

Query parameters: `plan` (default `v2`) and `selected_only` (default `true`). Requesting the full network (`selected_only=false`) is allowed, but it is large.

```json
{
  "meta": { "synthetic": true, "config_hash": "PLACEHOLDER" },
  "data": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "id": "seg_000123",
        "geometry": { "type": "LineString", "coordinates": [[-114.07, 51.04], [-114.06, 51.04]] },
        "properties": {
          "asset_id": "seg_000123",
          "rank": 1,
          "selected": true,
          "consequence_tier": "T1",
          "evidence_confidence": "HIGH",
          "recommended_action": "INSPECT"
        }
      }
    ]
  }
}
```

---

## `GET /api/assets/{asset_id}`

Asset detail with V1 and V2 side by side. Sources: `plan_v1.parquet`, `plan_v2.parquet`, `rank_changes.csv`.

Physical attributes are shared. Plan-specific fields sit under `v1` / `v2`.

```json
{
  "meta": { "synthetic": true, "config_hash": "PLACEHOLDER" },
  "data": {
    "asset_id": "seg_000123",
    "source_segment_ids": ["12345"],
    "length_m": 142.6,
    "consequence_tier": "T1",
    "evidence_confidence": "HIGH",
    "association_quality": 0.92,
    "rank_stability": 0.88,
    "evidence_basis": "3 matched breaks since 2000; nearest-line distance < 5 m",
    "latitude": 51.0447,
    "longitude": -114.0719,
    "geometry": { "type": "LineString", "coordinates": [[-114.07, 51.04], [-114.06, 51.04]] },
    "v1": {
      "rank": 40,
      "selected": true,
      "likelihood_score": 0.71,
      "priority_score": 0.74,
      "recommended_action": "INSPECT",
      "revision_reason": null
    },
    "v2": {
      "rank": 1,
      "selected": true,
      "likelihood_score": 0.89,
      "priority_score": 0.913,
      "recommended_action": "INSPECT",
      "revision_reason": "recent breaks weighted under hl10"
    },
    "rank_change": {
      "delta_rank": -39,
      "reason_1": "recency weighting",
      "reason_2": null,
      "show_in_demo": true
    }
  }
}
```

`rank_change` is `null` when the asset has no row in `rank_changes.csv`. `likelihood_score` and `priority_score` are separate fields; neither is a failure probability.

---

## `GET /api/rank-changes`

Source: `rank_changes.csv`. Feeds the "three rank/action changes" demo cards.

Query parameters: `demo_only` (bool, default `true`) and `limit` (int, 1–500, default `50`).

```json
{
  "meta": { "synthetic": true, "config_hash": "PLACEHOLDER" },
  "data": {
    "items": [
      {
        "asset_id": "seg_000123",
        "rank_v1": 40,
        "rank_v2": 1,
        "delta_rank": -39,
        "action_v1": "INSPECT",
        "action_v2": "INSPECT",
        "reason_1": "recency weighting",
        "reason_2": null,
        "show_in_demo": true
      }
    ]
  }
}
```

---

## `GET /api/audit`

Ordered autonomous-loop events from `agent_log.jsonl`.

```json
{
  "meta": { "synthetic": true, "config_hash": "PLACEHOLDER" },
  "data": {
    "events": [
      {
        "seq": 4,
        "event_type": "TEST_CANDIDATE",
        "timestamp": "2026-10-03T21:00:00Z",
        "summary": "Testing C2 against V1 on 3 validation origins",
        "candidate": {
          "candidate_id": "C2",
          "origin_wins": 2,
          "n_origins": 3,
          "pooled_v1_score": 0.190,
          "pooled_candidate_score": 0.205,
          "difference": 0.015,
          "bootstrap_se": 0.008,
          "required_delta": 0.008,
          "decision": "ACCEPT",
          "reason": "won 2/3 origins and pooled gain >= 1 SE"
        },
        "details": {}
      }
    ]
  }
}
```

`events` are sorted by `seq` ascending. `candidate` is non-null on `TEST_CANDIDATE`, `ACCEPT` and `REJECT` events, and `null` otherwise. `details` is a free-form object for event-specific extras; the frontend may display it but must not derive domain results from it.

---

## `GET /api/escalations`

Source: `escalation.csv`.

```json
{
  "meta": { "synthetic": true, "config_hash": "PLACEHOLDER" },
  "data": {
    "items": [
      {
        "asset_id": "seg_000123",
        "priority_rank": 1,
        "consequence_tier": "T1",
        "evidence_confidence": "LOW_VERIFY",
        "escalation_reason": "high consequence, low evidence confidence",
        "owner": "Water Integrity Lead",
        "required_action": "Verify asset record before scheduling",
        "response_deadline": "2026-11-01",
        "status": "OPEN",
        "last_reviewed": "2026-10-03"
      }
    ]
  }
}
```

---

## `GET /api/not-covered`

Source: `not_covered.csv`.

```json
{
  "meta": { "synthetic": true, "config_hash": "PLACEHOLDER" },
  "data": {
    "items": [
      {
        "coverage_issue_id": "NC-01",
        "scope": "service connections",
        "description": "Service lines are not in the public pipe layer.",
        "why_not_covered": "No public geometry or break attribution.",
        "required_evidence": "Utility service-line registry",
        "ui_severity": "HIGH",
        "source_note": "City of Calgary open data pipe layer"
      }
    ]
  }
}
```

---

## `GET /api/data-quality`

Source: `data_quality.json`. The engine must write these exact keys. (Note: `ARTIFACT_SCHEMAS.md` lists these items in prose only; these key names are the frozen spelling.)

```json
{
  "meta": { "synthetic": true, "config_hash": "PLACEHOLDER" },
  "data": {
    "rows_dropped_missing_coordinates": 112,
    "match_rate_by_origin": { "2013": 0.81, "2016": 0.84, "2019": 0.86 },
    "match_rate_by_era": { "pre_2000": 0.62, "2000_2012": 0.83, "2013_plus": 0.88 },
    "unmatched_share_by_era": { "pre_2000": 0.38, "2000_2012": 0.17, "2013_plus": 0.12 },
    "unreachable_final_test_share": 0.09,
    "future_year_pipe_rows_excluded": 14,
    "planned_rows_excluded": 230,
    "inactive_sensitivity": { "included_capture_5pct": 0.21, "excluded_capture_5pct": 0.20 },
    "retired_status_strata": { "ACTIVE": 0.93, "RETIRED": 0.07 },
    "notes": ["Present-day network does not reconstruct all historical assets."]
  }
}
```

Map keys are origin years or era labels as strings. Era labels come from config.

---

## Contract Rules

1. Backend response models are Pydantic schemas; field names equal artifact column names.
2. Frontend does not infer missing domain fields.
3. Frontend does not calculate priority, gate outcomes, or policy selection.
4. API does not mutate frozen artifacts.
5. `meta.synthetic` and `meta.config_hash` are present on every enveloped response.
6. Schema changes must update backend Pydantic models, this document, and frontend types in the same pull request.
