# Pipe Dreams — Experiment Protocol

This document is authoritative for model selection, autonomous revision, and final evaluation.

## 1. Time Convention

Cutoff T = end of Dec. 31 of cutoff year T.

At T:
- features may use data through T;
- candidate asset requires `install_year <= T`;
- age = `T - install_year`;
- outcomes are T+1 through T+3;
- stacked labels must end on/before T.

Historical break attribution requires:

```text
install_year < break_year
```

---

## 2. Rolling Validation

| Cutoff | Outcomes |
|---:|---|
| 2013 | 2014–2016 |
| 2016 | 2017–2019 |
| 2019 | 2020–2022 |

Report reachable/matched outcome share at every origin.

---

## 3. Final Corrected Test

Cutoff:
- 2022.

Outcomes:
- 2023–2025.

Disclosure:
- this final window was viewed once in an earlier flawed audit.

Before corrected run:
- thresholds frozen;
- no TODO/placeholders;
- config hashed;
- commit/tag recorded.

After result:
- no tuning.

---

## 4. 2026 Confirmation

Cutoff:
- 2025.

Outcome:
- 2026 YTD.

Use:
- directional relative lift versus the same baselines only.

Do not compare incomplete-YTD absolute capture directly with 3-year capture.

---

## 5. History Windows

Preserve prior audit choices:
- `full`;
- `2000_plus`;
- `2016_plus`.

`2016_plus` is not eligible for the multi-origin winner where early origins cannot evaluate it fairly.

---

## 6. Recency

Frozen:
- `none`;
- `hl10`.

No new half-lives.

---

## 7. V1

- full history;
- no decay;
- per-asset ranking.

V1 is intentionally not the pre-optimized winner.

---

## 8. Candidate Revisions

- C1: `2000_plus`, no decay, per-asset.
- C2: full history, `hl10`, per-asset.
- C3: full history, no decay, per-metre.
- C4: `2000_plus + hl10`, per-asset.

Compare each independently against V1 on validation.

If several pass:
- highest pooled validation score becomes V2.

If none pass:
- V2 = V1.

---

## 9. Primary Gate Metric

For budgets:

```text
1%, 2%, 5%, 10% of eligible network length
```

Per-origin score:

```text
mean future-breaking-asset capture across the four budgets
```

Pooled score:

```text
mean of per-origin scores across 2013, 2016, 2019 validation origins
```

---

## 10. Spatial Block Bootstrap

- CRS: EPSG:3776.
- Block: 1 km × 1 km.
- Default reps: 1000.
- Resample blocks, not individual assets.

---

## 11. Acceptance Gate

Candidate passes only if:
1. candidate beats V1 at ≥2 of 3 validation origins; and
2. pooled improvement ≥1 pooled spatial-block-bootstrap SE.

This is a pragmatic heuristic, not a formal significance test.

---

## 12. Baselines

### Count-only
Same segment unit as Pipe Dreams.

### Organizer cell baseline
Rounded-coordinate cell.

Metric:
- future event capture.

Do not report pipe-capture for a cell baseline.

Other simple baselines may be retained if already implemented and clearly labeled.

---

## 13. Evidence Confidence

Thresholds may use validation data only.

Freeze them before the corrected final test.

Output:
- HIGH;
- MEDIUM;
- LOW_VERIFY.

If holdout outcomes do not separate:
- describe as evidence-quality tiers only.

---

## 14. Data Quality

Report:
- rows dropped for missing coordinates;
- matched/unmatched breaks;
- match rate by era;
- match/reachable rate by origin;
- unreachable final-test share;
- planned/future-year exclusions;
- current INACTIVE sensitivity;
- present-day RETIRED status as reporting stratum only.

---

## 15. Final-Test Candidate Restriction

Final window scores:
- V1;
- selected V2;
- frozen baselines.

Do not score every rejected candidate on the final window.

---

## 16. Reproducibility

`audit_summary.json` must contain:
- config hash;
- git commit/tag;
- data checksums;
- V1 ID;
- V2 ID;
- gate definition;
- final-window disclosure;
- synthetic flag;
- data-quality summary.

---

## 17. Claims

Allowed only with supporting artifact:
- measured capture/lift;
- candidate accepted/rejected under gate;
- comparison to baseline;
- confidence/evidence tier under declared rule.

Not allowed:
- exact production failure probability;
- official Calgary risk;
- automatic repair recommendation;
- invented savings;
- Bearspaw prediction/prevention claim.
