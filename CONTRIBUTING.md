# Contributing

## Branches

Use short-lived branches from `main`.

Suggested:
- `feat/audit-engine`
- `feat/api`
- `feat/frontend-overview`
- `fix/<short-description>`

Avoid long-lived personal branches.

## Commits

Use conventional-style prefixes:

- `feat:`
- `fix:`
- `docs:`
- `test:`
- `refactor:`
- `chore:`

Examples:

```text
feat: add FastAPI artifact overview endpoint
fix: prevent post-cutoff features in rolling audit
docs: freeze candidate revision set
```

## Pull Requests

Each PR should:
- have one clear purpose;
- state what changed;
- state how it was tested;
- mention any config/methodology impact;
- avoid mixing architecture changes with unrelated UI work.

## Shared Contract Rule

Do not change:
- artifact schemas;
- API response shapes;
- frozen config;
- experiment protocol

without notifying the other teammate and updating corresponding docs/tests.

## Final-Test Rule

Any commit that changes model selection, features, temporal logic, gate logic, thresholds, or candidate policies after the frozen tag must be treated as invalidating the prior final evaluation.
