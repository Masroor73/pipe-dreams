# Pipe Dreams — AI Coding Guardrails

This file is intentionally editor/model agnostic. It applies equally to Cursor, VS Code extensions, Claude, Gemini, ChatGPT, Copilot, or another coding assistant.

Before making architectural, modeling, or API-contract changes, read:

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `docs/TECH_STACK.md`
- `docs/EXPERIMENT_PROTOCOL.md`
- `docs/API_CONTRACT.md`
- `docs/ARTIFACT_SCHEMAS.md`
- `docs/RUBRIC_TRACEABILITY.md`
- `docs/BUILD_PLAN.md`

Rules:

1. Do not introduce a new framework, model family, data source, database, queue, or cloud service without explicit team approval.
2. Keep React responsible for presentation, not risk calculations.
3. Keep FastAPI thin; do not duplicate engine logic in API routes.
4. Do not use an LLM for risk scoring, model selection, revision acceptance, or consequence weighting.
5. Preserve temporal rules exactly as documented.
6. Never tune from the corrected 2023–2025 final result.
7. `VERIFY` and `ESCALATE` are governance rules unless independently validated.
8. Heavy spatial/model work is precomputed into artifacts.
9. Synthetic artifacts must always surface a visible synthetic-data warning.
10. Do not use or recreate unsupported Bearspaw rank/prediction claims.
11. If code and `EXPERIMENT_PROTOCOL.md` conflict, stop and flag the conflict rather than silently changing methodology.
12. Prefer explicit, boring, testable code over abstraction.
13. API schema changes must update backend Pydantic models, `API_CONTRACT.md`, and frontend types in the same change.
14. Domain constants and thresholds belong in config, not scattered literals.
15. Do not change frozen experiment choices merely because another AI suggests an alternative.
