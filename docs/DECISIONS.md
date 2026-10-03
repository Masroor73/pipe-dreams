# Pipe Dreams — Decisions Log

This file records **why** major choices were made. It is authoritative for architectural/product tradeoffs.

## 1. Product Scope

**Decision:** inspection-planning and audit agent, not autonomous repair/replacement.

**Reason:** public data does not provide the condition, hydraulic, operational, or cost evidence required to authorize replacement.

---

## 2. Planning Unit

**Decision:** raw public GIS segment for the hackathon MVP.

**Reason:** this is the unit already used by the existing audit and avoids introducing new topology logic late in the build.

**Known limitation:** tiny segments can distort per-metre ranking.

**Rejected for MVP:** run-merging/topology reconstruction.

---

## 3. Frontend

**Decision:** React + TypeScript + Vite.

**Reason:** both teammates already have substantial React/TypeScript experience; neither has Streamlit experience. Using the team's strongest stack reduces delivery risk and allows a more controlled demo UI.

**Rejected:** Streamlit.

This is not because Streamlit is unsuitable in general; it is because it is the wrong optimization for this team's existing skills.

---

## 4. Backend API

**Decision:** FastAPI.

**Reason:** React requires an HTTP/data boundary to the Python engine and artifacts. FastAPI gives:
- Python-native access to the engine/artifacts;
- typed Pydantic contracts;
- automatic OpenAPI docs;
- minimal glue code.

**Important:** FastAPI does not replace the engine. It replaces Streamlit's role as the browser-facing Python application layer.

---

## 5. Architecture Shape

**Decision:** monorepo with React SPA + thin FastAPI + Python engine.

**Rejected:**
- microservices;
- database-backed distributed architecture;
- Node backend;
- duplicated TypeScript risk logic.

---

## 6. Heavy Computation

**Decision:** precompute spatial joins, rolling backtests, bootstrap, and final plans.

**Reason:** live recomputation adds demo risk and no rubric value.

FastAPI serves artifacts; it does not rerun the audit per page request.

---

## 7. Model Choice

**Decision:** logistic regression is the primary current candidate subject to corrected rolling validation.

**Reason:** previous audit showed it outperforming the more complex boosting candidate.

**Rejected:** keeping gradient boosting simply because it looks more sophisticated.

---

## 8. V1

**Decision:** full history, no recency decay, per-asset ranking.

**Reason:** V1 must be a declared starting policy, not the fully optimized validation winner.

Known weakness:
- under a length budget, per-asset ranking can let long segments consume more capacity.

---

## 9. Candidate Revisions

Frozen finite candidate set:

- **C1:** `2000_plus`, no decay, per-asset.
- **C2:** full history, `hl10`, per-asset.
- **C3:** full history, no decay, per-metre.
- **C4:** `2000_plus + hl10`, per-asset.

If several pass the frozen gate, highest pooled validation score wins.

If none pass, V2 = V1.

---

## 10. Recency Grid

**Decision:** only:
- `none`;
- `hl10`.

These are the exact settings used in the earlier audit.

Do not add 5-year or 20-year variants after the fact.

---

## 11. Final-Test Discipline

**Decision:** corrected 2023–2025 final test runs only after config freeze, hash, commit, and tag.

**Disclosure:** the final window had been seen once in the earlier flawed audit.

**Rule:** no tuning after corrected result is viewed.

---

## 12. Revision Gate

**Decision:** candidate score is mean future-breaking-asset capture across fixed 1%, 2%, 5%, and 10% network-length budgets.

Candidate must:
- beat V1 on at least 2 of 3 rolling validation origins;
- improve pooled mean by at least 1 pooled 1-km spatial-block-bootstrap SE.

This is a pragmatic decision heuristic, not a formal significance test.

---

## 13. Bootstrap

**Decision:** 1 km spatial blocks in EPSG:3776.

**Reason:** spatially clustered outcomes make naive per-asset bootstrap too optimistic.

---

## 14. Priority vs Evidence Confidence

**Decision:** separate them.

Priority:
- planning/ranking output.

Evidence confidence:
- quality, completeness, and stability of supporting evidence.

Do not represent evidence confidence as failure probability.

---

## 15. Governance

**Decision:** VERIFY / ESCALATE are governance rules unless independently validated.

**Reason:** validating them against the same ambiguity/stability inputs that define them would be circular.

---

## 16. Consequence

**Decision:** keep consequence prototype minimal.

Default:
- diameter / asset-class tier.

Fallback:
- organizer lab consequence with explicit disclosure.

**Rejected as default:**
- community population;
- school proximity;
- fire-station proximity;
- invented people-served estimates;
- invented savings.

---

## 17. Bearspaw

**Decision:** do not use a Bearspaw rank/prediction claim.

**Reason:** the earlier inferred asset identity was not sufficiently verified for a judge-facing claim.

A previous draft also contained an incorrect/unverified statement that the project pipe file had no segments above 900 mm. That statement must not be repeated.

Allowed:
- verified contextual motivation about consequence / escalation.

Not allowed:
- "our model ranked/predicted Bearspaw";
- "Pipe Dreams would have prevented Bearspaw."

---

## 18. Organizer Baseline

**Decision:** preserve the rounded-coordinate-cell starter baseline for Case 8 comparability.

Because it is cell-based:
- compare it on future event capture;
- do not force it into a pipe-level capture metric.

Count-only on the same segment unit is the primary pipe-level baseline.

---

## 19. Frontend Risk Logic

**Decision:** none.

The frontend never calculates priority or policy selection.

All domain results come from the backend/frozen artifacts.

---

## 20. Database

**Decision:** no database for MVP.

**Reason:** artifacts are enough for a two-person hackathon and improve reproducibility.

---

## 21. ElevenLabs

**Decision:** post-core only.

Preferred:
- TTS summary / escalation briefing.

Do not jeopardize core autonomous reasoning or final demo for sponsor integration.

---

## 22. AI Coding Assistants

**Decision:** repo-level `AGENTS.md` contains tool/model-independent guardrails.

Do not commit Cursor-specific, Claude-specific, Gemini-specific, or VS Code-specific behavioral config as the authoritative project specification.

Individual developers may use local editor-specific configuration, but it must not become the shared source of architectural truth.

---

## 23. Remaining Freeze Items

Before corrected final testing:

1. derive evidence-confidence thresholds from validation data only;
2. remove placeholders from frozen config;
3. hash config;
4. commit and tag;
5. run corrected final evaluation once.

Architecture and tech stack are otherwise frozen unless a concrete bug, official-rule conflict, or strong domain correction requires change.
